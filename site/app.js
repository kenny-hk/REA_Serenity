'use strict';
let dataset, days = 1, visibleMentions = [];
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateText = value => new Date(value).toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
const badge = stance => `<span class="badge ${['bullish','bearish','neutral','unclassified'].includes(stance) ? stance : 'unclassified'}">${esc(stance)}</span>`;
const source = m => `https://x.com/aleabitoreddit/status/${/^\d+$/.test(m.post_id) ? m.post_id : ''}`;
$('date').value = new Date().toISOString().slice(0,10);
$('edition-date').textContent = dateText(new Date());
function render() {
  if (!dataset) return;
  const end = new Date(`${$('date').value}T23:59:59.999Z`);
  if (!Number.isFinite(end.getTime())) return;
  const start = new Date(end.getTime() - days * 86400000 + 1);
  $('window-label').textContent = `${dateText(start)}${days > 1 ? ' – ' + dateText(end) : ''} · UTC`;
  const windowMentions = dataset.mentions.filter(m => new Date(m.created_at) >= start && new Date(m.created_at) <= end);
  const tickers = new Set(windowMentions.map(m => m.ticker));
  $('stats').innerHTML = [{label:'Stocks mentioned',value:tickers.size,sub:'unique tickers'}, ...['bullish','bearish','neutral','unclassified'].map(s => ({label:s[0].toUpperCase()+s.slice(1), value:windowMentions.filter(m=>m.stance===s).length,sub:'stock mentions'}))].map(s=>`<div class="stat"><span class="stat-label">${s.label}</span><strong>${s.value}</strong><small>${s.sub}</small></div>`).join('');
  const query = $('search').value.toLowerCase().trim();
  const stance = $('stance').value;
  const groups = new Map();
  for (const mention of windowMentions) {
    if (!`${mention.ticker} ${mention.company}`.toLowerCase().includes(query)) continue;
    if (!groups.has(mention.ticker)) groups.set(mention.ticker, []);
    groups.get(mention.ticker).push(mention);
  }
  let stocks = [...groups.values()].map(ms=>ms.sort((a,b)=>b.created_at.localeCompare(a.created_at)));
  stocks = stocks.filter(ms=>stance==='all'||ms[0].stance===stance);
  stocks.sort((a,b)=>$('sort').value==='ticker'?a[0].ticker.localeCompare(b[0].ticker):$('sort').value==='mentions'?b.length-a.length:b[0].created_at.localeCompare(a[0].created_at));
  visibleMentions = stocks.flat();
  $('rows').innerHTML = stocks.map(ms=>{const m=ms[0]; return `<tr><td><button data-ticker="${esc(m.ticker)}"><strong>${esc(m.ticker)} ↗</strong><span>${esc(m.company)}</span></button></td><td>${badge(m.stance)}</td><td>${ms.length}</td><td>${esc(m.summary)}</td><td>${dateText(m.created_at)}</td></tr>`;}).join('');
  $('empty').hidden = stocks.length > 0;
  if (!dataset.last_success) {
    $('empty').innerHTML = '<span class="empty-icon">◎</span><h3>The notebook is ready. The feed is next.</h3><p>No posts have been collected yet. Once the data connection is configured, daily stock mentions and their source-linked histories will appear here.</p><p><a href="https://github.com/kenny-hk/REA_Serenity#enable-daily-updates">View collection setup ↗</a></p>';
  } else {
    $('empty').innerHTML = '<span class="empty-icon">⌕</span><h3>No matching mentions</h3><p>Try a longer time window, a different date, or clear your filters. No mentions does not mean a neutral stance.</p>';
  }
  $('result-count').textContent = `${stocks.length} stocks · ${visibleMentions.length} mentions shown. Stance filter uses each stock’s latest mention in this window. Counts above show the full window.`;
}
function showDetail(ticker) {
  const ms = dataset.mentions.filter(m=>m.ticker===ticker).sort((a,b)=>b.created_at.localeCompare(a.created_at));
  const latest = ms[0];
  $('detail-content').innerHTML = `<h2>${esc(ticker)} <span class="light">${esc(latest.company)}</span></h2><p class="detail-meta">${ms.length} collected mentions · First collected mention ${dateText(ms.at(-1).created_at)}<br>Full collected history, across all dates. Labels and summaries are AI-inferred.</p><div class="timeline">${ms.map(m=>`<article class="entry"><time>${dateText(m.created_at)}</time>${badge(m.stance)}<p>${esc(m.summary)}</p><blockquote>${esc(m.evidence)}</blockquote>${m.risks.length?`<p class="risk">Stated risks: ${m.risks.map(esc).join('; ')}</p>`:''}<a href="${source(m)}" target="_blank" rel="noopener">Read original post ↗</a></article>`).join('')}</div>`;
  $('detail').showModal();
}
document.querySelectorAll('[data-days]').forEach(button=>button.addEventListener('click',()=>{days=Number(button.dataset.days);document.querySelectorAll('[data-days]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));render();}));
['date','search','stance','sort'].forEach(id=>$(id).addEventListener('input',render));
$('rows').addEventListener('click',event=>{const button=event.target.closest('[data-ticker]');if(button)showDetail(button.dataset.ticker);});
$('close').addEventListener('click',()=>$('detail').close());
$('detail').addEventListener('click',event=>{if(event.target===$('detail')){const r=$('detail').getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)$('detail').close();}});
$('export').addEventListener('click',()=>{
  const fields=['ticker','company','stance','created_at','summary','url'];
  const safe = value => {let v=String(value??'');if(/^[=+\-@\t\r]/.test(v))v="'"+v;return '"'+v.replace(/"/g,'""')+'"';};
  const csv=[fields.join(','),...visibleMentions.map(m=>fields.map(f=>safe(f==='url'?source(m):m[f])).join(','))].join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`serenity-${$('date').value}-${days}d.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
fetch('data/tracker.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Data unavailable');return r.json();}).then(data=>{
  if(data.schema_version!==1||!Array.isArray(data.mentions))throw Error('Unsupported dataset');dataset=data;
  const stale=data.last_success&&Date.now()-new Date(data.last_success).getTime()>36*3600000;
  const last=data.last_success?` Last successful collection: ${new Date(data.last_success).toLocaleString('en-GB',{timeZone:'Asia/Hong_Kong'})} HKT.`:'';
  $('health').textContent=data.status==='awaiting_configuration'?'○ Collection is awaiting configuration. No live updates are being collected.'+last:data.status==='error'?'○ The latest collection failed. Previously collected history is preserved.'+last:stale?'○ Collection is overdue; this data may be stale.'+last:`● Daily collection connected.${last}${data.backlog?' Catching up: '+data.backlog+' posts remain.':''}`;
  if(data.status==='error'||stale)$('health').classList.add('error');
  render();
}).catch(()=>{$('health').textContent='Unable to load the dataset. Please reload or check collection history on GitHub.';$('health').classList.add('error');$('empty').hidden=false;$('empty').textContent='The dataset is unavailable. No sentiment counts can be shown.';});
