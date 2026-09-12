"""Independent source-to-output reconciliation and offline page/asset checks."""
import argparse
import collections
import hashlib
import json
import pathlib
import re

from shapefile import archive, require


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=pathlib.Path,required=True)
    parser.add_argument('--transects',type=pathlib.Path,required=True)
    parser.add_argument('--aa',type=pathlib.Path,required=True)
    args=parser.parse_args()
    sections=['AA','BB','CC','DD','EE','FF']
    datasets=archive(args.transects,{f's2{s.lower()}_mr' for s in sections[1:]})
    datasets.update(archive(args.aa,{'s2aa_mr'}))
    labels={'TCE_ppb_l':'TCE','Cis12DCE_ppb_l':'CIS12DCE','VC_ppb_l':'VC'}
    manifest=json.loads((args.build/'manifest.json').read_text())
    validation=json.loads((args.build/'validation.json').read_text())
    require(validation['defaultPosition']=='joinedX','Incorrect default position policy')
    require(validation['defaultPositionFields']==['X_1','exg_tos_el','exg_bos_el'],'Unapproved default coordinate fields')
    require(validation['geometryApproved'] is False,'Horizontal correction must not imply full geometry approval')
    for name,sha in manifest.items():
        require(hashlib.sha256((args.build/name).read_bytes()).hexdigest()==sha,f'Manifest mismatch: {name}')
    require(set(p.name for p in args.build.glob('s2*.html'))=={f's2{s.lower()}_{m}.html' for s in sections for m in ['mr','max']},'Missing/extra transect pages')
    counts={}
    for sec in sections:
        rows=datasets[f's2{sec.lower()}_mr']['rows']
        expected={(r['Well_ID'],labels[r['Analyte']],r['SDate'],r['Result']) for r in rows}
        data=json.loads(next((args.build/'transects-assets').glob(sec+'.*.json')).read_text())
        require(data['defaultPosition']=='joinedX',f'{sec}: wrong default coordinate source')
        actual={(w['id'],a,r['date'],r['result']) for w in data['wells'] for a,samples in w['samples'].items() for r in samples}
        require(expected==actual,f'{sec}: measurements were lost, added or altered')
        source_rows=[n for w in data['wells'] for samples in w['samples'].values() for r in samples for n in r['sourceRows']]
        require(sorted(source_rows)==list(range(1,len(rows)+1)),f'{sec}: lost/duplicate raw-record provenance')
        # Reconcile each sample against its own raw rows, not just the overall key
        # set. This catches swapped provenance, invented X/elevation combinations,
        # fallback to the first X, and unapproved elevation replacement.
        fields={'shape':('X','exg_tos_el','exg_bos_el'),
                'joined':('X_1','exg_tos__1','exg_bos__1'),
                'joinedX':('X_1','exg_tos_el','exg_bos_el')}
        for well in data['wells']:
            for analyte,samples in well['samples'].items():
                for sample in samples:
                    originals=[rows[n-1] for n in sample['sourceRows']]
                    key=(well['id'],analyte,sample['date'],sample['result'])
                    require(all((r['Well_ID'],labels[r['Analyte']],r['SDate'],r['Result'])==key for r in originals),
                            f'{sec}: source records assigned to the wrong measurement')
                    for source,names in fields.items():
                        expected_positions=sorted({tuple(r[name] for name in names) for r in originals})
                        require([tuple(p) for p in sample[source]]==expected_positions,
                                f'{sec}/{well["id"]}: altered or mismatched {source} coordinates')
        require(data['latest']==max(r['SDate'] for r in rows),f'{sec}: wrong latest date')
        for mode in ['mr','max']:
            page=(args.build/f's2{sec.lower()}_{mode}.html').read_text()
            require(f'data-mode="{mode}"' in page and 'href="./" id="map-link"' in page,'Broken mode or relative map link')
            require('bundle.js' not in page,'Old embedded data bundle is still referenced')
            require('<select id="position"><option value="joinedX" selected>' in page,'Wrong default position view')
            for ref in re.findall(r'(?:src|href|data-source)="(transects-assets/[^"<>]+)"',page):
                require((args.build/ref).is_file(),f'Missing asset: {ref}')
        counts[sec]={'sourceRows':len(rows),'measurementKeys':len(actual),'latest':data['latest'],
                     'correctedXSourceRows':sum(r['X']!=r['X_1'] for r in rows),
                     'exportedScreenElevationsPreserved':True}
    print(json.dumps({'verified':True,'manifestFiles':len(manifest),'pages':12,'sections':counts},indent=2))


if __name__=='__main__': main()
