#!/usr/bin/env python3
"""Stream the verified county inputs through bounded COPY statements.

Changes transport only. Every source ID/input checksum must match the audit.
COPY is for an empty county batch; it is not an upsert/replay mechanism.
"""
import argparse,csv,json,shutil
from collections import defaultdict
from pathlib import Path
from prepare_source_staging import digest

PREFIX='INSERT INTO ingest.county_inventory_feature(audit_sha256,source_id,object_id,input_text) VALUES '
SUFFIX=' ON CONFLICT DO NOTHING;\n'


def values(text):
    """Decode the generator's four-column SQL literals; reject other SQL syntax."""
    i=0
    def expect(s):
        nonlocal i
        if not text.startswith(s,i):raise ValueError('Unexpected generated SQL syntax')
        i+=len(s)
    def quoted():
        nonlocal i
        expect("'");parts=[]
        while True:
            j=text.index("'",i);parts.append(text[i:j]);i=j+1
            if i<len(text) and text[i]=="'":parts.append("'");i+=1
            else:return ''.join(parts)
    while i<len(text):
        expect('(');audit=quoted();expect(',');source=quoted();expect(',')
        j=text.index(',',i);oid=int(text[i:j]);i=j+1;raw=quoted();expect(')')
        yield audit,source,oid,raw
        if i<len(text):expect(',')


def repack(prepared,report,output):
    expected=json.loads(report.read_bytes());audit=digest(report.read_bytes());seen=defaultdict(dict)
    output.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(prepared/'manifest.json',output/'manifest.json')
    source_hash=__import__('hashlib').sha256();total=0
    with (prepared/'load.sql').open() as src,(output/'load.sql').open('w',newline='') as out:
        writer=csv.writer(out,lineterminator='\n')
        for line in src:
            source_hash.update(line.encode())
            if not line.startswith(PREFIX):
                out.write(line)
                if line=='BEGIN;\n':
                    out.write("SET LOCAL statement_timeout=0;\n")
                    out.write("DO $$ BEGIN IF EXISTS(SELECT 1 FROM ingest.county_inventory_feature WHERE audit_sha256='"+audit+"') THEN RAISE EXCEPTION 'COPY transfer requires an empty county batch'; END IF; END $$;\n")
                continue
            if not line.endswith(SUFFIX):raise ValueError('Unexpected feature statement suffix')
            rows=list(values(line[len(PREFIX):-len(SUFFIX)]))
            for offset in range(0,len(rows),25):
                out.write('COPY ingest.county_inventory_feature(audit_sha256,source_id,object_id,input_text) FROM STDIN WITH (FORMAT csv);\n')
                for a,sid,oid,raw in rows[offset:offset+25]:
                    if a!=audit or oid in seen[sid]:raise ValueError('Changed audit or duplicate source identity')
                    seen[sid][oid]=digest(raw.encode());writer.writerow((a,sid,oid,raw));total+=1
                out.write('\\.\n')
    actual={sid:{'count':len(rows),'sha256':digest(''.join(f'{oid}:{sha}\n' for oid,sha in sorted(rows.items())).encode())} for sid,rows in seen.items()}
    if actual!=expected['record_manifest']:
        (output/'load.sql').unlink();raise ValueError('Repacked input fingerprints differ')
    h=__import__('hashlib').sha256()
    with (output/'load.sql').open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    proof={'audit_sha256':audit,'feature_rows':total,'record_manifest_matches':True,'original_sql_sha256':source_hash.hexdigest(),'copy_sql_sha256':h.hexdigest(),
           'method_sha256':digest(Path(__file__).read_bytes()),'rows_per_copy':25,'empty_batch_required':True,'statement_timeout':'disabled only inside the load transaction'}
    (output/'transport-verification.json').write_text(json.dumps(proof,indent=2)+'\n');return proof

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(repack(a.prepared,a.report,a.output),indent=2))
