#!/usr/bin/env python3
"""Explain the captured 0443D display discrepancy; never replace the published map."""
import argparse
import json
from pathlib import Path

import fitz
from shapely.geometry import Polygon, box

from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql, verify
from investigate_osborn_fema import parts, restore

BASE=ROOT/'research/fema-map-discrepancy'
METHOD='scripts/investigate_fema_map_mask.py'
PRIOR_SHA='97dcabac9db9de0f153760755f8fe6e2088d9588c73e98bd58b7505fb7cbd5f3'
PDF_SHA='fcef7a0a0838e02a45ded5ab071078e5f4938ae02c2849b4bd1639bfb333320b'
PDF_PATH='research/osborn-fema/large-documents/osborn-lomr-document.response'
PAGE=7
MASK=103
CLIP=[560,240,740,390]


def require(value,message):
    if not value:raise ValueError(message)


def validate_mask(document):
    require(document.page_count==10 and document[PAGE].xref==190, 'Unexpected PDF structure')
    require(document.get_layer()=={}, 'Original default configuration changed')
    require(document.get_ocgs()[MASK]['name']=='MASK', 'Unexpected optional-content group')
    require(document.xref_get_key(document[PAGE].xref,'Resources/Properties/OC6')==('xref','103 0 R'), 'Mask/page association changed')
    paths=[d for d in document[PAGE].get_drawings(extended=True) if d.get('layer')=='MASK' and d['type']=='f']
    require(len(paths)==1,'Ambiguous mask paint')
    d=paths[0]
    require(d['fill']==(1.0,1.0,1.0) and d['fill_opacity']==1 and d['even_odd'], 'Mask is not the expected opaque white fill')
    require(len(d['items'])==4 and all(item[0]=='l' for item in d['items']), 'Mask path changed')
    coordinates=[list(d['items'][0][1])]+[list(item[2]) for item in d['items']]
    require(all(d['items'][i][2]==d['items'][(i+1)%4][1] for i in range(4)), 'Mask path not closed/continuous')
    mask=Polygon(coordinates)
    require(mask.is_valid and mask.covers(box(*CLIP)), 'Mask does not cover the diagnostic crop')
    return {'pdf_page':PAGE+1,'page_xref':190,'optional_content_group_xref':MASK,
            'page_resource':'OC6','name':'MASK','paint_sequence':d['seqno'],
            'fill':list(d['fill']),'opacity':d['fill_opacity'],'path_page_points':coordinates,
            'diagnostic_clip_page_points':CLIP,'covers_diagnostic_clip':True,
            'group_dictionary':document.xref_object(MASK)}


def hidden_view(original):
    """Toggle an exact OCG by xref in memory; same-name UI groups are ambiguous."""
    before={x:original.xref_object(x) for x in range(1,original.xref_length())}
    original.set_layer(-1,off=[MASK])
    changed=[x for x,text in before.items() if original.xref_object(x)!=text]
    require(changed==[original.pdf_catalog()], 'Changes outside catalog display configuration')
    require(original.get_layer()=={'off':[MASK]}, 'Unexpected layer change')
    # Reopen in memory to make the renderer adopt the changed default configuration.
    # Serialization can re-encode object dictionaries; this copy is never saved as evidence.
    view=fitz.open(stream=original.tobytes(),filetype='pdf')
    require(view.get_layer()=={'off':[MASK]}, 'Display configuration did not persist in temporary view')
    for i in range(original.page_count):
        require(original[i].get_contents()==view[i].get_contents(), 'Page content membership changed')
        for x in original[i].get_contents():
            require(original.xref_stream(x)==view.xref_stream(x), 'Page drawing instructions changed')
    return view


def pixmap(document,page=PAGE,crop=True):
    return document[page].get_pixmap(matrix=fitz.Matrix(4,4) if crop else fitz.Matrix(.3,.3),
                                    clip=fitz.Rect(CLIP) if crop else None)


