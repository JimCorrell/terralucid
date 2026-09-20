#!/usr/bin/env python3
"""Restore captured evidence from a downloaded private checksum archive; no network."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def restore(audit,download):
    pending=[]
    for log in sorted((audit/'runs').glob('*/results.json')):
        for record in json.loads(log.read_bytes()):
            name=record['response_file'];sha=record['sha256']
            if Path(name).name!=name or not re.fullmatch('[0-9a-f]{64}',sha):raise ValueError('Unsafe evidence reference')
            data=(download/'sha256'/(sha+'.response')).read_bytes()
            if hashlib.sha256(data).hexdigest()!=sha or len(data)!=record['bytes']:raise ValueError('Archive checksum mismatch')
            target=log.parent/name
            if target.exists():
                if target.read_bytes()!=data:raise ValueError('Existing evidence differs; refusing to overwrite')
            else:pending.append((target,data))
    if not list((audit/'runs').glob('*/results.json')):raise ValueError('No evidence logs found')
    # Validate all inputs before creating files; preserve existing evidence.
    for target,data in pending:
        with target.open('xb') as f:f.write(data)
    return len(pending)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--download',type=Path,required=True);a=p.parse_args()
    print('Restored',restore(a.audit,a.download),'private evidence files')
