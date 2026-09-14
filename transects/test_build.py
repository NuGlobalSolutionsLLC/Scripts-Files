import copy
import struct
import unittest

from build import ANALYTES, REQUIRED, coordinates, make_section, selected, page
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
    def test_default_position_uses_joined_x_only(self):
        markup = page('BB', 'max', '<svg></svg>', 'data.json', 'app.js', 'style.css')
        self.assertIn('<select id="position"><option value="joinedX" selected>', markup)
        self.assertIn('Corrected X; original screen elevations', markup)
        self.assertIn('Original export (comparison)', markup)
        self.assertIn('Joined X and elevations (comparison)', markup)

    def test_joined_x_does_not_replace_exported_elevations(self):
        row = fixture()['rows'][0]
        row.update(X_1=510, exg_tos__1=1800, exg_bos__1=1400)
        self.assertEqual(coordinates(row, 'joinedX'), (510, 1600, 1200))
        self.assertEqual(coordinates(row, 'shape'), (500, 1600, 1200))
        self.assertEqual(coordinates(row, 'joined'), (510, 1800, 1400))
        with self.assertRaisesRegex(ValueError, 'geometry source'):
            coordinates(row, 'unknown')

    def test_corrected_coordinates_keep_each_raw_rows_x_elevation_pairing(self):
        data = fixture()
        data['rows'][0]['X_1'] = 510
        extra = copy.deepcopy(data['rows'][0])
        extra.update(Transect='A_A02', X=550, X_1=560, exg_tos_el=1800, exg_bos_el=1400)
        data['rows'].append(extra)
        data['shapes'].append([(550, 1800), (550, 1400)])
        result, _ = make_section('AA', data, {})
        sample = result['wells'][0]['samples']['TCE'][0]
        self.assertEqual(sample['joinedX'], [(510, 1600, 1200), (560, 1800, 1400)])
        self.assertEqual(sample['shape'], [(500, 1600, 1200), (550, 1800, 1400)])
        self.assertEqual(sample['sourceRows'], [1, 4])

    def test_epa2_horizontal_correction_preserves_three_exported_intervals(self):
        data = fixture()
        data['rows'], data['shapes'] = [], []
        variants = [(6375.18, 12580, 12490), (6430.95, 11680, 11590), (7442.06, 12780, 12580)]
        for x, top, bottom in variants:
            for analyte in ANALYTES:
                row = fixture()['rows'][0]
                row.update(Well_ID='EPA-2', Transect='B_B09', Analyte=analyte,
                           X=x, exg_tos_el=top, exg_bos_el=bottom, X_1=7442.06,
                           exg_tos__1=12780, exg_bos__1=12580)
                data['rows'].append(row)
                data['shapes'].append([(x, top), (x, bottom)])
        result, report = make_section('BB', data, {})
        for samples in result['wells'][0]['samples'].values():
            self.assertEqual(len(samples), 1)
            self.assertEqual({p[0] for p in samples[0]['joinedX']}, {7442.06})
            self.assertEqual({p[1:] for p in samples[0]['joinedX']}, {p[1:] for p in variants})
            self.assertEqual(samples[0]['joined'], [(7442.06, 12780, 12580)])
        self.assertEqual(report['correctedXSourceRows'], 6)
        self.assertEqual(report['screenElevationSourceRowsDiffer'], 6)

    def test_authorized_production_review_keeps_position_warning(self):
        args = ('AA', 'mr', '<svg></svg>', 'data.json', 'app.js', 'style.css')
        self.assertIn('Local validation preview — not deployed', page(*args))
        live = page(*args, production_review=True)
        self.assertNotIn('not deployed', live)
        self.assertIn('screen positioning is awaiting GIS review', live)
        self.assertIn('Position comparison', live)
        self.assertIn('data-review-banners="shown"', live)

    def test_presentation_only_hides_banners_not_comparison_or_data(self):
        args = ('BB', 'max', '<svg></svg>', 'data.json', 'app.js', 'style.css')
        shown = page(*args, production_review=True)
        hidden = page(*args, production_review=True, hide_review_banners=True)
        self.assertEqual(hidden, shown.replace('data-review-banners="shown"', 'data-review-banners="hidden"'))
        self.assertIn('Position comparison', hidden)
        self.assertIn('Position check', hidden)
        self.assertIn('data-source="data.json"', hidden)
        with self.assertRaisesRegex(ValueError, 'authorized production review'):
            page(*args, hide_review_banners=True)

    def test_release_candidate_preserves_presentation_without_claiming_deployment(self):
        args = ('BB', 'max', '<svg></svg>', 'data.json', 'app.js', 'style.css')
        shown = page(*args, release_candidate=True)
        hidden = page(*args, release_candidate=True, hide_review_banners=True)
        self.assertIn('Release candidate — not deployed', hidden)
        self.assertEqual(hidden, shown.replace('data-review-banners="shown"', 'data-review-banners="hidden"'))
        self.assertIn('<option value="joinedX" selected>', hidden)
        self.assertIn('Position comparison', hidden)
        self.assertIn('data-source="data.json"', hidden)
        with self.assertRaisesRegex(ValueError, 'either a release candidate or production review'):
            page(*args, production_review=True, release_candidate=True)

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
