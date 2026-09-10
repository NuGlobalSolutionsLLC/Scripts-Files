"""Build isolated AFP4 transect review pages. Never writes into an application."""
import argparse
import collections
import datetime
import hashlib
import html
import json
import pathlib
import re

from shapefile import archive, require

HERE = pathlib.Path(__file__).resolve().parent
SECTIONS = ('AA', 'BB', 'CC', 'DD', 'EE', 'FF')
ANALYTES = {'TCE_ppb_l': 'TCE', 'Cis12DCE_ppb_l': 'CIS12DCE', 'VC_ppb_l': 'VC'}
LABELS = {'TCE': 'Trichloroethylene', 'CIS12DCE': 'cis-1,2-Dichloroethylene', 'VC': 'Vinyl chloride'}
REQUIRED = ('Well_ID', 'SDate', 'Matrix', 'Analyte', 'Result', 'Transect',
            'X', 'exg_tos_el', 'exg_bos_el', 'X_1', 'exg_tos__1', 'exg_bos__1', 'PerpDist')


def selected(samples, mode):
    """Preserve all latest-date values or all dates tied for the maximum."""
    require(mode in ('mr', 'max'), 'Unknown display mode')
    if not samples:
        return []
    key = 'date' if mode == 'mr' else 'result'
    best = max(row[key] for row in samples)
    return [row for row in samples if row[key] == best]


def coordinates(row, source):
    fields = ('X', 'exg_tos_el', 'exg_bos_el') if source == 'shape' else ('X_1', 'exg_tos__1', 'exg_bos__1')
    return tuple(row[key] for key in fields)


def make_section(sec, dataset, published):
    require(set(REQUIRED) <= set(dataset['fields']), f'{sec}: missing required fields')
    require('NAD_1983_StatePlane_Texas_North_Central_FIPS_4202_Feet' in dataset['prj'], f'{sec}: unexpected CRS declaration')
    grouped, row_counts = collections.defaultdict(dict), collections.Counter()
    geometry_disagreements = []
    for number, (row, points) in enumerate(zip(dataset['rows'], dataset['shapes']), 1):
        require(all(row[key] not in (None, '') for key in REQUIRED), f'{sec}: empty required value in record {number}')
        require(row['Matrix'] == 'GW' and row['Analyte'] in ANALYTES, f'{sec}: unexpected matrix or analyte')
        require(row['Transect'].startswith(sec[0] + '_' + sec[1]), f'{sec}: unexpected transect identifier')
        require(row['Result'] >= 0, f'{sec}: negative result needs source review')
        datetime.date.fromisoformat(row['SDate'])
        require(abs(row['PerpDist']) < 20, f'{sec}: source includes a perpendicular distance outside the stated filter')
        shape = coordinates(row, 'shape')
        joined = coordinates(row, 'joined')
        require(shape[1] > shape[2] and joined[1] > joined[2], f'{sec}: invalid screen elevations')
        require(all(abs(p[0] - shape[0]) < .01 for p in points), f'{sec}: shape X disagrees with its attributes')
        require(abs(max(p[1] for p in points) - shape[1]) < .01 and abs(min(p[1] for p in points) - shape[2]) < .01,
                f'{sec}: shape elevation disagrees with its attributes')
        if any(abs(a - b) > .001 for a, b in zip(shape, joined)):
            geometry_disagreements.append({'record': number, 'well': row['Well_ID'], 'date': row['SDate'],
                                           'shape': shape, 'joined': joined})
        analyte = ANALYTES[row['Analyte']]
        row_counts[analyte] += 1
        key = (analyte, row['SDate'], row['Result'])
        sample = grouped[row['Well_ID']].setdefault(key, {'date': row['SDate'], 'result': row['Result'],
                                                           'shape': set(), 'joined': set(), 'sourceRows': []})
        sample['shape'].add(shape)
        sample['joined'].add(joined)
        sample['sourceRows'].append(number)
    require(set(row_counts) == set(LABELS), f'{sec}: all three analytes are required')
    wells, issues = [], []
    for well, records in sorted(grouped.items()):
        samples = {a: [] for a in LABELS}
        for (analyte, _, _), value in sorted(records.items()):
            samples[analyte].append({**value, 'shape': sorted(value['shape']), 'joined': sorted(value['joined'])})
        old = published.get(sec + '/' + well)
        wells.append({'id': well, 'samples': samples, 'publishedBox': old})
        for analyte, measurements in samples.items():
            for mode in ['mr', 'max']:
                chosen = selected(measurements, mode)
                if not chosen:
                    continue
                shape = {tuple(p) for r in chosen for p in r['shape']}
                joined = {tuple(p) for r in chosen for p in r['joined']}
                values = {r['result'] for r in chosen}
                if len(shape) > 1 or len(joined) > 1 or shape != joined or len(values) > 1:
                    issues.append({'well': well, 'analyte': analyte, 'mode': mode, 'shape': sorted(shape),
                                   'joined': sorted(joined), 'results': sorted(values)})
    unique = sum(len(rows) for w in wells for rows in w['samples'].values())
    report = {'sourceRows': len(dataset['rows']), 'uniqueMeasurementKeys': unique, 'repeatedRows': len(dataset['rows']) - unique,
              'wells': len(wells), 'analytes': {a: {'rows': row_counts[a], 'uniqueMeasurementKeys': sum(len(w['samples'][a]) for w in wells),
                                                  'latest': max(r['date'] for w in wells for r in w['samples'][a])} for a in LABELS},
              'shapeAttributeDisagreements': geometry_disagreements, 'selectedResultReview': issues,
              'newWells': [w['id'] for w in wells if w['publishedBox'] is None],
              'omittedPublishedWells': sorted(k.split('/', 1)[1] for k in published if k.startswith(sec + '/') and k.split('/', 1)[1] not in grouped)}
    return {'section': sec, 'labels': LABELS, 'wells': wells,
            'latest': max(r['SDate'] for r in dataset['rows']),
            'reviewWells': sorted({r['well'] for r in issues})}, report


