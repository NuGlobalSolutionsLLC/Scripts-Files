"""Strict, dependency-free readers for the supplied AFP4 DBF/SHP/SHX exports.

Read ZIP members in memory. Do not extract paths or transform profile geometry.
"""
import datetime
import math
import struct
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def dbf(blob, encoding):
    require(len(blob) >= 33, 'DBF header is truncated')
    count, header, width = struct.unpack_from('<IHH', blob, 4)
    require(header + count * width <= len(blob), 'DBF records are truncated')
    fields = []
    for start in range(32, header - 1, 32):
        if blob[start] == 13:
            break
        descriptor = blob[start:start + 32]
        name = descriptor[:11].split(b'\0')[0].decode('ascii')
        fields.append((name, chr(descriptor[11]), descriptor[16]))
    require(len({f[0] for f in fields}) == len(fields), 'Duplicate DBF field names')
    require(sum(f[2] for f in fields) + 1 == width, 'DBF field widths disagree')
    rows = []
    for index in range(count):
        raw = blob[header + index * width:header + (index + 1) * width]
        require(raw[:1] == b' ', 'Deleted or invalid DBF record; re-export before building')
        row, offset = {}, 1
        for name, kind, length in fields:
            value = raw[offset:offset + length].decode(encoding).strip()
            offset += length
            if not value or set(value) == {'*'}:
                value = None
            elif kind in ('N', 'F'):
                value = float(value)
                require(math.isfinite(value), 'Non-finite DBF number')
            elif kind == 'D':
                value = datetime.datetime.strptime(value, '%Y%m%d').date().isoformat()
            row[name] = value
        rows.append(row)
    return [f[0] for f in fields], rows


def shapes(shp, shx):
    for blob in (shp, shx):
        require(len(blob) >= 100, 'Shapefile header is truncated')
        require(struct.unpack_from('>I', blob)[0] == 9994, 'Invalid shapefile magic')
        require(struct.unpack_from('>I', blob, 24)[0] * 2 == len(blob), 'Invalid shapefile length')
        require(struct.unpack_from('<I', blob, 28)[0] == 1000, 'Unsupported shapefile version')
    require((len(shx) - 100) % 8 == 0, 'Invalid SHX record length')
    result, offset = [], 100
    for index in range((len(shx) - 100) // 8):
        require(offset + 8 <= len(shp), 'SHP record header is truncated')
        number, words = struct.unpack_from('>II', shp, offset)
        indexed_offset, indexed_words = struct.unpack_from('>II', shx, 100 + index * 8)
        require(number == index + 1, 'Out-of-order SHP record')
        require(indexed_offset * 2 == offset and indexed_words == words, 'SHP/SHX index mismatch')
        data = shp[offset + 8:offset + 8 + words * 2]
        require(len(data) == words * 2 and len(data) >= 4, 'SHP record is truncated')
        kind = struct.unpack_from('<I', data)[0]
        if kind == 1:
            require(len(data) == 20, 'Invalid point shape')
            points = [struct.unpack_from('<dd', data, 4)]
        elif kind == 3:
            require(len(data) >= 48, 'Polyline is truncated')
            parts, count = struct.unpack_from('<II', data, 36)
            require(parts == 1 and count >= 2, 'Expected a single-part polyline')
            require(struct.unpack_from('<I', data, 44)[0] == 0, 'Invalid polyline part index')
            require(len(data) == 48 + 16 * count, 'Polyline point length mismatch')
            points = [struct.unpack_from('<dd', data, 48 + 16 * n) for n in range(count)]
        else:
            raise ValueError(f'Unsupported or null shape type {kind}')
        require(all(math.isfinite(v) for p in points for v in p), 'Non-finite shape coordinate')
        result.append(points)
        offset += 8 + words * 2
    require(offset == len(shp), 'SHP/SHX record count mismatch')
    return result


def archive(path, include=None):
    result = {}
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None, 'ZIP checksum failure')
        names = {n.lower(): n for n in z.namelist()}
        require(len(names) == len(z.namelist()), 'Duplicate ZIP member names')
        for name in sorted(n for n in names if n.endswith('.shp')):
            stem = name[:-4]
            if include is not None and stem not in include:
                continue
            required = ['.shp', '.shx', '.dbf', '.cpg', '.prj']
            require(all(stem + ext in names for ext in required), f'Missing sidecar for {stem}')
            blobs = {ext: z.read(names[stem + ext]) for ext in required}
            fields, rows = dbf(blobs['.dbf'], blobs['.cpg'].decode().strip())
            geometry = shapes(blobs['.shp'], blobs['.shx'])
            require(len(rows) == len(geometry), f'SHP/DBF count mismatch for {stem}')
            result[stem] = {'fields': fields, 'rows': rows, 'shapes': geometry,
                            'prj': blobs['.prj'].decode(), 'blobs': blobs}
    require(bool(result), 'No shapefiles in archive')
    return result
