"""Capture SDA source evidence for the pinned county; no database writes."""
import argparse,hashlib,json,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from shapely import wkb,wkt
from shapely.geometry import box
from shapely.ops import transform,unary_union
from pyproj import Transformer
URL='https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def rows(document):
    table=document.get('Table')
    if not table or len(set(table[0]))!=len(table[0]):raise ValueError('Missing/duplicate SDA columns')
    if any(len(r)!=len(table[0]) for r in table[1:]):raise ValueError('SDA row width mismatch')
    return [dict(zip(table[0],r)) for r in table[1:]]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--county-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=a.resume);logs=json.loads((a.output/'requests.json').read_bytes()) if a.resume else []
    b=json.loads(a.county_report.read_bytes())['boundary'];boundary=wkb.loads(b['wkb_hex'],hex=True)
    if b['srid']!=26919 or sha(boundary.wkb)!=b['sha256'] or not boundary.is_valid:raise ValueError('County boundary mismatch')
    forward=Transformer.from_crs(26919,4326,always_xy=True);back=Transformer.from_crs(4326,26919,always_xy=True)
    geographic=transform(forward.transform,boundary);envelope=box(*geographic.bounds).wkt
    def fetch(name,query):
        payload={'query':query,'format':'JSON+COLUMNNAME'}
        if a.resume:
            matches=[entry for entry in logs if entry['id']==name]
            if matches:
                entry=matches[0];raw=(a.output/entry['response_file']).read_bytes()
                if len(matches)!=1 or entry['payload']!=payload or sha(raw)!=entry['sha256']:raise ValueError('Resume evidence mismatch')
                return rows(json.loads(raw))
        started=datetime.now(timezone.utc).isoformat()
        request=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','User-Agent':'TerraLucid source capture'})
        with urllib.request.urlopen(request,timeout=90) as response:
            raw=response.read();status=response.status
        (a.output/(name+'.json')).write_bytes(raw)
        logs.append({'id':name,'url':URL,'payload':payload,'retrieved_at':started,'http_status':status,'sha256':sha(raw),'bytes':len(raw),'response_file':name+'.json'})
        (a.output/'requests.json').write_text(json.dumps(logs,indent=2)+'\n')
        result=rows(json.loads(raw));print(name,len(result),flush=True);return result
    catalog_sql="SELECT * FROM sacatalog WHERE areasymbol LIKE 'ME%' ORDER BY areasymbol"
    before=fetch('catalog-start',catalog_sql)
    candidates=fetch('survey-candidates',"SELECT areasymbol FROM SDA_Get_Areasymbol_from_intersection_with_WktWgs84('"+envelope+"') ORDER BY areasymbol")
    surveys=[]
    for candidate in candidates:
        code=candidate['areasymbol']
        if not re.fullmatch('[A-Z]{2}[0-9]{3}',code):raise ValueError('Invalid survey code')
        outlines=fetch('outline-'+code,"SELECT * FROM SDA_Get_AreasymbolWKTWgs84_from_Areasymbol('"+code+"')")
        gs=[transform(back.transform,wkt.loads(r['AreasymbolWkt84'])) for r in outlines]
        if not gs or any(not g.is_valid or g.is_empty for g in gs):raise ValueError('Unusable survey outline; preserve response and investigate '+code)
        area=unary_union(gs).intersection(boundary).area
        surveys.append({'areasymbol':code,'county_intersection_m2':area,'selected':area>0})
    # Capture every polygon in the envelope, including narrow adjacent-survey parts.
    id_sql="SELECT mupolygonkey FROM SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84('"+envelope+"') ORDER BY mupolygonkey"
    count_sql="SELECT COUNT(*) AS n FROM SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84('"+envelope+"')"
    count=int(fetch('polygon-count-start',count_sql)[0]['n']);ids=[r['mupolygonkey'] for r in fetch('polygon-ids-start',id_sql)]
    if len(ids)!=count or len(set(ids))!=count or any(not re.fullmatch('[0-9]+',x) for x in ids):raise ValueError('Polygon membership mismatch')
    for offset in range(0,len(ids),500):
        part=ids[offset:offset+500]
        data=fetch('polygons-'+str(offset),"SELECT mupolygonkey,mukey,mupolygongeo.STAsText() AS source_wkt FROM mupolygon WHERE mupolygonkey IN ("+','.join(part)+") ORDER BY mupolygonkey")
        if sorted(r['mupolygonkey'] for r in data)!=sorted(part):raise ValueError('Polygon page mismatch')
    # All envelope-survey tables retained: outside-county rows are not coverage evidence.
    codes=','.join("'"+r['areasymbol']+"'" for r in surveys)
    joins={'legend':('l','legend l','l.lkey'),
           'mapunit':('m','mapunit m JOIN legend l ON l.lkey=m.lkey','m.mukey'),
           'component':('c','component c JOIN mapunit m ON m.mukey=c.mukey JOIN legend l ON l.lkey=m.lkey','c.cokey'),
           'chorizon':('h','chorizon h JOIN component c ON c.cokey=h.cokey JOIN mapunit m ON m.mukey=c.mukey JOIN legend l ON l.lkey=m.lkey','h.chkey')}
    for name,(alias,join,key) in joins.items():
        where=' FROM '+join+' WHERE l.areasymbol IN ('+codes+')'
        expected=int(fetch(name+'-count','SELECT COUNT(*) AS n'+where)[0]['n'])
        if expected>=100000:raise ValueError('Table needs pagination')
        data=fetch(name,'SELECT '+alias+'.*'+where+' ORDER BY '+key)
        if len(data)!=expected or len({r[key.split('.')[1]] for r in data})!=expected:raise ValueError('Table count/key mismatch')
    # SDA does not expose the attempted metadata table query; units require
    # the publisher's separate Tables and Columns metadata before interpretation.
    after=fetch('catalog-end',catalog_sql)
    end_ids=[r['mupolygonkey'] for r in fetch('polygon-ids-end',id_sql)]
    if before!=after or ids!=end_ids:raise ValueError('Source changed during capture')
    result={'status':'CAPTURED','boundary':b,'surveys':surveys,'polygon_count':count,'catalog_and_membership_stable':True,
            'requests_sha256':sha((a.output/'requests.json').read_bytes()),'method_sha256':sha(Path(__file__).read_bytes()),
            'limits':['Sequential source requests, not an atomic source snapshot','Envelope candidates are not exact county coverage','No source repairs or suitability determinations']}
    (a.output/'capture.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
