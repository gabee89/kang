window.Rankings=(()=>{
const $=id=>document.getElementById(id);let saved=new Set();
function local(){try{return JSON.parse(localStorage.getItem('poke_solo_rank_v2')||'[]');}catch{return[];}}
function draw(el,rows){el.replaceChildren();if(!rows.length){el.textContent='아직 기록이 없어요. 첫 기록에 도전하세요!';return;}rows.slice(0,20).forEach((r,i)=>{const div=document.createElement('div');div.className='ranking-row';div.textContent=(i+1)+'. '+r.name+' · '+r.score.toLocaleString()+'점 · '+(r.completed?'50R 완주':r.wave+'R')+' · '+({normal:'보통',challenge:'도전',extreme:'극한'}[r.difficulty]||'');el.append(div);});}
async function refresh(){draw($('localRanks'),local());$('rankStatus').textContent='서버 기록 불러오는 중…';try{const res=await fetch('/api/leaderboard?difficulty='+$('rankDifficulty').value);if(!res.ok)throw Error();const d=await res.json();draw($('serverRanks'),d.entries);$('rankStatus').textContent=d.durable?'외부 저장소 연결 · 서버 기록 유지':'현재 서버 기록 · 재배포 시 초기화될 수 있음 / 내 기록은 이 기기에 저장';}catch{$('rankStatus').textContent='서버 랭킹을 불러오지 못했어요. 내 기기 기록은 아래에서 확인하세요.';}}
function record(r,slot){if(!r.solo||saved.has(r.runId))return;saved.add(r.runId);const p=r.scores.find(p=>p.id===slot);if(!p)return;try{const rows=local().filter(x=>x.runId!==r.runId);rows.push({runId:r.runId,name:p.name,score:p.score,wave:r.wave,completed:r.completed,difficulty:r.difficulty});rows.sort((a,b)=>b.score-a.score);localStorage.setItem('poke_solo_rank_v2',JSON.stringify(rows.slice(0,50)));}catch{}}
function init(){$('refreshRanks').onclick=refresh;$('rankDifficulty').onchange=refresh;try{$('trainerName').value=localStorage.getItem('poke_trainer_name')||'';}catch{}$('trainerName').oninput=()=>{try{localStorage.setItem('poke_trainer_name',$('trainerName').value);}catch{}};refresh();}
return{init,refresh,record};
})();

