// Lightweight DOM contract tests; not a substitute for visual browser QA.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {Blob} from 'node:buffer';
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {value:'',innerHTML:'',textContent:'',hidden:false,
    listeners:{},classList:{add(){}},addEventListener(type,fn){this.listeners[type]=fn;},
    showModal(){this.open=true;},close(){this.open=false;}});
  return elements.get(id);
};
const document = {getElementById:element, querySelectorAll:()=>[]};
const sample = (ticker, stance, date) => ({ticker,company:'Example <Company>',stance,created_at:date,
  post_id:'123',summary:'Summary <script>alert(1)</script>',evidence:'literal evidence',risks:[]});
const fixture = {schema_version:1,status:'ok',last_success:new Date().toISOString(),mentions:[
  sample('TEST','bullish','2026-10-18T12:00:00Z'),sample('TEST','bearish','2026-10-17T12:00:00Z'),
  sample('OTHER','neutral','2026-10-12T12:00:00Z'),sample('OLD','bullish','2026-06-01T12:00:00Z')]};
const context = vm.createContext({document,fetch:async()=>({ok:true,json:async()=>fixture}),Date,Set,Map,URL,Blob,setTimeout});
vm.runInContext(fs.readFileSync(new URL('../site/app.js',import.meta.url),'utf8'),context);
await new Promise(resolve=>setImmediate(resolve));
element('date').value='2026-10-18';element('stance').value='all';element('sort').value='recent';
vm.runInContext('render()',context);
assert.match(element('result-count').textContent,/1 stocks · 1 mentions/);
assert.ok(element('rows').innerHTML.includes('&lt;script&gt;'));
assert.ok(!element('rows').innerHTML.includes('<script>'));
vm.runInContext('days=7;render()',context);
assert.match(element('result-count').textContent,/2 stocks · 3 mentions/);
element('stance').value='bearish';vm.runInContext('render()',context);
assert.match(element('result-count').textContent,/0 stocks/); // TEST latest is bullish
element('stance').value='all';element('search').value='other';vm.runInContext('render()',context);
assert.match(element('result-count').textContent,/1 stocks · 1 mentions/);
vm.runInContext("showDetail('TEST')",context);
assert.equal(element('detail').open,true);
assert.match(element('detail-content').innerHTML,/2 collected mentions/);
assert.match(element('detail-content').innerHTML,/https:\/\/x.com\/aleabitoreddit\/status\/123/);
vm.runInContext('dataset={schema_version:1,mentions:[],last_success:null};render()',context);
assert.match(element('empty').innerHTML,/No posts have been collected/);
console.log('Frontend checks passed: windows, latest-stance filtering, search, escaping, history, empty state.');