def write_asset(root, name, content):
    data = content.encode() if isinstance(content, str) else content
    suffix = pathlib.Path(name).suffix
    stem = pathlib.Path(name).stem
    filename = f'{stem}.{hashlib.sha256(data).hexdigest()[:16]}{suffix}'
    relative = pathlib.Path('transects-assets') / filename
    target = root / relative
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(data)
    return relative.as_posix()


def page(sec, mode, svg, data_url, script_url, style_url, production_review=False, hide_review_banners=False):
    require(not hide_review_banners or production_review, 'Hiding review banners requires an authorized production review')
    title = sec[0] + '–' + sec[1]
    options = ''.join(f'<option value="{a}">{html.escape(label)}</option>' for a, label in LABELS.items())
    modes = ''.join(f'<option value="{m}"{" selected" if m == mode else ""}>{label}</option>'
                    for m, label in [('mr', 'Most Recent'), ('max', 'Maximum Value')])
    notice = ('Updated transect data — screen positioning is awaiting GIS review. Original diagrams are unchanged.'
              if production_review else
              'Local validation preview — not deployed. Original diagrams are unchanged. Well-position checks are pending.')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AFP4 transect {title} — {"Most Recent" if mode == "mr" else "Maximum Value"}</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="{style_url}"></head>
<body data-section="{sec}" data-mode="{mode}" data-source="{data_url}" data-review-banners="{'hidden' if hide_review_banners else 'shown'}">
<header><h1>Transect {title}</h1><a href="./" id="map-link">Map View</a></header>
<p class="preview">{notice}</p>
<div class="controls"><label>Data display <select id="mode">{modes}</select></label>
<label>Analyte <select id="analyte"><option value="">Choose an analyte</option>{options}</select></label>
<label>Position comparison <select id="position"><option value="shape">Exported screen geometry</option><option value="joined">Joined coordinate fields</option></select></label></div>
<p id="status" role="status">Loading transect data…</p><p id="warning" class="warning" hidden></p>
<main><div class="diagram">{svg}</div><div id="legend" class="legend" aria-label="Concentration legend"></div>
<section aria-labelledby="history-title"><h2 id="history-title">Well history</h2><p id="detail">Choose an analyte, then click a screen or a well in the table.</p>
<svg id="history" viewBox="0 0 1200 230" role="img" aria-label="Sample history chart"></svg>
<details id="history-records" hidden><summary>Exact plotted sample values</summary><table><thead><tr><th>Date</th><th>Result (µg/L)</th></tr></thead><tbody id="history-body"></tbody></table></details></section>
<section aria-labelledby="results-title"><h2 id="results-title">Displayed results</h2><div class="table-wrap"><table><thead><tr><th>Well</th><th>Sample date(s)</th><th>Result (µg/L)</th><th>Position check</th></tr></thead><tbody id="results"></tbody></table></div></section>
</main><script type="module" src="{script_url}"></script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transects', type=pathlib.Path, required=True, help='B–F source ZIP; its older A–A is deliberately ignored')
    parser.add_argument('--aa', type=pathlib.Path, required=True, help='Complete replacement A–A ZIP')
    parser.add_argument('--output', type=pathlib.Path, required=True, help='New, empty, isolated build directory')
    parser.add_argument('--production-review', action='store_true', help='Use only with explicit approval to publish while GIS review remains pending')
    parser.add_argument('--hide-review-banners', action='store_true', help='Presentation-only: hide the two review banners with explicit approval; retains comparison, data, and position checks')
    args = parser.parse_args()
    require(not args.hide_review_banners or args.production_review, 'Hiding review banners requires an authorized production review')
    require(not args.output.exists(), 'Output must be a new directory; never overwrite an application or earlier build')
    base_stems = {f's2{s.lower()}_{m}' for s in SECTIONS[1:] for m in ['mr', 'max']}
    datasets = archive(args.transects, base_stems)
    datasets.update(archive(args.aa, {'s2aa_mr', 's2aa_max'}))
    require(set(datasets) == base_stems | {'s2aa_mr', 's2aa_max'}, 'Expected exactly twelve profile exports')
    layouts = json.loads((HERE / 'legacy/layouts.json').read_text())
    published = json.loads((HERE / 'legacy/published-screens.json').read_text())
    section_data, sections = {}, {}
    for sec in SECTIONS:
        a, b = (datasets[f's2{sec.lower()}_{m}'] for m in ['mr', 'max'])
        require(all(a['blobs'][ext] == b['blobs'][ext] for ext in ['.shp', '.shx', '.dbf', '.prj']), f'{sec}: MR/MAX sources differ; review source semantics first')
        section_data[sec], sections[sec] = make_section(sec, a, published)
        section_data[sec]['layout'] = layouts[sec]
    args.output.mkdir(parents=True)
    model_url = write_asset(args.output, 'model.js', (HERE / 'model.mjs').read_text())
    app = (HERE / 'app.mjs').read_text().replace("'./model.mjs'", repr('./' + pathlib.Path(model_url).name))
    app_url = write_asset(args.output, 'app.js', app)
    style_url = write_asset(args.output, 'style.css', (HERE / 'style.css').read_text())
    files = []
    for sec, data in section_data.items():
        image = write_asset(args.output, f'{sec}.png', (HERE / f'legacy/{sec}.png').read_bytes())
        svg = (HERE / f'legacy/{sec}.svg').read_text()
        layout = layouts[sec]
        svg = re.sub(r'<svg\b[^>]*>', f'<svg id="profile" viewBox="0 0 {layout["width"]} {layout["height"]}" aria-label="Transect {sec} diagram">', svg, count=1)
        first_tag_end = svg.index('>') + 1
        svg = svg[:first_tag_end] + f'<image href="{image}" width="{layout["imageWidth"]}" height="{layout["imageHeight"]}" opacity="0.4"/>' + svg[first_tag_end:]
        data_url = write_asset(args.output, f'{sec}.json', json.dumps(data, separators=(',', ':'), allow_nan=False))
        for mode in ['mr', 'max']:
            filename = f's2{sec.lower()}_{mode}.html'
            (args.output / filename).write_text(page(sec, mode, svg, data_url, app_url, style_url, args.production_review, args.hide_review_banners))
            files.append(filename)
    review = {'productionReady': False, 'reason': 'Local draft: coordinate reconciliation and release approval are required.',
              'productionReviewRequested': args.production_review, 'geometryApproved': False,
              'reviewBannersVisible': not args.hide_review_banners,
              'selectionPolicy': 'Latest date retains every distinct result; maximum retains every tied sample date. No averages, invented flags or old-history gap filling.',
              'geometryPolicy': 'Preview presents original screen geometry and joined attributes separately. No coordinate choice or geographic reprojection is applied.',
              'sources': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.transects, args.aa]}, 'sections': sections}
    if args.production_review:
        review['reason'] = 'User authorized production publication for client review; coordinate authority remains unresolved. Banner visibility is a presentation choice, not geometry approval.'
    (args.output / 'validation.json').write_text(json.dumps(review, indent=2) + '\n')
    links = ''.join(f'<li><a href="{f}">{f}</a></li>' for f in files)
    (args.output / 'review.html').write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><title>AFP4 local transect review</title><h1>AFP4 local transect review</h1><p>Not deployed. Review all six sections, three analytes and both display modes.</p><ul>{links}</ul><a href="validation.json">Validation report</a></html>')
    manifest = {p.relative_to(args.output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.output.rglob('*')) if p.is_file()}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(args.output.resolve()), 'pages': len(files), 'productionReady': False,
                      'sections': {s: {k: v for k, v in r.items() if k not in ['shapeAttributeDisagreements', 'selectedResultReview']}
                                   | {'resultPositionReviewCount': len(r['selectedResultReview'])} for s, r in sections.items()}}, indent=2))


if __name__ == '__main__':
    main()
