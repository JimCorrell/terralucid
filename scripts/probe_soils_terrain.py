"""Read-only catalog discovery; no feature load, suitability or coverage claim."""
import argparse,hashlib,json,urllib.request,urllib.parse
from pathlib import Path
from datetime import datetime,timezone
from pyproj import Transformer

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--county-capture',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    county=json.loads(args.county_capture.read_bytes())
    bounds=Transformer.from_crs(26919,4326,always_xy=True).transform_bounds(*county['county_bounds_26919'],densify_pts=21)
    report={'started_at':datetime.now(timezone.utc).isoformat(),'scope':'county-containing rectangle, not exact county coverage','county_boundary_sha256':county['county_wkb_sha256'],'bbox_4326':bounds,'requests':[]}
    def fetch(name,url,payload=None):
        entry={'name':name,'url':url,'payload':payload,'retrieved_at':datetime.now(timezone.utc).isoformat()}
        data=json.dumps(payload).encode() if payload else None
        request=urllib.request.Request(url,data=data,headers={'User-Agent':'TerraLucid source-readiness audit','Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=60) as response:
                raw=response.read();entry.update(status=response.status,final_url=response.url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            (args.output/(name+'.response')).write_bytes(raw)
            result=json.loads(raw)
        except Exception as e:
            entry['error']=str(e);result=None
        report['requests'].append(entry);return result
    soils=fetch('soil-survey-catalog','https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest',{'query':"SELECT areasymbol, areaname, saverest FROM sacatalog WHERE areasymbol LIKE 'ME%' ORDER BY areasymbol",'format':'JSON'})
    report['soil_catalog']=soils
    # These names identify candidates, not the final county spatial membership.
    profile_query="""SELECT l.areasymbol, COUNT(DISTINCT m.mukey) AS mapunits,
      COUNT(DISTINCT c.cokey) AS components, COUNT(DISTINCT h.chkey) AS horizons
      FROM legend l INNER JOIN mapunit m ON m.lkey=l.lkey
      LEFT JOIN component c ON c.mukey=m.mukey
      LEFT JOIN chorizon h ON h.cokey=c.cokey
      WHERE l.areasymbol IN ('ME615','ME620') GROUP BY l.areasymbol ORDER BY l.areasymbol"""
    report['soil_candidate_profile']=fetch('soil-candidate-profile','https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest',{'query':profile_query,'format':'JSON'})
    # Inventory every page. Bounds select candidates only, not valid-data pixels.
    items=[];offset=0;total=None
    while total is None or offset<total:
        params={'datasets':'Digital Elevation Model (DEM) 1 meter','bbox':','.join(map(str,bounds)),'max':1000,'offset':offset}
        page=fetch('dem-products-'+str(offset),'https://tnmaccess.nationalmap.gov/api/v1/products?'+urllib.parse.urlencode(params))
        if not page or page.get('errors'):break
        if total is None:total=page['total']
        if page['total']!=total:raise ValueError('Catalog total changed during pagination')
        batch=page.get('items',[])
        if not batch:break
        items.extend(batch);offset+=len(batch)
    ids=[i['sourceId'] for i in items]
    report['terrain']={'catalog_total':total,'retrieved':len(items),'unique_source_ids':len(set(ids)),
       'pagination_complete':total is not None and len(items)==total and len(set(ids))==len(items),
       'size_bytes_sum':sum(i.get('sizeInBytes') or 0 for i in items),
       'products':[{k:i.get(k) for k in ['sourceId','title','publicationDate','lastUpdated','sizeInBytes','boundingBox','metaUrl','downloadURL']} for i in items]}
    state=fetch('maine-2024-dem','https://gis.maine.gov/image/rest/services/DEM/Maine_Elevation_DEM_2024/ImageServer?f=pjson')
    if state:report['maine_service']={k:state.get(k) for k in ['name','description','extent','spatialReference','pixelSizeX','pixelSizeY','copyrightText']}
    report['completed_at']=datetime.now(timezone.utc).isoformat()
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'soil_catalog':soils,'terrain_total':total,'terrain_retrieved':len(items),'terrain_bytes':report['terrain']['size_bytes_sum'],'errors':[r for r in report['requests'] if 'error' in r]},indent=2))
if __name__=='__main__':main()
