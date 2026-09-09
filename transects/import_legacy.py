"""One-time extraction of the published diagrams and calibration, not data updates."""
import argparse
import base64
import hashlib
import json
import pathlib
import re
import struct

SECTIONS = ('AA', 'BB', 'CC', 'DD', 'EE', 'FF')


def recover(bundle):
    sources = {}
    for match in re.finditer(r'sourceMappingURL=data:application/json[^,]*;base64,([A-Za-z0-9+/=]+)', bundle):
        data = json.loads(base64.b64decode(match[1]))
        for name, content in zip(data['sources'], data.get('sourcesContent', [])):
            leaf = name.split('?')[0].rsplit('/', 1)[-1]
            if len(content or '') > len(sources.get(leaf, '')):
                sources[leaf] = content
    return sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new output directory; legacy references are immutable')
    args.output.mkdir(parents=True)
    layouts, origins, screens = {}, {}, None
    for sec in SECTIONS:
        name = f's2{sec.lower()}_mr'
        html_path = args.public / f'{name}.html'
        page = html_path.read_text()
        bundle_ref = re.findall(r'<script\s+src="([^"\s]+/' + name + r'\.[^"\s]+\.bundle\.js)"', page)
        if len(bundle_ref) != 1:
            raise ValueError(f'Cannot identify the original bundle for {sec}')
        bundle_path = args.public / bundle_ref[0]
        source = recover(bundle_path.read_text())
        component = source[f'V_{name}.vue']
        # Read only the section calibration preceding the rendering body.
        calibration = re.sub(r'/\*.*?\*/', '', component, flags=re.S)
        numbers = {key: float(re.search(r'\b' + key + r'\s*=\s*([0-9.]+)', calibration)[1])
                   for key in ['width', 'height', 'xpadding', 'ypadding', 'xIncreaseIndex', 'yIncreaseIndex']}
        xdomain = [float(n.strip()) for n in re.search(r'var xScale = d3.scale.linear\(\)\s*\.domain\(\[([^]]+)\]', calibration)[1].split(',')]
        ydomain = [float(n.strip()) for n in re.search(r'var yScale = d3.scale.linear\(\)\s*\.domain\(\[([^]]+)\]', calibration)[1].split(',')]
        svg = re.search(r'<svg\b.*?</svg\s*>', page, re.S)[0]
        svg = re.sub(r'\sdata-v-[a-z0-9]+=""', '', svg)
        svg = re.sub(r'\s+id="[^"]*"', '', svg)
        image_path = args.public / 'static' / 'img' / f'{sec}2.png'
        image = image_path.read_bytes()
        image_width, image_height = struct.unpack_from('>II', image, 16)
        layouts[sec] = {'width': numbers['width'], 'height': numbers['height'], 'xDomain': xdomain, 'yDomain': ydomain,
                        'xRange': [numbers['xpadding'], numbers['width'] - numbers['xpadding'] * 2 - numbers['xIncreaseIndex']],
                        'yRange': [numbers['height'] - numbers['ypadding'], numbers['ypadding'] - numbers['yIncreaseIndex']],
                        'imageWidth': image_width, 'imageHeight': image_height, 'elevationExaggeration': 20}
        (args.output / f'{sec}.svg').write_text(svg)
        (args.output / f'{sec}.png').write_bytes(image)
        origins[sec] = {str(p.relative_to(args.public)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [html_path, bundle_path, image_path]}
        if screens is None:
            old = json.loads(source['xsect_data.js'].removeprefix('export default ').strip().removesuffix(';').replace('{ data:', '{"data":', 1))['data']
            screens = {}
            for row in old:
                key = row['xsect'] + '/' + row['Well_ID']
                box = {k: row[k] for k in ['x', 'y', 'width', 'height']}
                if key in screens and screens[key] != box:
                    raise ValueError(f'Legacy screen has multiple layouts: {key}')
                screens[key] = box
    for filename, data in [('layouts.json', layouts), ('origins.json', origins), ('published-screens.json', screens)]:
        (args.output / filename).write_text(json.dumps(data, indent=2) + '\n')
    print(f'Imported {len(layouts)} unchanged diagrams and {len(screens)} published screen positions')


if __name__ == '__main__':
    main()
