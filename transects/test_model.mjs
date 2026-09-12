import test from 'node:test';
import assert from 'node:assert/strict';
import { selectSamples, colorFor, legendFor, screenBox, markersFor } from './model.mjs';

test('most recent is selected by date, preserving different same-day results', () => {
  const samples = [{date:'2024-01-01',result:900}, {date:'2025-03-11',result:0}, {date:'2025-03-11',result:2}];
  assert.deepEqual(selectSamples(samples, 'mr'), samples.slice(1));
  assert.deepEqual(selectSamples(samples, 'max'), samples.slice(0, 1));
});
test('maximum preserves all tied dates instead of manufacturing one sample date', () => {
  const samples = [{date:'2001-01-01',result:8}, {date:'2020-01-01',result:8}, {date:'2025-01-01',result:0}];
  assert.deepEqual(selectSamples(samples, 'max'), samples.slice(0, 2));
});
test('zero and missing measurements are distinct', () => {
  assert.deepEqual(selectSamples([], 'mr'), []);
  assert.equal(selectSamples([{date:'2025-01-01',result:0}], 'mr')[0].result, 0);
  assert.equal(colorFor('TCE', 0), '#00ff00');
  assert.equal(colorFor('CIS12DCE', 0), '#38A800');
  assert.equal(colorFor('VC', 0), '#00ff00');
});
test('legacy color thresholds retain inclusive upper boundaries', () => {
  for (const [a, value, expected] of [['TCE',5,'#00ff00'],['TCE',5.01,'#00ffc5'],['TCE',50,'#00ffc5'],
    ['TCE',10000,'#ff0000'],['TCE',10001,'#8400a8'],['CIS12DCE',0.1,'#8BD100'],['CIS12DCE',5,'#8BD100'],
    ['CIS12DCE',5.1,'#FFFF00'],['CIS12DCE',500,'#FF8000'],['CIS12DCE',501,'#FF0000'],
    ['VC',2,'#00ff00'],['VC',2.1,'#e9ffbe'],['VC',100000,'#ff0000'],['VC',100001,'#8400a8']]) {
    assert.equal(colorFor(a, value), expected);
  }
  assert.equal(legendFor('TCE').length, 8);
  assert.equal(legendFor('CIS12DCE').length, 5);
  assert.equal(legendFor('VC').length, 7);
});
test('invalid measurements and modes fail instead of receiving a misleading color', () => {
  for (const value of [-1, NaN, Infinity, undefined]) assert.throws(() => colorFor('TCE', value));
  assert.throws(() => colorFor('UNKNOWN', 1));
  assert.throws(() => selectSamples([], 'average'));
});
const layout = {xDomain:[0,1000], xRange:[0,100], yDomain:[0,100], yRange:[100,0], elevationExaggeration:20};
test('profile elevations use the documented 20x display scale, without geographic reprojection', () => {
  assert.deepEqual(screenBox([500,1600,1200],layout), {x:50,y:20,width:7,height:20});
  assert.throws(() => screenBox([500,1000,1200],layout));
});
test('duplicate positions merge but conflicting positions and results remain inspectable', () => {
  const well = {samples:{TCE:[
    {date:'2025-03-11',result:2,shape:[[500,1600,1200]],joined:[[510,1600,1200]]},
    {date:'2025-03-11',result:4,shape:[[500,1600,1200],[550,1600,1200]],joined:[[510,1600,1200]]},
  ]}};
  const markers = markersFor(well,'TCE','mr','shape',layout);
  assert.equal(markers.length,2);
  assert.deepEqual(markers[0].results,[2,4]);
  assert.equal(markersFor(well,'TCE','mr','joined',layout).length,1);
});

test('EPA-2 uses one joined X while retaining the original three screen intervals', () => {
  const shape = [[6375.18,12580,12490],[6430.95,11680,11590],[7442.06,12780,12580]];
  const corrected = shape.map(([, top, bottom]) => [7442.06, top, bottom]);
  const well = {samples:{TCE:[{date:'1986-05-08',result:0,shape,
    joinedX:corrected,joined:[[7442.06,12780,12580]]}]}};
  const profile = {...layout,xDomain:[0,13000],xRange:[24,1154],yDomain:[425,660],yRange:[434,17]};
  for (const mode of ['mr','max']) {
    const markers = markersFor(well,'TCE',mode,'joinedX',profile);
    const original = markersFor(well,'TCE',mode,'shape',profile);
    assert.equal(markers.length,3);
    assert.deepEqual([...new Set(markers.map(m => m.coordinates[0]))],[7442.06]);
    assert.equal(new Set(markers.map(m => m.x)).size,1);
    assert.deepEqual(markers.map(m => [m.y,m.height]),original.map(m => [m.y,m.height]));
    assert.deepEqual(markers.flatMap(m => m.results),[0,0,0]);
    assert.equal(markersFor(well,'TCE',mode,'joined',profile).length,1);
  }
});

test('corrected positions retain subsegment pairs and same-day result ties', () => {
  const well = {samples:{TCE:[
    {date:'2025-03-11',result:2,joinedX:[[510,1600,1200],[560,1800,1400]]},
    {date:'2025-03-11',result:4,joinedX:[[510,1600,1200]]},
  ]}};
  const markers = markersFor(well,'TCE','mr','joinedX',layout);
  assert.deepEqual(markers.map(m => m.coordinates),[[510,1600,1200],[560,1800,1400]]);
  assert.deepEqual(markers[0].results,[2,4]);
  assert.deepEqual(markers[1].results,[2]);
});

test('corrected mode never silently falls back to the first X or joined elevations', () => {
  const well = {samples:{TCE:[{date:'2025-03-11',result:0,
    shape:[[500,1600,1200]],joined:[[510,1800,1400]]}]}};
  assert.throws(() => markersFor(well,'TCE','mr','joinedX',layout));
});

test('relative assets and map links work under all three existing application prefixes', () => {
  for (const base of ['/AFP4/','/AFP04/','/storymap/afp4/']) {
    const page = `https://app.nuglobalsolutions.com${base}s2aa_mr.html`;
    assert.equal(new URL('./',page).pathname,base);
    assert.equal(new URL('transects-assets/AA.example.json',page).pathname,`${base}transects-assets/AA.example.json`);
    assert.equal(new URL('s2aa_max.html',page).pathname,`${base}s2aa_max.html`);
  }
});
