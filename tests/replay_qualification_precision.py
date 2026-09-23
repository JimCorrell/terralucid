"""Offline regression over PR54 private captures; emits aggregate evidence only."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import shapely
from qualify_area import qualify,currency,method_hash

def without_coverage(value):
    if isinstance(value,list):
        return [without_coverage(v) for v in value if v!='incomplete_geometric_coverage']
    if isinstance(value,dict):
        return {k:without_coverage(v) for k,v in value.items()
                if k not in ('coverage','aoi_coverage_by_orneville_civil_boundary','method_sha256')}
    return value

def run(root):
    cases=[]
    for name in ['orneville_parcel','overlapping_sources','parcel_near_hold','accepted_zoning_area']:
        raw=(root/name/'capture.json').read_bytes()
        capture=json.loads(raw)
        previous=json.loads((root/name/'packet.json').read_bytes())
        current=qualify(capture)
        assert without_coverage(previous)==without_coverage(current),name
        assert 'qualification_method_changed' in currency(previous,capture['context'])['reasons']
        changes={}
        for topic in ('identity','zoning','wetlands'):
            before=previous['topics'][topic];after=current['topics'][topic]
            assert ('incomplete_geometric_coverage' in after['reasons'])==(after['coverage']['state']!='full_geometric')
            assert 0<=after['coverage']['fraction']<=1
            changes[topic]={'before':before['coverage'],'after':after['coverage']}
        cases.append({'case':name,'capture_file_sha256':hashlib.sha256(raw).hexdigest(),
                      'coverage':changes,'noncoverage_evidence_and_permissions_unchanged':True,
                      'previous_packet_requires_method_revisit':True})
    assert cases[1]['coverage']['identity']['after']['state']=='full_geometric'
    assert cases[1]['coverage']['zoning']['after']['state']=='partial_geometric'
    assert cases[2]['coverage']['zoning']['after']['state']=='partial_geometric'
    return {'follow_up':'qualification-numerical-precision','status':'resolved_for_observed_cases',
            'mode':'offline replay of PR54 captures; no live currency claim or database writes',
            'method_sha256':method_hash(),'shapely':shapely.__version__,'geos':shapely.geos_version_string,'cases':cases}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_capture_directory',type=Path)
    args=parser.parse_args()
    print(json.dumps(run(args.private_capture_directory),indent=2))
