#!/usr/bin/env python3
"""Preserve base-panel comparison and final notice without interpreting hidden graphics as law."""
import argparse
import io
import json
import zipfile
from pathlib import Path
import fitz
from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql, verify
from investigate_osborn_fema import parts, restore
from investigate_fema_map_mask import PDF_PATH, PDF_SHA, require

BASE = ROOT / 'research/fema-mask-purpose'
METHOD = 'scripts/investigate_fema_mask_purpose.py'
PRIOR_SHA = 'b06c8d155bc23b05a3bc0f7d221a7ff53bc2924021d379762ea7731515a00e35'


def build():
    inputs, evidence = {}, {}
    def dependency(path, expected=None):
        data = (ROOT/path).read_bytes()
        require(expected is None or digest(data) == expected, 'Changed input: '+path)
        inputs[path] = digest(data)
        return data
    prior = json.loads(dependency('research/fema-map-discrepancy/report.json', PRIOR_SHA))
    pdf = (ROOT/PDF_PATH).read_bytes()
    require(digest(pdf) == PDF_SHA, 'Changed original determination')
    document = prior['large_document_evidence']
    require(parts(pdf) == document['parts'], 'Changed PDF parts')
    review = json.loads(dependency('research/fema-mask-purpose/review.json'))
    dependency('research/osborn-fema/report.json', '2f106e1b19fa2b13415741a109d34f1f9dbc4fdb04cf67e77fe882325aebe5ff')
    dependency('research/osborn-fema/runs/catalog/catalog-osborn.response')
    payloads = {}
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            require(Path(r['response_file']).name == r['response_file'], 'Unsafe path')
            path = log.parent/r['response_file']; data = path.read_bytes()
            require(digest(data) == r['sha256'] and len(data) == r['bytes'], 'Changed capture')
            evidence[log.parent.name+'/'+r['id']] = dict(r, response_path=path.relative_to(BASE).as_posix())
            payloads[r['id']] = (r, data)
    base_record, base_bytes = payloads['base-panel-0443']
    notice_record, notice_bytes = payloads['final-notice']
    require(base_record['http_status'] == notice_record['http_status'] == 200, 'Missing primary evidence')
    with zipfile.ZipFile(io.BytesIO(base_bytes)) as z:
        require(set(z.namelist()) == {'23009C0443D.png','23009C0443D.pgw','READ-ME.pdf'}, 'Unexpected base panel package')
        members = {n:{'sha256':digest(z.read(n)), 'bytes':len(z.read(n))} for n in z.namelist()}
        # Render only the original PNG. No world-file registration or alignment is inferred.
        image_bytes = z.read('23009C0443D.png')
    base_doc = fitz.open(stream=image_bytes, filetype='png')
    revision = fitz.open(stream=pdf, filetype='pdf')
    notice = fitz.open(stream=notice_bytes, filetype='pdf')
    require(notice.page_count == 4 and '230595' in notice[2].get_text() and 'Osborn' in notice[2].get_text(), 'Wrong final notice')
    renderings = {}
    for label, doc, page in [('base-2016',base_doc,0),('revision-published-2024',revision,7),('notice-50604',notice,0),('notice-50606',notice,2)]:
        p = doc[page]; pix = p.get_pixmap(matrix=fitz.Matrix(1200/p.rect.width,1200/p.rect.width))
        path = BASE/'diagnostics'/(label+'.png'); path.parent.mkdir(exist_ok=True)
        data = pix.tobytes('png'); path.write_bytes(data)
        relative = path.relative_to(ROOT).as_posix(); dependency(relative)
        renderings[label] = {'path':relative,'sha256':digest(data),'width':pix.width,'height':pix.height,'display':'published/default; no layer toggle'}
    for path in ['scripts/prepare_source_staging.py','scripts/investigate_osborn_fema.py','scripts/investigate_fema_map_mask.py','scripts/collect_document_evidence.py','research/fema-mask-purpose/probes.json','research/fema-mask-purpose/publisher-questions.md']:
        dependency(path)
    require((ROOT/PDF_PATH).read_bytes() == pdf, 'Source modified')
    return {'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),
        'scope':'Historical 2016 base panel compared with archived 2024 revision and finalization notice; no current legal certification',
        'prior_audit_sha256':PRIOR_SHA,'evidence':evidence,'inputs':inputs,'large_document_evidence':document,
        'base_package_members':members,'renderings':renderings,'runtime':{'PyMuPDF':fitz.VersionBind,'MuPDF':fitz.VersionFitz},
        'review':review,'checks':{'source_PDF_bytes_unchanged':True,'no_geometry_or_screening_mutation':True},
        'finding_reviews':[
          {'finding_id':'TL-F-0105','status':'in_progress','priority':'medium','report_pointer':'/review',
           'note':'2016 base panel already shows a similar large white Osborn area; legacy mask carry-forward is an inference, not confirmed publisher intent. Federal Register 2024-13142 corroborates finalization of Osborn case 22-01-0871P on May 31, 2024. Neither fact certifies the regulatory role of covered graphics. Originals retained; no correction accepted.',
           'next_action':'Obtain authoritative explanation of the retained 0443D blank area and controlling depiction at FLD_AR_ID 23009C_14660; retain separate current-revision and LUPC adoption checks. Unsent inquiry questions are documented.'},
          {'finding_id':'TL-F-0026','status':'in_progress','priority':'high','report_pointer':'/review/conclusion',
           'note':'Case finalization is independently corroborated; similar blanking predates the revision. Specific hidden graphics remain legally unqualified. The two exact-version structural geometry proposals remain unaccepted and unchanged.',
           'next_action':'Review any future FEMA geometry acceptance separately from legal applicability; carry the unresolved 0443D publisher clarification and adoption/version qualifications.'}]}


