#!/usr/bin/env python3
"""Compare only captured, exactly aligned raster blocks; never fetch missing pixels."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import re
import tempfile
import numpy as np
import rasterio
from rasterio.windows import Window
from investigate_terrain_readiness import sha


def run(evidence, output):
    report=json.loads((evidence/'report.json').read_text())
    sources=json.loads((evidence/'sources.json').read_text()); arrays=[]
    for project in report['projects']:
        r=project['raster']; samples={}
        with tempfile.NamedTemporaryFile(suffix='.tif') as f:
            f.truncate(r['current_file_bytes'])
            for src in sources:
                if src['url']!=r['url']:continue
                if sha(evidence/src['file'])!=src['sha256']:raise ValueError('Capture hash mismatch')
                match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',src['content_range'])
                if src['etag']!=r['etag'] or int(match[3])!=r['current_file_bytes']:raise ValueError('Version mismatch')
                f.seek(int(match[1]));f.write((evidence/src['file']).read_bytes())
            f.flush()
            with rasterio.open(f.name) as ds:
                for s in r['samples']:
                    key=tuple(s[k] for k in ('column','row','width','height'))
                    a=ds.read(1,window=Window(*key),masked=True)
                    if int(np.ma.getmaskarray(a).sum())!=s['masked']:raise ValueError('Sample reconstruction mismatch')
                    samples[key]=a
        arrays.append((project['project'],r,samples))
    pairs=[]
    for i,(an,ar,aa) in enumerate(arrays):
        for bn,br,ba in arrays[i+1:]:
            if any(ar[k]!=br[k] for k in ('crs_wkt','bounds','width','height','resolution')):continue
            shared=sorted(set(aa)&set(ba)); diffs=[]; union=0
            for key in shared:
                a,b=aa[key],ba[key]
                av=~np.ma.getmaskarray(a)&np.isfinite(a.data);bv=~np.ma.getmaskarray(b)&np.isfinite(b.data)
                both=av&bv;union+=int((av|bv).sum())
                diffs.append(b.data[both].astype('float64')-a.data[both].astype('float64'))
            if not shared:continue
            d=np.concatenate(diffs)
            pairs.append({'a':an,'b':bn,'shared_blocks':len(shared),'union_valid_pixels':union,'both_valid_pixels':len(d),
                'b_minus_a_median':float(np.median(d)) if len(d) else None,
                'absolute_difference_p95':float(np.percentile(abs(d),95)) if len(d) else None,
                'absolute_difference_max':float(abs(d).max()) if len(d) else None})
    result={'evidence_state':'DERIVED','method_sha256':sha(__file__),'input_report_sha256':sha(evidence/'report.json'),
        'pairs':pairs,'limits':['Raw differences of matching sampled native pixels, without datum adjustment. Not an accuracy assessment or preferred-source rule.',
        'Samples are not clipped to county; no claim about county coverage, statistical representativeness or full-project seams.']}
    output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence,a.output)
