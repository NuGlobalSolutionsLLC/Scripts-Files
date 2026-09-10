import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { selectSamples, markersFor } from './model.mjs';

const directory = path.join(process.argv[2], 'transects-assets');
let selections = 0, positions = 0;
for (const section of ['AA','BB','CC','DD','EE','FF']) {
  const file = fs.readdirSync(directory).find(name => name.startsWith(`${section}.`) && name.endsWith('.json'));
  const data = JSON.parse(fs.readFileSync(path.join(directory,file),'utf8'));
  for (const well of data.wells) for (const [analyte,samples] of Object.entries(well.samples)) {
    assert.deepEqual(samples.map(s => [s.date,s.result]), samples.map(s => [s.date,s.result]).sort((a,b) => a[0].localeCompare(b[0]) || a[1]-b[1]));
    for (const mode of ['mr','max']) {
      const actual = selectSamples(samples,mode);
      const expected = samples.filter(s => !samples.some(other => mode === 'mr' ? other.date > s.date : other.result > s.result));
      assert.deepEqual(actual,expected);
      selections++;
      for (const position of ['shape','joined']) {
        const markers = markersFor(well,analyte,mode,position,data.layout);
        assert.deepEqual([...new Set(markers.flatMap(m=>m.results))].sort((a,b)=>a-b), [...new Set(actual.map(s=>s.result))].sort((a,b)=>a-b));
        for (const marker of markers) {
          assert.ok([marker.x,marker.y,marker.width,marker.height].every(Number.isFinite));
          assert.ok(marker.height > 0 && marker.width > 0);
          assert.ok(marker.x > -10 && marker.x < data.layout.width && marker.y > -10 && marker.y+marker.height < data.layout.height+10,
            `Screen outside published diagram: ${section}/${well.id}`);
          positions++;
        }
      }
    }
  }
}
console.log(JSON.stringify({verified:true,selections,positions}));