def build():
    inputs,evidence={},{}
    def dependency(path,expected=None):
        data=(ROOT/path).read_bytes()
        require(expected is None or digest(data)==expected,'Changed input: '+path)
        inputs[path]=digest(data);return data
    prior=json.loads(dependency('research/fema-geometry-investigation/report.json',PRIOR_SHA))
    pdf=(ROOT/PDF_PATH).read_bytes();require(digest(pdf)==PDF_SHA,'Original PDF checksum changed')
    document=prior['large_document_evidence']
    require(document['retrieval']['sha256']==PDF_SHA and parts(pdf)==document['parts'], 'PDF archive metadata mismatch')
    review=json.loads(dependency('research/fema-map-discrepancy/review.json'))
    require(review['pdf_sha256']==PDF_SHA,'Review belongs to another PDF')
    previous_review=json.loads(dependency('research/fema-geometry-investigation/map-review.json'))
    old_clip=next(r['clip_points'] for r in previous_review['locators'] if r['OBJECTID']==27129510)
    require(box(*CLIP).covers(box(*old_clip)), 'Diagnostic crop does not include the prior locator')
    service=prior['evidence']['render/render-27129510']
    dependency('research/fema-geometry-investigation/'+service['response_path'],service['sha256'])
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            require(Path(r['response_file']).name==r['response_file'],'Unsafe response path')
            path=log.parent/r['response_file'];data=path.read_bytes()
            require(r['http_status']==200 and digest(data)==r['sha256'] and len(data)==r['bytes'],'Failed reference capture')
            evidence[log.parent.name+'/'+r['id']]=dict(r,response_path=path.relative_to(BASE).as_posix())
    source=fitz.open(stream=pdf,filetype='pdf');mask=validate_mask(source)
    original_pix=pixmap(source)
    controls={i:digest(pixmap(source,i,False).samples) for i in [6,8]}
    view=hidden_view(source);revealed_pix=pixmap(view)
    require(original_pix.width==revealed_pix.width and original_pix.height==revealed_pix.height,'Crop dimensions changed')
    require(original_pix.samples!=revealed_pix.samples,'Mask toggle has no visible effect')
    require(all(digest(pixmap(view,i,False).samples)==sha for i,sha in controls.items()),'Control page changed')
    # Restore the mask and verify that the original rendered display is recovered exactly.
    view.set_layer(-1,on=[MASK],off=[])
    restored=fitz.open(stream=view.tobytes(),filetype='pdf')
    require(pixmap(restored).samples==original_pix.samples,'Restoring the mask failed pixel equality')
    paths={}
    for name,pix in [('published-display',original_pix),('diagnostic-mask-hidden',revealed_pix)]:
        path=BASE/'diagnostics'/(name+'.png');path.parent.mkdir(exist_ok=True)
        data=pix.tobytes('png');path.write_bytes(data);dependency(path.relative_to(ROOT).as_posix(),digest(data))
        paths[name]={'path':path.relative_to(ROOT).as_posix(),'sha256':digest(data),'bytes':len(data),
                     'pixel_sha256':digest(pix.samples),'width':pix.width,'height':pix.height,
                     'classification':'DERIVED diagnostic rendering; not a revised official map'}
    require((ROOT/PDF_PATH).read_bytes()==pdf,'Source file was modified')
    for path in ['scripts/investigate_osborn_fema.py','scripts/prepare_source_staging.py',
                 'scripts/collect_document_evidence.py','research/fema-map-discrepancy/probes.json']:
        dependency(path)
    return {'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),
        'scope':{'OBJECTID':27129510,'panel':'23009C0443D','prior_audit_sha256':PRIOR_SHA,
                 'new_FEMA_capture':False,'purpose':'Explain the existing captured map/service display discrepancy'},
        'evidence':evidence,'inputs':inputs,'large_document_evidence':document,
        'runtime':{'PyMuPDF':fitz.VersionBind,'MuPDF':fitz.VersionFitz},'mask':mask,'renderings':paths,
        'checks':{'only_catalog_dictionary_changed_before_serialization':True,
            'all_page_drawing_instruction_streams_unchanged':True,
            'control_pages_7_and_9_pixel_identical':True,'restored_page_8_crop_pixel_identical':True,
            'original_PDF_bytes_unchanged':True,'modified_PDF_saved':False,
            'no_geometry_or_screening_change':True},
        'review':review,
        'conclusion':{'display_discrepancy':'EXPLAINED: opaque white optional-content mask covers existing hazard graphics.',
            'underlying_graphics':'Visual context is consistent with the earlier NFHL rendering; exact survey/topology equivalence is not established.',
            'mask_purpose':'UNKNOWN','regulatory_role_of_hidden_graphics':'UNKNOWN',
            'geometry_proposals':'UNCHANGED, proposed_not_accepted','legal_applicability':'UNKNOWN'},
        'finding_reviews':[
            {'finding_id':'TL-F-0105','status':'in_progress','priority':'medium','report_pointer':'/conclusion',
             'next_action':'Clarify the regulatory purpose of the 0443D PDF mask and the status of the covered graphics with authoritative evidence; continue revision coverage and LUPC adoption qualification.',
             'note':'The apparent blank-map discrepancy is explained by opaque white MASK OCG 103. Hiding only that group in an in-memory view reveals existing hazard graphics at the prior locator; restoring it exactly reproduces the original pixels. This supersedes uncertainty about missing graphic content, not the published presentation or regulatory interpretation. Source PDF preserved; hidden graphics are diagnostic only.'},
            {'finding_id':'TL-F-0026','status':'in_progress','priority':'high','report_pointer':'/review',
             'next_action':'Review the two existing exact-version shell/hole proposals and any future FEMA acceptance layer while preserving mask-purpose, regulatory-adoption and source-version qualifications.',
             'note':'Additional map evidence explains why the smaller polygon appeared uncorroborated in the default 0443D display: an opaque MASK layer covers the region. Underlying graphics provide visual context but do not certify the exact vertex touch or legal applicability. Candidate hashes and original exclusions are unchanged; neither proposal accepted.'}]}


