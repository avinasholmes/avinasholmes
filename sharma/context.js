const element=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
const format=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
let context=null;
function safeUrl(value){try{const url=new URL(value);return ['https:','http:'].includes(url.protocol)?url.href:null;}catch{return null;}}
export function stockContext(ticker){
 const box=element('div');box.className='stock-context';
 if(!context){box.append(element('p','News context is unavailable.'));return box;}
 const news=context.news.filter(n=>n.ticker===ticker);
 box.append(element('p',`News context · observed ${format.format(new Date(context.observed_at))} ET · Not used in score`));
 if(!news.length){box.append(element('p','No entity matches in the retained news batch. This does not establish that no news exists.'));return box;}
 const list=element('ul');for(const article of news.slice(0,4)){const url=safeUrl(article.url);if(!url)continue;const li=element('li'),a=element('a',`${article.publisher} ↗`);a.href=url;a.target='_blank';a.rel='noopener noreferrer';li.append(a);list.append(li);}box.append(list);return box;
}
async function loadContext(){
 const response=await fetch(`data/context.json?check=${Date.now()}`,{cache:'no-store'});if(!response.ok)throw new Error('context unavailable');
 const data=await response.json();if(!Array.isArray(data.news)||!data.statuses||!Number.isFinite(Date.parse(data.observed_at)))throw new Error('invalid context');context=data;
 const news=data.statuses.news,social=data.statuses.social;
 const age=Date.now()-Date.parse(data.observed_at);
 document.getElementById('context-status').textContent=`${news.status==='connected'?'GDELT connected':data.retained_after_error?'News refresh unavailable — previous observations retained':'News unavailable'} · ${social.status==='connected'?'Social connected':`Social unavailable${social.http_status?` (HTTP ${social.http_status})`:''}`}${age>1800000?' · Context is stale':''}`;
 const detail=document.getElementById('context-detail');detail.replaceChildren();const stocks=new Set(data.news.map(n=>n.ticker));detail.append(element('p',`${data.news.length} article–stock matches across ${stocks.size} securities. Observed ${format.format(new Date(data.observed_at))} ET.`));detail.append(element('p',news.scope||news.reason||'Limited source coverage.'));
 window.dispatchEvent(new Event('sharma:context'));
}
async function loadValidation(){
 const response=await fetch('data/validation.json',{cache:'no-store'});if(!response.ok)throw new Error('validation unavailable');
 const data=await response.json();const h=data.horizons.find(v=>v.minutes===10);if(!h)throw new Error('invalid validation');
 document.getElementById('validation-status').textContent=`Exploratory replay · ${data.sessions.length} sessions · ${h.observations.toLocaleString()} eligible 10-minute observations. No demonstrated edge.`;
 const container=document.getElementById('validation-detail');container.replaceChildren();const table=element('table');table.className='validation-table';const caption=element('caption','Hypothetical mean return per active signal after 10 bp assumed costs');table.append(caption);const head=element('thead'),tr=element('tr');for(const title of ['Strategy','Signals','Net bp'])tr.append(element('th',title));head.append(tr);table.append(head);const body=element('tbody');for(const [key,label] of [['sharma','Sharma PV'],['momentum','Momentum'],['rsi','RSI reversal'],['always_up','Always up']]){const m=h.strategies[key].find(m=>m.cost_bps===10);const row=element('tr');for(const value of [label,String(m.active),m.mean_net_bps_per_active_signal.toFixed(2)])row.append(element('td',value));body.append(row);}table.append(body);container.append(table);const link=element('a','Download the full replay report ↗');link.href='data/validation.json';link.className='text-link';link.download='sharma-validation.json';container.append(link);
}
export async function refreshContext(){await Promise.allSettled([loadContext().catch(()=>{document.getElementById('context-status').textContent=context?'Context refresh failed — previous observations retained':'Context unavailable — no sentiment inferred';}),loadValidation().catch(()=>{document.getElementById('validation-status').textContent='Replay report unavailable.';})]);}
