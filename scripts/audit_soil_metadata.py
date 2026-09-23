"""Audit pinned soil attributes; no repairs, parcel ratings or live writes."""
import argparse,json,hashlib,xml.etree.ElementTree as ET
from collections import defaultdict,Counter
from decimal import Decimal
from pathlib import Path
from verify_county_soil_bundle import verify,file_sha
from collect_county_soils import rows

def missing(v):return v is None or str(v).strip()==''
def number(v):return None if missing(v) else Decimal(str(v))
def ranges(records,base):
    incomplete=[];reversed_keys=[]
    for r in records:
        vals=[number(r.get(base+'_'+suffix)) for suffix in ['l','r','h']]
        key=r.get('cokey') if 'chkey' not in r else r['chkey']
        if any(v is None for v in vals):incomplete.append(key)
        known=[v for v in vals if v is not None]
        if any(a>b for a,b in zip(known,known[1:])):reversed_keys.append(key)
    return {'incomplete_count':len(incomplete),'inverted_keys':reversed_keys}
def profile(mapunits,components,horizons):
    by_mu=defaultdict(list);by_co=defaultdict(list)
    for c in components:by_mu[c['mukey']].append(c)
    for h in horizons:by_co[h['cokey']].append(h)
    missing_h=[{k:c.get(k) for k in ['cokey','mukey','compname','compkind','comppct_r']} for c in components if not by_co[c['cokey']]]
    pct=[];varied=0;ties=0
    for m in mapunits:
        cs=by_mu[m['mukey']];values=[number(c['comppct_r']) for c in cs]
        if any(v is None for v in values) or sum(values)!=100:pct.append({'mukey':m['mukey'],'sum':str(sum(v for v in values if v is not None)),'missing':sum(v is None for v in values)})
        known=[v for v in values if v is not None]
        if known and known.count(max(known))>1:ties+=1
        if len({c['drainagecl'] for c in cs if not missing(c['drainagecl'])})>1:varied+=1
    bounds=[]
    for ckey,hs in by_co.items():
        valid=[]
        for h in hs:
            top=number(h['hzdept_r']);bottom=number(h['hzdepb_r'])
            if top is None or bottom is None or top>=bottom:bounds.append({'cokey':ckey,'chkey':h['chkey'],'problem':'missing_or_nonpositive_depth'});continue
            valid.append((top,bottom,h['chkey']))
        valid.sort()
        for left,right in zip(valid,valid[1:]):
            if left[1]!=right[0]:bounds.append({'cokey':ckey,'between':[left[2],right[2]],'problem':'gap' if left[1]<right[0] else 'overlap'})
    nulls={kind:{field:sum(missing(r.get(field)) for r in data) for field in fields} for kind,data,fields in [
      ('component',components,['comppct_r','slope_l','slope_r','slope_h','drainagecl','hydricrating','hydgrp']),
      ('chorizon',horizons,['hzdept_r','hzdepb_r','ksat_l','ksat_r','ksat_h','awc_r','sandtotal_r','claytotal_r']),
      ('mapunit',mapunits,['vtsepticsyscl','mustatus','mucertstat'])]}
    return {'counts':{'mapunits':len(mapunits),'components':len(components),'horizons':len(horizons)},'missing':nulls,
      'components_without_horizons':missing_h,'component_percent_sum_exceptions':pct,'mapunits_with_multiple_components':sum(len(v)>1 for v in by_mu.values()),
      'mapunits_with_tied_largest_component':ties,'mapunits_with_differing_drainage_classes':varied,'horizon_depth_observations':bounds,
      'ranges':{'component.'+b:ranges(components,b) for b in ['comppct','slope']}|{'chorizon.'+b:ranges(horizons,b) for b in ['hzdept','hzdepb','ksat','awc']}}
