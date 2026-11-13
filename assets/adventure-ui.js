window.AdventureUI=(()=>{
let sendAction,offerKey='',lastReward=0,lastEvent=0,shareText='';
const $=id=>document.getElementById(id);
function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function notify(text){const e=node('div',text,'toast adventure-reward');$('toasts').append(e);setTimeout(()=>e.remove(),3200);}
$('openAdventure').onclick=()=>{$('adventurePanel').hidden=!$('adventurePanel').hidden;};
$('closeAdventure').onclick=()=>$('adventurePanel').hidden=true;
$('supportSection').onclick=e=>{const b=e.target.closest('[data-support]');if(b&&!b.disabled)sendAction('support',{skill:b.dataset.support,target:Number($('supportTarget').value)});};
$('shareResult').onclick=async()=>{try{await navigator.clipboard.writeText(shareText);notify('결과를 복사했어요.');}catch{prompt('결과 텍스트를 복사하세요.',shareText);}};
function reset(){offerKey='';lastReward=0;lastEvent=0;$('adventurePanel').hidden=true;$('fateDialog').hidden=true;}
function render(state,slot,send){
sendAction=send;const me=state.players.find(p=>p.id===slot),data=me?.adventure;if(!data)return;
const coop=state.gameMode==='coop';$('supportSection').hidden=!coop;
const targets=state.players.filter(p=>p.id!==slot&&p.alive&&p.connected),targetKey=targets.map(p=>p.id+':'+p.name).join('|');
if($('supportTarget').dataset.key!==targetKey){$('supportTarget').dataset.key=targetKey;$('supportTarget').replaceChildren(...targets.map(p=>{const o=node('option',p.name);o.value=p.id;return o;}));}
const ready=data.support?.readyIn||0;for(const b of $('supportSection').querySelectorAll('[data-support]')){const cost={attack:80,defense:120,energy:100}[b.dataset.support];b.disabled=!me.alive||!targets.length||ready>0||me.gold<cost||state.stage==='prep'||b.dataset.support==='defense'&&data.support.defenseUses>=3;}
$('supportStatus').textContent=!targets.length?'접속 중인 다른 생존 팀원이 필요합니다.':ready>0?'재사용 '+Math.ceil(ready)+'초':'공통 재사용 20초 · 방어 지원 경기당 3회';
if(state.adventureEvent?.id&&state.adventureEvent.id!==lastEvent){lastEvent=state.adventureEvent.id;notify(state.adventureEvent.message);if(state.adventureEvent.kind==='victory'&&!matchMedia('(prefers-reduced-motion: reduce)').matches){$('game').classList.add('boss-victory');setTimeout(()=>$('game').classList.remove('boss-victory'),600);}}
const m=data.mission;$('missionTiny').textContent=m?m.status==='completed'?'✓':m.progress+'/'+m.target:'';
const status={active:'진행 중',completed:'성공',expired:'기간 종료'};
$('missionInfo').replaceChildren();if(m){$('missionInfo').append(node('b',m.name+' · '+status[m.status]),node('p',m.description),node('small',m.progress+'/'+m.target+' · '+m.until+'R까지 · 보상 '+m.reward+' ◈'));const bar=node('progress');bar.max=m.target;bar.value=m.progress;$('missionInfo').append(bar);}else $('missionInfo').append(node('p','다음 구간 미션을 기다리고 있어요.'));
$('synergyInfo').replaceChildren(...data.synergies.map(s=>{const e=node('div',undefined,'synergy-row'+(s.active?' enabled':''));e.append(node('b',s.icon+' '+s.name),node('small',s.counts.map(n=>Math.min(2,n)+'/2').join(' · ')+' · '+s.effect));return e;}));
$('ownedCards').replaceChildren(...data.cards.map(c=>node('div',c.icon+' '+c.name+' ×'+c.count+' · '+c.description,'owned-card')));
if(!data.cards.length)$('ownedCards').append(node('small','5·15·25·35·45R 완료 후 선택합니다.'));
const key=data.choices.map(c=>c.id).join(':')+':'+data.choiceRound;
$('fateDialog').hidden=!data.choices.length||!me.alive;
$('choiceTimer').textContent=Math.ceil(state.stageLeft)+'초 후 서버 자동 선택';
if(data.choices.length&&key!==offerKey){offerKey=key;$('choiceCards').replaceChildren(...data.choices.map(c=>{const b=node('button',undefined,'fate-card');b.type='button';b.dataset.grade=c.grade;b.append(node('span',c.icon,'fate-icon'),node('small',c.grade,'card-grade'),node('strong',c.name),node('span',c.description));b.onclick=()=>{b.classList.add('chosen');$('choiceCards').querySelectorAll('button').forEach(x=>x.disabled=true);sendAction('choose_card',{id:c.id});};return b;}));}
if(!data.choices.length)offerKey='';
if(data.lastReward&&data.lastReward.id!==lastReward){lastReward=data.lastReward.id;notify(data.lastReward.message+(data.lastReward.coins?' +'+data.lastReward.coins+' ◈':''));}
}
function results(r,slot){
$('ranks').replaceChildren();const lines=['POKÉ LUCK · '+r.wave+'R · '+(r.completed?'완주':'경기 종료')];
r.scores.forEach((p,i)=>{const a=r.awards?.[p.id]||[],stats=p.adventure?.stats||{},row=node('article',undefined,'result-player'+(r.mvpSlot===p.id?' mvp':''));row.append(node('h3',(i+1)+'위 · '+p.name+(p.id===slot?' (나)':'')+' · '+p.score.toLocaleString()+'점'),node('div',a.map(t=>t.icon+' '+t.name).join(' · '),'result-titles'),node('p','처치 '+p.kills+' · 누적 피해 '+p.damage.toLocaleString()+' · 보스 '+p.bossDamage.toLocaleString()),node('p','전설 '+(stats.legendary||0)+' · 합성/진화 '+(stats.evolutions||0)+' · 미션 '+(stats.missions||0)+' · 지원 '+(stats.supports||0)));$('ranks').append(row);lines.push((i+1)+'. '+p.name+' '+p.score+'점 · 처치 '+p.kills+' · 보스 '+p.bossDamage+' · '+a.map(t=>t.name).join('/'));});shareText=lines.join('\n');
}
return{render,reset,notify,results};
})();
