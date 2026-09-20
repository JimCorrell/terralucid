#!/usr/bin/env python3
"""Record the scope of ZP 796 and the unresolved Osborn LOMR incorporation question."""
import argparse
import json
from pathlib import Path
import fitz
from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql, verify

BASE = ROOT/'research/osborn-flood-adoption'
METHOD = 'scripts/investigate_osborn_flood_adoption.py'


def require(value, message):
    if not value: raise ValueError(message)


def build():
    inputs, evidence, payloads = {}, {}, {}
    def dependency(path, expected=None):
        data = (ROOT/path).read_bytes()
        require(expected is None or digest(data) == expected, 'Changed dependency: '+path)
        inputs[path] = digest(data)
        return data
    dependency('research/lupc-currency/report.json','027c4170c9fc7748d5f40b64ed45cca8c11ec09a90a1bca473f1333a9fc28b9e')
    dependency('research/fema-mask-purpose/report.json','769cff43b96b0c5fc909e6dd7821bf9d96e5ac1cf21c2170c718c36f183d95e1')
    chapter = dependency('research/lupc-currency/runs/publication/chapter-10.response','167196d1e19ddc9c02e8b7f2b0921049ce5609cdbee2eecef38f1d93365ef274')
    review = json.loads(dependency('research/osborn-flood-adoption/review.json'))
    for path in ['research/osborn-flood-adoption/publisher-questions.md','research/osborn-flood-adoption/probes.json',
                 'research/osborn-flood-adoption/followup-probes.json','scripts/prepare_source_staging.py','scripts/collect_document_evidence.py']:
        dependency(path)
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            require(Path(r['response_file']).name == r['response_file'], 'Unsafe response path')
            path = log.parent/r['response_file']; data = path.read_bytes()
            require(digest(data) == r['sha256'] and len(data) == r['bytes'], 'Changed source bytes')
            evidence[log.parent.name+'/'+r['id']] = dict(r,response_path=path.relative_to(BASE).as_posix())
            require(r['id'] not in payloads,'Duplicate probe')
            payloads[r['id']] = (r,data)
    for name in ['zp796-probe','osborn-map','chapter-4','rules-index','flood-rule-basis','incorporation-reference']:
        require(payloads[name][0]['http_status'] == 200, 'Missing primary evidence: '+name)
    require(digest(payloads['osborn-map'][1]) == '9de0a5f83415be0433e57d62aba24382dfe71a51ea938a56af595b11fc046beb','Map changed; review again')
    documents = {n:fitz.open(stream=payloads[n][1],filetype='pdf') for n in ['zp796-probe','chapter-4','flood-rule-basis']}
    documents['chapter-10'] = fitz.open(stream=chapter,filetype='pdf')
    require(len(documents['zp796-probe']) == 10 and 'Osborn' in documents['zp796-probe'][3].get_text(),'Wrong ZP 796 document')
    renderings = {}
    selections = {'zp796-probe':[1,2,3,4,10],'chapter-4':[49],'chapter-10':[133,251],'flood-rule-basis':[1,2]}
    for name,pages in selections.items():
        for page in pages:
            pix = documents[name][page-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3))
            path = BASE/'diagnostics'/(name+'-'+str(page)+'.png'); path.parent.mkdir(exist_ok=True)
            data = pix.tobytes('png'); path.write_bytes(data)
            relative = path.relative_to(ROOT).as_posix(); dependency(relative)
            renderings[name+'/'+str(page)] = {'path':relative,'sha256':digest(data),'pdf_page':page,'display':'default; source unchanged'}
    return {'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),
      'evidence':evidence,'inputs':inputs,'review':review,'renderings':renderings,
      'runtime':{'PyMuPDF':fitz.VersionBind,'MuPDF':fitz.VersionFitz},
      'checks':{'osborn_map_identical_to_prior_review':True,'no_geometry_or_screening_change':True},
      'finding_reviews':[
       {'finding_id':'TL-F-0109','status':'in_progress','priority':'medium','report_pointer':'/review',
        'note':'Signed ZP 796 confirms the August 2024 Osborn map amendment was clerical, retaining existing zoning. Chapter 4 permits staff adoption of amended FEMA maps; authority does not establish a specific action. The existing 2016 reference and Chapter 10 do not resolve incorporation of case 22-01-0871P in this review. Non-adoption is not established. All other currency/omitted-protection qualifications remain.',
        'next_action':review['next_action']},
       {'finding_id':'TL-F-0105','status':'in_progress','priority':'medium','report_pointer':'/review/conclusion',
        'note':'LUPC incorporation review locates signed ZP 796 but establishes only clerical scope. Federal finalization remains corroborated; LUPC applicability and the FEMA mask question remain separate unknowns. Preserve Zone X/SFHA distinctions; no geometry proposal accepted.',
        'next_action':'Obtain the authoritative 0443D mask clarification and LUPC incorporation record/interpretation for case 22-01-0871P; retain separate revision currency and parcel applicability checks.'}]}


def prepare_load(report, output, current):
    prepare(BASE,output,BASE/'report.json')
    manifest = json.loads((output/'manifest.json').read_bytes())
    for path,sha in report['inputs'].items():
        data = (ROOT/path).read_bytes(); require(digest(data) == sha,'Changed input')
        require(len(data) <= 52428800,'Oversized object')
        key = 'sha256/'+sha+'.response'; (output/'objects'/key).write_bytes(data)
        manifest['objects'][key] = {'sha256':sha,'bytes':len(data)}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows = {r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    sha = digest((BASE/'report.json').read_bytes()); sql = (output/'load.sql').read_text().removesuffix('COMMIT;\n')
    for r in report['finding_reviews']:
        fid = r['finding_id']; eid = digest(canonical([fid,sha,'flood-adoption']).encode())
        event = {k:v for k,v in r.items() if k != 'report_pointer'}
        event.update(event_id=eid,actor='TerraLucid Osborn flood adoption review',evidence_refs=['audit:'+sha+'#'+r['report_pointer']])
        sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(eid),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        sql += 'SELECT ingest.record_finding_event('+jsql(event)+','+literal(rows[fid]['event_id'])+');\n'
    (output/'load.sql').write_text(sql+'COMMIT;\n')
    print(json.dumps({'audit_sha256':sha,'archive_objects':len(manifest['objects'])}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path)
    p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path)
    a = p.parse_args()
    if a.verify_download:
        if not a.prepared:p.error('--verify-download requires --prepared')
        require('sha256/'+digest((BASE/'report.json').read_bytes())+'.response' in json.loads((a.prepared/'manifest.json').read_bytes())['objects'],'Report absent from archive')
        print(verify(a.prepared,a.verify_download))
    else:
        if a.prepare and not a.current:p.error('--prepare requires --current')
        report = build();(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(report,a.prepare,a.current)
        else:print(json.dumps(report['review']['conclusion']))
