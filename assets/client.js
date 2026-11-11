(()=>{'use strict';
const $=x=>document.getElementById(x),CW=46,RH=30,TAU=Math.PI*2;
const info=[null,['박선옥','#5ef3bf','바람의 개척자'],['김영관','#ffbf73','운명의 전략가'],['강병갑','#9babff','번개의 정복자']];
function avatar(i){ return ['/assets/unknown.svg','/assets/park.svg','/assets/kim.svg','/assets/kang.svg'][i] || '/assets/kang.svg'; }

const P=info.map((p,i)=>p?{name:p[0],color:p[1],kind:p[2],img:avatar(i)}:null);
const images=P.map(p=>{if(!p)return null;const a=new Image();a.src=p.img;return a});
const layers=['homeLayer','lobbyLayer','upgradeLayer','resultLayer','reconnectLayer'],canvas=$('game'),ctx=canvas.getContext('2d');
let picked=3,occupied=[],slot=0,code='',token='',host=false,ws=null,phase='home',room=null,state=null,cards=null,result=null,connecting=false,userLeft=false,tries=0,reconnectTimer;
let xAxis=0,yAxis=0,joy={x:0,y:0},touch={x:0,y:0},key={x:0,y:0},pointer=null,touchPointer=null,start=null,fx=[],sound=false,audio;
const clamp=(a,b,c)=>Math.max(b,Math.min(c,a));
const say=(t,kind='info')=>{const d=document.createElement('div');d.className='toast '+kind;d.textContent=t;$('toasts').prepend(d);setTimeout(()=>d.remove(),2800);while($('toasts').children.length>3)$('toasts').lastChild.remove()};
const view=n=>layers.forEach(x=>$(x).classList.toggle('show',x===n));
const send=(type,obj={})=>{if(ws&&ws.readyState===1)ws.send(JSON.stringify(Object.assign({type},obj)))};
const saved=c=>{try{return JSON.parse(sessionStorage.getItem('luck_session_'+c)||'null')}catch{return null}};
const remember=()=>{try{sessionStorage.setItem('luck_session_'+code,JSON.stringify({token,slot}))}catch{}};
const fmt=t=>String(Math.floor(Math.max(0,t)/60)).padStart(2,'0')+':'+String(Math.floor(Math.max(0,t)%60)).padStart(2,'0');
const net=(t,ok)=>{$('netText').textContent=t;$('net').classList.toggle('on',!!ok)};
function select(){
 const busy=room?.slots?room.slots.filter(Boolean).map(a=>a.id):occupied;
 $('select').innerHTML=P.slice(1).map((p,j)=>{const i=j+1;return '<button type="button" data-c="'+i+'" class="'+(picked===i?'selected ':'')+(busy.includes(i)?'taken':'')+'" style="--pc:'+p.color+'" '+(busy.includes(i)?'disabled':'')+'><img src="'+p.img+'" alt=""><strong>'+p.name+'</strong><small>'+p.kind+'</small>'+(picked===i?'<span class="pill">선택</span>':'')+'</button>'}).join('');
 $('select').querySelectorAll('button').forEach(b=>b.onclick=()=>{picked=+b.dataset.c;select()});
}
function board(){
 const arr=state?.players||room?.slots?.filter(Boolean)||[];
 const el=$('scoreboard');
 if(el.children.length!==3)el.innerHTML=P.slice(1).map(p=>'<div class="score" style="--pc:'+p.color+'"><div class="avatar"><img src="'+p.img+'"></div><div class="texts"><div><b class="score-name">'+p.name+'</b><em>0%</em></div><div class="track"><i class="fill"></i></div><div class="state">선택 대기</div></div></div>').join('');
 for(let k=0;k<3;k++){const i=k+1,p=arr.find(a=>a.id===i),e=el.children[k],v=Number(p?.score||0);e.classList.toggle('me',slot===i);e.querySelector('b').textContent=P[i].name+(slot===i?' ★':'');e.querySelector('em').textContent=v.toFixed(1)+'%';e.querySelector('.fill').style.width=v+'%';e.querySelector('.state').textContent=p?(p.connected?'🟢 접속 중':'📡 재접속 대기'):'자리 비움'}
}
function hud(){
 const p=state?.players?.find(v=>v.id===slot);if(!p)return;
 $('territory').textContent=p.score.toFixed(1);$('level').textContent=p.level;$('xp').textContent=p.xp+'/'+p.nextXp;$('hearts').textContent='♥'.repeat(Math.min(8,p.hp))+(p.shield?' 🛡️'+p.shield:'');$('luck').textContent=p.luck;$('time').textContent=fmt(state.remain);$('roomBadge').textContent='ROOM '+code;$('status').textContent=state.pausedForReconnect?'📡 재접속 대기':state.players.filter(v=>v.connected).length+'/3 접속 · '+p.kills+'킬';$('pulse').disabled=p.pulseReady>0||state.pausedForReconnect;$('pulseLabel').textContent=p.pulseReady>0?Math.ceil(p.pulseReady)+'초':'PULSE';
}
function lobby(){
 if(!room)return;
 $('lobbyCode').textContent=code;
 $('lobbyRows').innerHTML=P.slice(1).map((p,i)=>{const q=room.slots[i];return '<div class="lobby-seat"><img src="'+p.img+'"><strong style="color:'+p.color+'">'+p.name+'</strong><small>'+(q?(q.connected?'🟢 입장 완료':'📡 재접속 대기'):'⚪ 자리 비움')+'</small></div>'}).join('');
 const cnt=room.slots.filter(s=>s&&s.connected).length;$('beginBtn').disabled=!host||cnt!==3;$('beginBtn').textContent=cnt!==3?cnt+'/3명 입장 대기 중':(host?'⚔️ 대전 시작하기!':'방장 시작 대기 중…');$('lobbyTip').textContent=host?'3명이 입장하면 시작할 수 있습니다.':'방장이 시작하면 동시에 대전이 시작됩니다.';board();
}
const invite=()=>location.origin+'/?room='+encodeURIComponent(code);
async function copy(text){try{await navigator.clipboard.writeText(text);say('📋 초대 링크 복사 완료','good')}catch{prompt('초대 링크를 복사하세요',text)}}
async function inviteShare(){if(navigator.share){try{await navigator.share({title:'땅따먹기 LUCK RUSH',text:code+' 방에 입장해요',url:invite()});return}catch(e){if(e?.name==='AbortError')return}}copy(invite())}
async function lookup(c){
 $('roomInput').value=c;$('joinBtn').textContent='⚔️ 초대받은 방 입장';
 try{const r=await fetch('/api/rooms/'+c);if(!r.ok)throw Error();const d=await r.json();occupied=d.occupied||[];if(!saved(c)&&occupied.includes(picked))picked=[1,2,3].find(i=>!occupied.includes(i))||picked;select();if(d.phase!=='lobby'&&!saved(c))say('이미 대전 중인 방입니다.','danger')}catch{say('방을 찾을 수 없습니다.','danger')}
}
async function create(){
 try{const r=await fetch('/api/rooms',{method:'POST'});if(!r.ok)throw Error('서버 응답 오류');const d=await r.json();code=d.code;token='';slot=0;userLeft=false;history.replaceState(null,'','/?room='+code);connect()}catch(e){say('방 생성 실패: '+e.message,'danger')}
}
async function join(){
 const c=$('roomInput').value.trim().toUpperCase().replace(/[^A-Z2-9]/g,'');
 if(c.length!==5)return say('5자리 방 코드를 입력하세요','danger');
 try{const r=await fetch('/api/rooms/'+c);if(!r.ok)throw Error('존재하지 않는 방입니다');const d=await r.json();const s=saved(c);if(d.phase!=='lobby'&&!s)throw Error('이미 시작한 게임입니다');if(d.occupied.includes(picked)&&!s)throw Error('이미 선택한 캐릭터입니다');code=c;token='';slot=0;userLeft=false;history.replaceState(null,'','/?room='+c);connect()}catch(e){say(e.message,'danger')}
}
function connect(){
 if(connecting||!code)return;connecting=true;clearTimeout(reconnectTimer);net('접속 중…');
 const s=saved(code);if(s){token=s.token;slot=s.slot}
 const w=new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws?room='+code);ws=w;
 w.onopen=()=>{connecting=false;tries=0;net('온라인 연결',true);send('join',{slot:token?slot:picked,token:token||undefined})};
 w.onmessage=ev=>{let d;try{d=JSON.parse(ev.data)}catch{return}onMessage(d)};
 w.onerror=()=>{connecting=false};
 w.onclose=()=>{if(ws!==w)return;connecting=false;net('연결 끊김');if(userLeft)return;view('reconnectLayer');$('reconnectText').textContent='연결이 끊겼습니다. 자동 재접속 중입니다.';if(tries++<15)reconnectTimer=setTimeout(connect,Math.min(4000,1200+tries*250));else say('서버에 다시 접속해 주세요','danger')};
}
function onMessage(d){
 if(d.type==='joined'){slot=d.slot;token=d.token;host=d.isHost;phase='lobby';remember();view('lobbyLayer');say(P[slot].name+' 캐릭터로 참가했습니다','good')}
 else if(d.type==='room'){room=d;host=room.host===token;if(room.phase==='lobby'){phase='lobby';if(!cards)view('lobbyLayer');lobby()}else if(room.phase==='playing'&&phase!=='playing'){phase='playing';if(!cards)view(null)}}
 else if(d.type==='state'){if(state&&d.seq<=state.seq)return;state=d;if(d.phase==='playing'&&phase!=='playing'){phase='playing';if(!cards)view(null)}if(phase==='playing'&&!cards){if(d.pausedForReconnect){view('reconnectLayer');$('reconnectText').textContent='참가자 재접속 대기: '+d.reconnectLeft+'초'}else if($('reconnectLayer').classList.contains('show'))view(null)}board();hud()}
 else if(d.type==='event')say(d.message,d.kind);
 else if(d.type==='effect'){fx.push({id:d.id,range:d.range,end:performance.now()+450})}
 else if(d.type==='upgrade'){cards=d.cards;view('upgradeLayer');$('upgradeCards').innerHTML=d.cards.map((c,i)=>'<button type="button" class="upgrade '+c.tier+'" data-i="'+i+'"><span class="emoji">'+c.icon+'</span><i>'+c.tier.toUpperCase()+'</i><strong>'+c.name+'</strong><small>'+c.desc+'</small></button>').join('');$('upgradeCards').querySelectorAll('button').forEach(b=>b.onclick=()=>{send('upgrade',{id:cards[+b.dataset.i].id});b.disabled=true})}
 else if(d.type==='upgrade_done'){cards=null;if(phase==='playing')view(null)}
 else if(d.type==='finished'){result=d;phase='finished';cards=null;view('resultLayer');$('resultTitle').textContent='👑 '+(P[d.winner]?.name||'플레이어')+' 우승!';$('resultDesc').textContent=d.reason==='dominance'?'영토 55% 점령으로 조기 우승!':'가장 많은 영토를 점령한 플레이어가 승리!';$('rankList').innerHTML=d.scores.map((v,i)=>'<div class="rank"><span>'+['🥇','🥈','🥉'][i]+' '+P[v.id].name+'</span><strong>'+v.score.toFixed(1)+'% · '+v.kills+'킬</strong></div>').join('');$('rematchBtn').style.display=host?'':'none'}
 else if(d.type==='error'){say(d.message||'오류가 발생했습니다','danger');if(phase==='home'){userLeft=true;ws?.close();view('homeLayer')}}
}
function leave(){userLeft=true;send('leave');ws?.close();ws=null;try{sessionStorage.removeItem('luck_session_'+code)}catch{}history.replaceState(null,'','/');room=null;state=null;slot=0;token='';code='';phase='home';occupied=[];cards=null;connecting=false;net('연결 대기');view('homeLayer');select();board()}
const keys=new Set();
function direction(){const a=joy.x||joy.y?joy:touch.x||touch.y?touch:key;const dx=Math.abs(a.x)>=Math.abs(a.y)?Math.sign(a.x):0,dy=dx?0:Math.sign(a.y);if(xAxis!==dx||yAxis!==dy){xAxis=dx;yAxis=dy;send('input',{x:dx,y:dy})}}
function keyboard(){key={x:+(keys.has('ArrowRight')||keys.has('d'))-+(keys.has('ArrowLeft')||keys.has('a')),y:+(keys.has('ArrowDown')||keys.has('s'))-+(keys.has('ArrowUp')||keys.has('w'))};direction()}
const point=(x,y)=>Math.hypot(x,y)<10?{x:0,y:0}:Math.abs(x)>Math.abs(y)?{x:Math.sign(x),y:0}:{x:0,y:Math.sign(y)};
function wire(){
 select();board();$('createBtn').onclick=create;$('joinBtn').onclick=join;$('joinSmall').onclick=join;$('roomInput').onkeydown=e=>{if(e.key==='Enter')join()};$('beginBtn').onclick=()=>send('start');$('copyLink').onclick=inviteShare;$('copyCode').onclick=()=>copy(code);$('leaveBtn').onclick=leave;$('newRoom').onclick=()=>{leave();create()};$('rematchBtn').onclick=()=>send('rematch');$('retryBtn').onclick=()=>{try{ws?.close()}catch{}connecting=false;setTimeout(connect,150)};$('pulse').onclick=()=>send('pulse');$('sound').onclick=()=>{sound=!sound;$('sound').textContent=sound?'🔊':'🔇'};
 addEventListener('keydown',e=>{if(['INPUT','TEXTAREA'].includes(document.activeElement?.tagName))return;const k=e.key.length===1?e.key.toLowerCase():e.key;if(k.startsWith('Arrow')||k===' ')e.preventDefault();keys.add(k);keyboard();if(k===' '&&phase==='playing')send('pulse');if(cards&&['1','2','3'].includes(k))$('upgradeCards').querySelectorAll('button')[+k-1]?.click()});
 addEventListener('keyup',e=>{keys.delete(e.key.length===1?e.key.toLowerCase():e.key);keyboard()});addEventListener('blur',()=>{keys.clear();key={x:0,y:0};joy={x:0,y:0};touch={x:0,y:0};direction()});
 const j=$('joystick');function move(e){const r=j.getBoundingClientRect(),dx=e.clientX-r.left-r.width/2,dy=e.clientY-r.top-r.height/2,len=Math.max(1,Math.hypot(dx,dy)),a=Math.min(34,len)/len;$('stick').style.transform='translate(calc(-50% + '+dx*a+'px),calc(-50% + '+dy*a+'px))';joy=point(dx,dy);direction()}
 j.onpointerdown=e=>{pointer=e.pointerId;j.setPointerCapture(e.pointerId);move(e)};j.onpointermove=e=>{if(pointer===e.pointerId)move(e)};for(const n of ['pointerup','pointercancel','lostpointercapture'])j.addEventListener(n,e=>{if(pointer!==e.pointerId)return;pointer=null;joy={x:0,y:0};$('stick').style.transform='translate(-50%,-50%)';direction()});
 canvas.onpointerdown=e=>{if(e.pointerType==='mouse')return;touchPointer=e.pointerId;start={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId)};canvas.onpointermove=e=>{if(touchPointer===e.pointerId&&start){touch=point(e.clientX-start.x,e.clientY-start.y);direction()}};for(const n of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(n,e=>{if(touchPointer===e.pointerId){touchPointer=null;touch={x:0,y:0};direction()}});
}
function draw(t){
 const r=$('frame').getBoundingClientRect(),w=r.width,h=r.height,dpr=Math.min(2,devicePixelRatio||1);if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr)}
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);ctx.fillStyle='#0a1425';ctx.fillRect(0,0,w,h);
 const me=state?.players?.find(p=>p.id===slot),portrait=w/h<1.08,unit=portrait?Math.max(w/25,h/31):Math.min(w/CW,h/RH),vw=w/unit,vh=h/unit;
 const cx=portrait?clamp((me?.x||23)-vw/2,0,Math.max(0,CW-vw)):(CW-vw)/2,cy=portrait?clamp((me?.y||15)-vh/2,0,Math.max(0,RH-vh)):(RH-vh)/2,sx=x=>(x-cx)*unit,sy=y=>(y-cy)*unit;
 ctx.fillStyle='#101b30';ctx.fillRect(sx(0),sy(0),CW*unit,RH*unit);
 const minX=Math.max(0,Math.floor(cx)),maxX=Math.min(CW,Math.ceil(cx+vw)),minY=Math.max(0,Math.floor(cy)),maxY=Math.min(RH,Math.ceil(cy+vh));
 for(let y=minY;y<maxY;y++)for(let x=minX;x<maxX;x++){if((x+y)%2===0){ctx.fillStyle='#ffffff04';ctx.fillRect(sx(x),sy(y),unit,unit)}const b=+(state?.board?.[y*CW+x]||0);if(b){ctx.fillStyle=['', '#265c51','#725b36','#464b7c','#64edc2','#ffcd7c','#adb6ff'][b];ctx.fillRect(sx(x)+.35,sy(y)+.35,unit-.7,unit-.7)}}
 ctx.strokeStyle='#91bece55';ctx.lineWidth=2;ctx.strokeRect(sx(0),sy(0),CW*unit,RH*unit);
 for(const e of state?.enemies||[]){ctx.fillStyle='#ba78fa';ctx.beginPath();ctx.arc(sx(e[0]),sy(e[1]),Math.max(3,unit*.38),0,TAU);ctx.fill()}
 for(const b of state?.bullets||[]){ctx.fillStyle=P[b[2]]?.color||'#fff';ctx.beginPath();ctx.arc(sx(b[0]),sy(b[1]),Math.max(2,unit*.2),0,TAU);ctx.fill()}
 for(const p of state?.players||[]){const px=sx(p.x+.5),py=sy(p.y+.5),im=images[p.id],size=unit*2.4;if(px< -50||px>w+50||py< -50||py>h+50)continue;ctx.fillStyle='#0007';ctx.beginPath();ctx.ellipse(px,py+unit*.45,unit*.55,unit*.18,0,0,TAU);ctx.fill();if(p.id===slot){ctx.strokeStyle='#e9ffff';ctx.lineWidth=2;ctx.beginPath();ctx.arc(px,py,unit*.87,0,TAU);ctx.stroke()}if(im.complete&&im.naturalWidth)ctx.drawImage(im,px-size*.35,py-size*.9,size*.7,size);else{ctx.fillStyle=P[p.id].color;ctx.beginPath();ctx.arc(px,py,unit*.5,0,TAU);ctx.fill()}ctx.textAlign='center';ctx.font='bold '+clamp(unit*.7,10,15)+'px sans-serif';ctx.lineWidth=3;ctx.strokeStyle='#061020';ctx.strokeText(P[p.id].name,px,py-size*.91-4);ctx.fillStyle=P[p.id].color;ctx.fillText(P[p.id].name,px,py-size*.91-4)}
 fx=fx.filter(v=>v.end>t);for(const f of fx){const p=state?.players?.find(v=>v.id===f.id);if(!p)continue;ctx.strokeStyle=P[f.id].color;ctx.globalAlpha=(f.end-t)/450;ctx.lineWidth=3;ctx.beginPath();ctx.arc(sx(p.x+.5),sy(p.y+.5),unit*f.range*(1-(f.end-t)/500),0,TAU);ctx.stroke();ctx.globalAlpha=1}
 if(portrait&&state?.board){const mw=78,mh=52,mx=w-mw-12,my=48;ctx.fillStyle='#080e20dc';ctx.fillRect(mx-4,my-4,mw+8,mh+8);for(let y=0;y<RH;y++)for(let x=0;x<CW;x++){const b=+state.board[y*CW+x];if(b>=1&&b<=3){ctx.fillStyle=P[b].color;ctx.fillRect(mx+x*mw/CW,my+y*mh/RH,mw/CW+.2,mh/RH+.2)}}}
 if(!state?.board){ctx.textAlign='center';ctx.fillStyle='#b4c8e0';ctx.font='bold 16px sans-serif';ctx.fillText('3명이 참가하면 대전을 시작합니다',w/2,h/2)}
 requestAnimationFrame(draw);
}
wire();const params=new URLSearchParams(location.search),c=params.get('room');if(c&&/^[A-HJ-NP-Z2-9]{5}$/i.test(c)){code=c.toUpperCase();const s=saved(code);if(s){token=s.token;slot=s.slot;connect()}else lookup(code)}requestAnimationFrame(draw);
})();