def audit(bundle,evidence,output):
    verified=verify(bundle);root=Path(__file__).resolve().parents[1]
    sources=json.loads((evidence/'sources.json').read_bytes())
    for s in sources:
        if file_sha(evidence/s['file'])!=s['sha256']:raise ValueError('Evidence changed')
    table=defaultdict(list)
    for line in (bundle/'records.jsonl').open():
        r=json.loads(line);table[r['kind']].append(r)
    investigation=json.loads((root/'research/soil-holds-investigation/report.json').read_bytes())
    activation_path=root/'research/soil-correction-activation/live-verification.json';activation=json.loads(activation_path.read_bytes())
    if activation['status']!='PASS' or activation['batch']!=verified['report_sha256']:raise ValueError('Activation source differs')
    accepted={x['mupolygonkey'] for x in investigation['candidates'] if x['candidate_county_area_m2']>0}
    county_mu={r['raw']['mukey'] for r in table['mupolygon'] if r['scope_relation']=='interior' or r['source_key'] in accepted}
    all_mu=[r['raw'] for r in table['mapunit']];all_co=[r['raw'] for r in table['component']];all_hz=[r['raw'] for r in table['chorizon']]
    county_co=[c for c in all_co if c['mukey'] in county_mu];keys={c['cokey'] for c in county_co}
    scoped=profile([m for m in all_mu if m['mukey'] in county_mu],county_co,[h for h in all_hz if h['cokey'] in keys])
    source_report=json.loads((bundle/'report.json').read_bytes())
    capture=json.loads((bundle/'objects'/source_report['capture_sha256']).read_bytes())
    requests=json.loads((bundle/'objects'/capture['requests_sha256']).read_bytes())
    catalog_request=next(r for r in requests if r['id']=='catalog-start')
    catalog={r['areasymbol']:r for r in rows(json.loads((bundle/'objects'/catalog_request['sha256']).read_bytes()))}
    current={r['areasymbol']:r for r in rows(json.loads((evidence/'survey-metadata.response').read_bytes()))}
    surveys=[]
    for item in table['legend']:
        r=item['raw'];c=current[r['areasymbol']];old=catalog[r['areasymbol']];xml=ET.fromstring(c['fgdcmetadata'])
        def texts(path):return [e.text for e in xml.findall(path)]
        surveys.append({'areasymbol':r['areasymbol'],'project_scale_denominator':r['projectscale'],'correlation_date':r['cordate'],'tabular_version':r['tabularversion'],
          'survey_version':c['saversion'],'version_established':c['saverest'],'catalog_version_and_metadata_match_capture':all(c[k]==old[k] for k in ['saversion','saverest','fgdcmetadata']),
          'fgdc_sha256':hashlib.sha256(c['fgdcmetadata'].encode()).hexdigest(),'publication_dates':texts('./idinfo/citation/citeinfo/pubdate'),
          'dataset_time_begin':texts('./idinfo/timeperd/timeinfo/rngdates/begdate'),'dataset_time_end':texts('./idinfo/timeperd/timeinfo/rngdates/enddate'),
          'time_currentness':texts('./idinfo/timeperd/current'),'metadata_dates':texts('./metainfo/metd'),
          'source_lineage':[{'abbreviation':n.findtext('srccitea'),'scale':n.findtext('srcscale'),'publication':n.findtext('srccite/citeinfo/pubdate'),'time_begin':n.findtext('srctime/timeinfo/rngdates/begdate'),'time_end':n.findtext('srctime/timeinfo/rngdates/enddate')} for n in xml.findall('./dataqual/lineage/srcinfo')]})
    report={'evidence_state':'DERIVED','method_sha256':file_sha(Path(__file__)),'bundle':verified,'sources':sources,'activation_sha256':file_sha(activation_path),
      'geometry_snapshot_id':activation['coverage']['snapshot_id'],'scope':'Unique map units touched by positive-area county polygons under pinned accepted corrections; not parcel-specific or area-weighted',
      'surveys':surveys,'whole_seven_survey_tables':profile(all_mu,all_co,all_hz),'county_linked_tables':scoped,
      'limits':['No source changes or live availability promotion','Version agreement does not establish currentness of every attribute','Source dates are not site observation dates','Components are mixtures, not separately mapped within parcels','All attributes outside the documented bounded dictionary remain unqualified']}
    output.mkdir(parents=True,exist_ok=False);(output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'counts':scoped['counts'],'component_percent_exceptions':len(scoped['component_percent_sum_exceptions']),'missing_horizon_components':len(scoped['components_without_horizons'])},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['bundle','evidence','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();audit(a.bundle,a.evidence,a.output)
