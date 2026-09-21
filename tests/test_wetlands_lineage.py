import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_wetlands_lineage import coverage,projected
from shapely.geometry import box,Point
from pyproj import Transformer
from pyproj.enums import TransformDirection

class LineageChecks(unittest.TestCase):
    def test_overlapping_footprints_do_not_hide_uncovered_area(self):
        result=coverage(box(0,0,10,10),[(1,box(0,0,6,10)),(2,box(4,0,8,10))])
        self.assertEqual(result['uncovered_m2'],20)
        self.assertEqual(len(result['positive_area_projects']),2)
    def test_touch_is_separate_from_positive_area_lineage(self):
        result=coverage(box(0,0,10,10),[(1,box(0,0,10,10)),(2,box(10,0,20,10))])
        self.assertEqual(result['uncovered_m2'],0)
        self.assertEqual(result['boundary_touch_projects'],[2])
        self.assertEqual(len(result['positive_area_projects']),1)
    def test_empty_footprints_preserve_unknown_gap(self):
        self.assertEqual(coverage(box(0,0,10,10),[])['uncovered_m2'],100)
    def test_explicit_datum_direction_and_axes_roundtrip(self):
        lon,lat=-68.25,44.78
        wlat,wlon=Transformer.from_pipeline('ESRI:108190').transform(lat,lon,direction=TransformDirection.INVERSE)
        x,y=Transformer.from_crs(4326,3857,always_xy=True).transform(wlon,wlat)
        expected=Point(*Transformer.from_crs(4269,5070,always_xy=True).transform(lon,lat))
        self.assertLess(projected(Point(x,y),'ESRI:108190').distance(expected),0.000001)
        self.assertGreater(projected(Point(x,y),'EPSG:1188').distance(expected),1)