def prepare_load(report, output, current):
    prepare(BASE, output, BASE/'report.json')
    manifest = json.loads((output/'manifest.json').read_bytes())
    def archive(data):
        sha = digest(data); key = 'sha256/'+sha+'.response'
        require(len(data) <= 52428800, 'Object too large')
        (output/'objects'/key).write_bytes(data)
        manifest['objects'][key] = {'sha256':sha,'bytes':len(data)}
    for path, sha in report['inputs'].items():
        data = (ROOT/path).read_bytes(); require(digest(data) == sha, 'Changed dependency'); archive(data)
    pdf = (ROOT/PDF_PATH).read_bytes(); require(digest(pdf) == PDF_SHA, 'Changed original')
    for p in report['large_document_evidence']['parts']: archive(pdf[p['offset']:p['offset']+p['bytes']])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows = {r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    sha = digest((BASE/'report.json').read_bytes()); sql = (output/'load.sql').read_text().removesuffix('COMMIT;\n')
    for r in report['finding_reviews']:
        fid = r['finding_id']; eid = digest(canonical([fid,sha,'mask-purpose']).encode())
        event = {k:v for k,v in r.items() if k != 'report_pointer'}
        event.update(event_id=eid,actor='TerraLucid FEMA mask purpose review',evidence_refs=['audit:'+sha+'#'+r['report_pointer']])
        sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(eid),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        sql += 'SELECT ingest.record_finding_event('+jsql(event)+','+literal(rows[fid]['event_id'])+');\n'
    (output/'load.sql').write_text(sql+'COMMIT;\n')
    print(json.dumps({'audit_sha256':sha,'archive_objects':len(manifest['objects'])}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',type=Path); p.add_argument('--current',type=Path)
    p.add_argument('--verify-download',type=Path); p.add_argument('--prepared',type=Path)
    a = p.parse_args()
    if a.verify_download:
        if not a.prepared:p.error('--verify-download requires --prepared')
        print(verify(a.prepared,a.verify_download))
        report = json.loads((BASE/'report.json').read_bytes())
        require('sha256/'+digest((BASE/'report.json').read_bytes())+'.response' in json.loads((a.prepared/'manifest.json').read_bytes())['objects'], 'Report absent from archive')
        restore(report['large_document_evidence'],a.verify_download)
        print('Original PDF reconstructed and verified')
    else:
        if a.prepare and not a.current:p.error('--prepare requires --current')
        report = build(); (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(report,a.prepare,a.current)
        else:print(json.dumps(report['review']['conclusion']))
