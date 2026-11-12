/* Persistent, deduplicated combat events; animation never controls damage. */
window.CombatFX=(()=>{
let events=[],seen=new Set(),counts={attack:0,ultimate:0,evolve:0};
const duration=e=>e.kind==='attack'?650:1600;
function reset(){events=[];seen.clear();counts={attack:0,ultimate:0,evolve:0};}
function ingest(state){const now=performance.now();for(const p of state.players)for(const e of p.effects||[]){if(seen.has(e.id))continue;seen.add(e.id);counts[e.kind]=(counts[e.kind]||0)+1;const start=now-Math.max(0,state.seconds-e.created)*1000/(state.speed||1);if(now-start<duration(e))events.push({...e,owner:p.id,start});}events=events.filter(e=>now-e.start<duration(e)).slice(-100);if(seen.size>4000){seen=new Set(events.map(e=>e.id));}}
function active(owner,now){return events.filter(e=>e.owner===owner&&now-e.start<duration(e));}
function pose(owner,u,now){const idle={dx:Math.sin(now*.002+u.id)*2,dy:Math.sin(now*.005+u.id)*4,scale:1+Math.sin(now*.006+u.id)*.025,angle:Math.sin(now*.003+u.id)*.025};const e=active(owner,now).findLast(e=>e.unit===u.id);if(!e)return idle;const age=(now-e.start)/duration(e);if(e.kind==='evolve')return{dx:0,dy:-Math.sin(age*Math.PI)*22,scale:1+.45*Math.sin(age*Math.PI),angle:Math.sin(age*25)*.1,evolving:true,fromDex:e.fromDex,age};const origin=Battlefield.xy(...Battlefield.data.cells[e.cell]),target=e.targets.length?Battlefield.xy(...Battlefield.position(e.targets[0])):origin,angle=Math.atan2(target[1]-origin[1],target[0]-origin[0]),pulse=Math.sin(Math.min(1,age*2)*Math.PI),distance=e.mode==='melee'?34:-12;return{dx:Math.cos(angle)*pulse*distance,dy:Math.sin(angle)*pulse*distance,scale:1+pulse*.16,angle:Math.sin(angle)*pulse*.25};}
function hit(owner,id,now){return active(owner,now).some(e=>(e.victims||[]).includes(id)&&now-e.start>170&&now-e.start<430);}
function circle(c,x,y,r,color,width=2){c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.stroke();}
function beam(c,a,b,color,width){c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.beginPath();c.moveTo(...a);c.lineTo(...b);c.stroke();}
function sparks(c,x,y,color,age,n=9){c.fillStyle=color;for(let i=0;i<n;i++){const a=i*2.399,dist=8+age*42;const size=3*(1-age)+1;c.fillRect(x+Math.cos(a)*dist,y+Math.sin(a)*dist,size,size);}}
function draw(c,owner,now){const all=active(owner,now);c.save();c.textAlign='center';
for(const e of all){const age=(now-e.start)/duration(e),a=Battlefield.xy(...Battlefield.data.cells[e.cell]),color=Battlefield.palette[e.role]||({ghost:'#c69aef',ice:'#bcf6ff',psychic:'#ffa8e9'}[e.role])||'#fff';c.globalAlpha=Math.max(0,1-age);
if(e.kind==='evolve'){ElementFX.evolution(c,a,age);circle(c,...a,20+age*65,'#fff6af',4);circle(c,...a,40+age*25,'#fff',2);sparks(c,...a,'#fff3a2',age,20);c.fillStyle='#fff9c1';c.font='bold 19px sans-serif';c.strokeStyle='#18352c';c.lineWidth=5;c.strokeText(e.move+(e.enhanced?' 강화!':' 진화!'),a[0],a[1]-52);c.fillText(e.move+(e.enhanced?' 강화!':' 진화!'),a[0],a[1]-52);continue;}
for(let i=0;i<e.targets.length;i++){const b=Battlefield.xy(...Battlefield.position(e.targets[i]));
ElementFX.projectile(c,a,b,e.role,age,e.kind==='ultimate');
if(e.kind==='attack'){
 if(e.mode==='melee'){const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);c.strokeStyle=color;c.lineWidth=5;c.beginPath();c.arc(a[0]+Math.cos(angle)*22,a[1]+Math.sin(angle)*22,25,-.8+angle+age*2,1+angle+age*2);c.stroke();if(age>.22)sparks(c,...b,color,age,7);}
 else if(age<.55){const t=Math.min(1,age/.45),x=a[0]+(b[0]-a[0])*t,y=a[1]+(b[1]-a[1])*t;beam(c,[x-(b[0]-a[0])*.08,y-(b[1]-a[1])*.08],[x,y],color,4);c.fillStyle='#fff';c.beginPath();c.arc(x,y,4,0,Math.PI*2);c.fill();}else{circle(c,...b,6+age*17,color,2);sparks(c,...b,color,age);}
 if(age>.3){c.font='bold '+(e.critical?17:12)+'px sans-serif';c.fillStyle=e.critical?'#ffe991':'#fff';c.fillText((e.critical?'CRIT ':'')+e.damage,b[0],b[1]-12-age*22);}
}else{
 if(e.style==='storm'){c.strokeStyle=color;c.lineWidth=4;c.beginPath();c.moveTo(b[0]-12,0);for(let j=0;j<9;j++)c.lineTo(b[0]+Math.sin(j*9+age*23)*15,b[1]*j/8);c.stroke();circle(c,...b,20+age*65,color,4);}
 else if(e.style==='beam'||e.style==='wave'){beam(c,a,b,color,20*Math.sin(Math.PI*age)+3);beam(c,a,b,'#fffbe0',5);if(e.style==='wave')for(let j=0;j<3;j++)circle(c,...b,12+((age+j*.2)%1)*54,color,3);}
 else if(e.style==='slash'){for(let j=0;j<3;j++)beam(c,[b[0]-30+j*12,b[1]-35],[b[0]-10+j*12,b[1]+30],color,6);}
 else{const radius=15+Math.sin(age*Math.PI)*48;const g=c.createRadialGradient(...b,0,...b,radius);g.addColorStop(0,'#fff8dc');g.addColorStop(.3,color);g.addColorStop(1,color+'00');c.fillStyle=g;c.beginPath();c.arc(...b,radius,0,Math.PI*2);c.fill();circle(c,...b,radius,color,3);if(e.move==='불대문자'){const r=radius*.7;for(const width of [9,3]){c.strokeStyle=width===9?'#ff7e38':'#fff0a8';c.lineWidth=width;c.beginPath();c.moveTo(b[0]-r,b[1]-r*.35);c.lineTo(b[0]+r,b[1]-r*.35);c.moveTo(b[0],b[1]-r);c.lineTo(b[0],b[1]);c.lineTo(b[0]-r*.8,b[1]+r);c.moveTo(b[0],b[1]);c.lineTo(b[0]+r*.8,b[1]+r);c.stroke();}}}
 sparks(c,...b,color,age,16);if(i===0){circle(c,...a,28+age*55,color,3);c.fillStyle=color+'12';c.fillRect(0,0,900,580);}
}
}}
const headline=all.findLast(e=>e.kind==='ultimate');if(headline){const age=(now-headline.start)/1600;c.globalAlpha=Math.min(1,(1-age)*3);c.fillStyle='#132235d9';c.beginPath();c.roundRect(230,8,440,45,12);c.fill();c.strokeStyle='#eddf9e';c.lineWidth=1;c.stroke();c.fillStyle='#fff2ad';c.font='bold 20px sans-serif';c.fillText('✦ '+headline.move+' ✦',450,38);}
c.restore();}
return{ingest,reset,pose,hit,draw,get stats(){return{...counts};}};
})();

