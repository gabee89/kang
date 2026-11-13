/* Deterministic scenery animation; encounter rolls and damage stay on the server. */
window.Environment=(()=>{
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
let mode='auto';try{mode=localStorage.getItem('poke-effects-mode')||'auto';}catch{}if(!['auto','on','off'].includes(mode))mode='auto';
const moving=()=>mode==='on'||mode==='auto'&&!reduced.matches;
function setMode(value){mode=['auto','on','off'].includes(value)?value:'auto';try{localStorage.setItem('poke-effects-mode',mode);}catch{}}
const icons={clear:'☀',rain:'☔',heat:'♨',snow:'❄',wind:'🍃'};
function label(plan){return (icons[plan?.weather]||'☀')+' '+(plan?.weatherName||'맑음')+' · '+(moving()?'배경 움직임':'배경 정지');}
const tints={forest:'#91c76c',valley:'#579fae',volcano:'#d77737',snowfield:'#bedcf5',moonlit:'#7965ac'};
function draw(c,time,state){
 const plan=state?.roundPlan;if(!plan||!Battlefield.data)return;
 const t=moving()?time*.001:0,map=Battlefield.data;
 c.save();c.fillStyle=tints[plan.theme]||tints.forest;c.globalAlpha=plan.theme==='forest'?.025:.15;c.fillRect(0,0,900,580);c.globalAlpha=1;
 if(plan.theme==='valley'){
  for(let i=0;i<3;i++){const y=150+i*160+Math.sin(t*.3+i)*18,g=c.createLinearGradient(0,y-30,0,y+30);g.addColorStop(0,'#b1d5d000');g.addColorStop(.5,'#b1d5d018');g.addColorStop(1,'#b1d5d000');c.fillStyle=g;c.fillRect(0,y-30,900,60);}
 }else if(plan.theme==='volcano'){
  const g=c.createRadialGradient(850,570,10,850,570,350);g.addColorStop(0,'#ef973b33');g.addColorStop(1,'#ef973b00');c.fillStyle=g;c.fillRect(0,0,900,580);
 }else if(plan.theme==='snowfield'){
  c.fillStyle='#e4f3ff40';for(let i=0;i<20;i++){c.beginPath();c.ellipse(i*83, i%2?579:1,48,12,0,0,Math.PI*2);c.fill();}
 }else if(plan.theme==='moonlit'){
  for(let i=0;i<15;i++){c.globalAlpha=.25+.25*Math.sin(t+i);c.fillStyle='#ede2ff';c.fillRect((i*137)%900,8+(i*23)%58,2,2);}c.globalAlpha=1;
 }
 // Moving reflections over water-aligned pedestals and leaves around the border.
 c.strokeStyle='#c5f2ec66';c.lineWidth=1;
 if(state.stage!=='boss')map.cells.forEach((cell,i)=>{if(map.terrain[i]!=='water')return;const [x,y]=Battlefield.xy(...cell);c.beginPath();c.ellipse(x,y+12,19+Math.sin(t*2+i)*6,4,0,0,Math.PI*2);c.stroke();});
 if(moving()&&state.stage!=='boss'){
  map.cells.forEach((cell,i)=>{const kind=map.terrain[i];if(kind!=='ghost'&&kind!=='electric')return;const [x,y]=Battlefield.xy(...cell);c.globalAlpha=.55+.2*Math.sin(t*2+i);if(kind==='ghost'){c.fillStyle='#b9d7ff';c.beginPath();c.ellipse(x+12*Math.sin(t+i),y-8+4*Math.sin(t*2+i),4,7,0,0,Math.PI*2);c.fill();}else if(Math.sin(t*3+i)>.55){c.strokeStyle='#d7c4ff';c.lineWidth=2;c.beginPath();c.moveTo(x-13,y+10);c.lineTo(x,y+6);c.lineTo(x-2,y+13);c.lineTo(x+9,y+8);c.stroke();}});c.globalAlpha=1;
 }
 if(moving()){
  for(let i=0;i<24;i++){const x=(i*71+t*24)%900,y=i%2?18+Math.sin(t+i)*7:556+Math.sin(t+i)*7;c.save();c.translate(x,y);c.rotate(Math.sin(t+i)*.4);c.fillStyle=i%3?'#a1c86c66':'#e6d99555';c.beginPath();c.ellipse(0,0,8,3,0,0,Math.PI*2);c.fill();c.restore();}
 }
 // Ambient terrain movement remains visible in every weather.
 if(moving()&&state.stage!=='boss')map.cells.forEach((cell,i)=>{const [x,y]=Battlefield.xy(...cell),kind=map.terrain[i];if(kind==='fire'){for(let j=0;j<3;j++){const a=t*1.4+i+j;c.fillStyle='#ffc16ca0';c.beginPath();c.arc(x+Math.sin(a)*17,y+24-(a*16%40),2,0,Math.PI*2);c.fill();}}else if(kind==='grass'){c.save();c.translate(x+Math.sin(t+i)*16,y+Math.cos(t*.8+i)*12);c.rotate(Math.sin(t+i));c.fillStyle='#d4ec8090';c.beginPath();c.ellipse(0,0,8,3,0,0,Math.PI*2);c.fill();c.restore();}});
 const wash={rain:'#537fa517',snow:'#deedff18',heat:'#ffb94d12',wind:'#b7e8ce08'}[plan.weather];if(wash){c.fillStyle=wash;c.fillRect(0,0,900,580);}
 if(plan.weather==='clear'&&mode!=='off'){c.save();c.globalAlpha=.07;for(let i=0;i<3;i++){c.fillStyle='#fff4b7';c.beginPath();const x=-100+i*280+Math.sin(t*.2)*45;c.moveTo(x,0);c.lineTo(x+70,0);c.lineTo(x+300,580);c.lineTo(x+160,580);c.fill();}c.restore();}
 // The same shortcut portal used by the server is highlighted during preparation.
 if(plan.entry==='shortcut'&&state.stage!=='boss'){
  const [x,y]=Battlefield.xy(...Battlefield.position(map.flankProgress));
  c.strokeStyle='#e4bcff';c.lineWidth=2;c.globalAlpha=.65+.2*Math.sin(t*3);c.beginPath();c.ellipse(x,y-4,27+3*Math.sin(t*3),39,0,0,Math.PI*2);c.stroke();c.globalAlpha=1;
  c.font='bold 11px sans-serif';c.textAlign='center';c.strokeStyle='#183a32';c.lineWidth=3;c.strokeText(state.stage==='prep'?'다음 라운드 진입':'샛길 개방',x,y+48);c.fillStyle='#f2dcff';c.fillText(state.stage==='prep'?'다음 라운드 진입':'샛길 개방',x,y+48);
 }
 const count=mode==='off'?0:matchMedia('(max-width:900px)').matches?50:96;
 if(plan.weather==='rain'){
  c.strokeStyle='#b4e9ffd0';c.lineWidth=1.6;for(let i=0;i<count;i++){const x=(i*97-t*70+90000)%900,y=(i*67+t*290)%580;c.beginPath();c.moveTo(x,y);c.lineTo(x-8,y+26);c.stroke();}
 }else if(plan.weather==='snow'){
  c.fillStyle='#effaffaa';for(let i=0;i<count;i++){const x=(i*79+Math.sin(t+i)*19)%900,y=(i*91+t*24)%580;c.beginPath();c.arc(x,y,2.2+i%3*.8,0,Math.PI*2);c.fill();}
 }else if(plan.weather==='heat'){
  for(let i=0;i<count/2;i++){const x=(i*113+Math.sin(t+i)*15)%900,y=580-(i*83+t*32)%580;c.fillStyle=i%2?'#ffd18b99':'#ff9c5e88';c.beginPath();c.arc(x,y,1.2,0,Math.PI*2);c.fill();}
 }else if(plan.weather==='wind'){
  c.strokeStyle='#d6e9bea0';c.lineWidth=1.5;for(let i=0;i<12;i++){const x=(i*151+t*95)%950-30,y=40+i*44+Math.sin(t+i)*12;c.beginPath();c.moveTo(x,y);c.quadraticCurveTo(x+18,y-8,x+60,y);c.stroke();}
 }
 c.restore();
}
function enter(previous,next){
 if(next.stage==='boss'&&previous?.stage!=='boss'&&moving()){const canvas=document.getElementById('game');canvas.classList.remove('boss-impact');void canvas.offsetWidth;canvas.classList.add('boss-impact');setTimeout(()=>canvas.classList.remove('boss-impact'),420);}
}
return{draw,enter,setMode,label,get mode(){return mode;}};
})();