def prepare_load(report,output,current):
    prepare(BASE,output,BASE/'report.json');manifest=json.loads((output/'manifest.json').read_bytes())
    def archive(data):
        sha=digest(data);key='sha256/'+sha+'.response';require(len(data)<=52428800,'Object too large')
        (output/'objects'/key).write_bytes(data);manifest['objects'][key]={'sha256':sha,'bytes':len(data)}
    for path,sha in report['inputs'].items():
        data=(ROOT/path).read_bytes();require(digest(data)==sha,'Changed dependency');archive(data)
    pdf=(ROOT/PDF_PATH).read_bytes();require(digest(pdf)==PDF_SHA,'Changed PDF')
    for part in report['large_document_evidence']['parts']:archive(pdf[part['offset']:part['offset']+part['bytes']])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows={r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    sha=digest((BASE/'report.json').read_bytes());sql=(output/'load.sql').read_text().removesuffix('COMMIT;\n')
    for r in report['finding_reviews']:
        fid=r['finding_id'];event={k:v for k,v in r.items() if k!='report_pointer'}
        event.update(event_id=digest(canonical([fid,sha,'map-mask']).encode()),actor='TerraLucid FEMA map display investigation',evidence_refs=['audit:'+sha+'#'+r['report_pointer']])
        occurrence=digest(canonical([fid,sha,'map-mask']).encode())
        sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(occurrence),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        sql+='SELECT ingest.record_finding_event('+jsql(event)+','+literal(rows[fid]['event_id'])+');\n'
    (output/'load.sql').write_text(sql+'COMMIT;\n')
    print(json.dumps({'audit_sha256':sha,'archive_objects':len(manifest['objects'])}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path)
    p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path);a=p.parse_args()
    if a.verify_download:
        if not a.prepared:p.error('--verify-download requires --prepared')
        print(verify(a.prepared,a.verify_download));data=(BASE/'report.json').read_bytes()
        require('sha256/'+digest(data)+'.response' in json.loads((a.prepared/'manifest.json').read_bytes())['objects'],'Report not in archive')
        restore(json.loads(data)['large_document_evidence'],a.verify_download);print('Original PDF reconstructed and verified')
    else:
        if a.prepare and not a.current:p.error('--prepare requires --current')
        r=build();(BASE/'report.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(r,a.prepare,a.current)
        else:print(json.dumps(r['conclusion']))
