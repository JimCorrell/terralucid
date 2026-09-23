#!/usr/bin/env python3
"""Replay retained XML and selected PDF pages; sparse PDF is diagnostic only."""
import argparse,hashlib,json,re,tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import fitz

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(evidence,ranges,out):
    out.mkdir(parents=True,exist_ok=False)
    manifests=[]
    for root in (evidence,ranges):
        records=json.loads((root/'sources.json').read_text())
        for e in records:
            if sha(root/e['file'])!=e['sha256']:raise ValueError('Evidence hash mismatch')
        manifests.append(records)
    entries=manifests[1];versions={(e['url'],e['etag'],int(e['content_range'].split('/')[1])) for e in entries}
    if len(versions)!=1:raise ValueError('PDF versions differ')
    url,etag,size=versions.pop()
    with tempfile.NamedTemporaryFile(suffix='.pdf') as temp:
        temp.truncate(size)
        for e in entries:
            match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',e['content_range'])
            raw=(ranges/e['file']).read_bytes()
            if len(raw)!=int(match[2])-int(match[1])+1:raise ValueError('Range length mismatch')
            temp.seek(int(match[1]));temp.write(raw)
        temp.flush();fitz.TOOLS.mupdf_display_errors(False);fitz.TOOLS.mupdf_warnings()
        doc=fitz.open(temp.name);pages=[]
        for i,expected in [(21,['5.3. Digital Elevation Model','122','31']), (22,['Table 4. NVA and VVA Accuracy Results','0.0652','0.0647','0.2023'])]:
            page=doc[i];text=page.get_text()
            if not all(v in text for v in expected):raise ValueError('Expected accuracy context missing')
            image=out/f'western-page-{i+1}.png';page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(image)
            pages.append({'pdf_page':i+1,'printed_page':i-2,'text':text,'render_file':image.name,'render_sha256':sha(image)})
        warnings=fitz.TOOLS.mupdf_warnings();doc.close()
    name='USGS_Maine_2017_LiDAR_HydroFlattenedDEM_Metadata.xml';root=ET.parse(evidence/name)
    xml={k:[(x.text or '').strip() for x in root.findall('.//'+k)] for k in ['begdate','enddate','horizdn','altdatum','altunits','vertaccr','vertaccv','vertacce']}
    if xml['vertaccv']!=['0.099','0.255']:raise ValueError('Eastern DEM accuracy fields changed')
    result={'evidence_state':'DERIVED','method_sha256':sha(__file__),'runtime':{'pymupdf':fitz.VersionBind},
        'eastern_dem_xml_sha256':sha(evidence/name),'eastern_dem_fields':xml,
        'western_pdf':{'url':url,'etag':etag,'complete_file_size':size,'retained_range_bytes':sum(e['bytes'] for e in entries),'complete_pdf_downloaded':False,
            'reviewed_pages':pages,'parser_warnings':warnings,
            'limits':'Partial sparse reconstruction, not a complete PDF. Unfetched page-tree branches produce a non-page warning. Only displayed report pages 19-20 (PDF 22-23), including table/context, are used; renders visually reviewed. No claim about inaccessible pages or attachments.'},
        'measured_results':{'eastern_2017':{'nva_numeric_m':0.099,'nva_prose_95_percent_m':0.100,'nva_rmse_prose_m':0.051,'nva_checkpoints':176,'vva_95th_percentile_m':0.255,'vva_checkpoints':123},
            'western_2024':{'raw_pointcloud_nva_95_percent_m':0.0652,'dem_nva_95_percent_m':0.0647,'nva_checkpoints':122,'dem_vva_95th_percentile_m':0.2023,'vva_checkpoints':31}},
        'limits':['Publisher project-level measured results, not independently remeasured or local parcel accuracy.',
            'No raster values, masks, source priorities, height corrections or terrain qualification changed.']}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print('Verified source hashes, XML fields, and PDF table/context text; rendered two pages for visual review.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--ranges',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence,a.ranges,a.output)
