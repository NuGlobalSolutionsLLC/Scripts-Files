import copy
import struct
import unittest

from build import ANALYTES, REQUIRED, make_section, selected, page
from shapefile import dbf, shapes


def fixture():
    rows=[]
    for analyte in ANALYTES:
        rows.append(dict(Well_ID='W-1',SDate='2025-03-11',Matrix='GW',Analyte=analyte,Result=0,
                         Transect='A_A01',X=500,exg_tos_el=1600,exg_bos_el=1200,X_1=500,
                         exg_tos__1=1600,exg_bos__1=1200,PerpDist=2))
    return {'fields':list(REQUIRED),'prj':'NAD_1983_StatePlane_Texas_North_Central_FIPS_4202_Feet',
            'rows':rows,'shapes':[[(500,1600),(500,1200)] for _ in rows]}


class SelectionTests(unittest.TestCase):
    def test_authorized_production_review_keeps_position_warning(self):
        args = ('AA', 'mr', '<svg></svg>', 'data.json', 'app.js', 'style.css')
        self.assertIn('Local validation preview — not deployed', page(*args))
        live = page(*args, production_review=True)
        self.assertNotIn('not deployed', live)
        self.assertIn('screen positioning is awaiting GIS review', live)
        self.assertIn('Position comparison', live)

    def test_latest_does_not_mean_largest(self):
        rows=[{'date':'2024-01-01','result':99},{'date':'2025-01-01','result':0},{'date':'2025-01-01','result':1}]
        self.assertEqual(selected(rows,'mr'),rows[1:])
        self.assertEqual(selected(rows,'max'),rows[:1])

    def test_exact_duplicates_keep_source_provenance(self):
        data=fixture()
        data['rows'] += copy.deepcopy(data['rows'])
        data['shapes'] += copy.deepcopy(data['shapes'])
        result,report=make_section('AA',data,{})
        self.assertEqual(report['sourceRows'],6)
        self.assertEqual(report['uniqueMeasurementKeys'],3)
        self.assertEqual(report['repeatedRows'],3)
        self.assertEqual(result['wells'][0]['samples']['TCE'][0]['sourceRows'],[1,4])

    def test_conflicting_coordinates_are_not_silently_selected(self):
        data=fixture()
        data['rows'][0]['X_1']=510
        result,report=make_section('AA',data,{})
        self.assertEqual(len(report['shapeAttributeDisagreements']),1)
        self.assertEqual(len(report['selectedResultReview']),2)
        self.assertEqual(result['wells'][0]['samples']['TCE'][0]['joined'],[(510,1600,1200)])

    def test_all_analytes_are_required(self):
        data=fixture(); data['rows']=data['rows'][:1]; data['shapes']=data['shapes'][:1]
        with self.assertRaisesRegex(ValueError,'three analytes'):
            make_section('AA',data,{})

    def test_invalid_sources_fail_closed(self):
        for key,value in [('Result',-1),('PerpDist',20),('Matrix','SW'),('SDate','2025-02-30'),
                          ('Well_ID',None),('Transect','B_B01'),('exg_tos_el',1000),('X',550)]:
            with self.subTest(key=key):
                data=fixture(); data['rows'][0][key]=value
                with self.assertRaises(ValueError): make_section('AA',data,{})

    def test_prj_and_required_fields_fail_closed(self):
        data=fixture(); data['prj']='WGS84'
        with self.assertRaises(ValueError): make_section('AA',data,{})
        data=fixture(); data['fields'].remove('SDate')
        with self.assertRaises(ValueError): make_section('AA',data,{})


class BinaryTests(unittest.TestCase):
    def test_truncated_and_invalid_headers_are_rejected(self):
        for value in [b'',b'X'*100]:
            with self.assertRaises(ValueError): dbf(value,'utf-8')
            with self.assertRaises(ValueError): shapes(value,value)

    def test_shx_offset_must_match(self):
        shp=bytearray(128); shx=bytearray(108)
        for blob in [shp,shx]:
            struct.pack_into('>I',blob,0,9994); struct.pack_into('>I',blob,24,len(blob)//2)
            struct.pack_into('<II',blob,28,1000,1)
        struct.pack_into('>II',shp,100,1,10)
        struct.pack_into('<Idd',shp,108,1,100,200)
        struct.pack_into('>II',shx,100,50,10)
        self.assertEqual(shapes(shp,shx),[[(100,200)]])
        struct.pack_into('>I',shx,100,51)
        with self.assertRaisesRegex(ValueError,'index mismatch'): shapes(shp,shx)


if __name__ == '__main__':
    unittest.main()
