/* Layered casts and a shared raid arena, drawn in the game's world coordinates. */
window.BattleSpectacle = (() => {
 const colors = {water:'#59d9ff',fire:'#ffad57',electric:'#ffe985',grass:'#b8f282',ice:'#d3faff',ghost:'#bc96ff',psychic:'#f6a5e6'};
 function impact(c, point, role, age, size=1) {
  if(age<.45)return;
  const progress=Math.min(1,(age-.45)/.55);
  c.save();c.globalAlpha=(1-progress)*.8;c.strokeStyle=colors[role]||'#fff4cf';c.lineWidth=2;
  c.beginPath();c.ellipse(point[0],point[1]+8,(8+progress*35)*size,(3+progress*12)*size,0,0,Math.PI*2);c.stroke();
  for(let i=0;i<12;i++){
   const angle=i*Math.PI/6,radius=(8+progress*30)*size;
   const x=point[0]+Math.cos(angle)*radius,y=point[1]+Math.sin(angle)*radius-progress*(1-progress)*35;
   c.fillStyle=i%3?colors[role]||'#fff':'#ffffff';c.beginPath();c.ellipse(x,y,2*size,(role==='water'?4:2)*size,angle,0,Math.PI*2);c.fill();
  }
  c.restore();
 }
 function water(c,a,b,age,special) {
  const travel=Math.min(1,age/.45),angle=Math.atan2(b[1]-a[1],b[0]-a[0]);
  const length=Math.hypot(b[0]-a[0],b[1]-a[1])*travel;
  c.save();c.translate(...a);c.rotate(angle);c.lineCap='round';c.globalAlpha=Math.min(1,(1-age)*3);
  if(special){
   for(const [width,color] of [[24,'#2478c84d'],[15,'#278eda'],[8,'#5ce1f4'],[3,'#e6ffff']]){
    c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.moveTo(0,0);
    c.bezierCurveTo(length*.3,Math.sin(age*30)*9,length*.7,-Math.sin(age*30)*9,length,0);c.stroke();
   }
   c.strokeStyle='#e1ffffa0';c.lineWidth=2;
   for(let i=0;i<7;i++){const x=((i/7+age*2)%1)*length;c.beginPath();c.ellipse(x,0,3,10,0,0,Math.PI*2);c.stroke();}
  }else{
   const glow=c.createRadialGradient(length,0,1,length,0,14);glow.addColorStop(0,'#ddffff');glow.addColorStop(.4,'#58dfff');glow.addColorStop(1,'#1679c600');c.fillStyle=glow;c.fillRect(length-15,-15,30,30);
   c.strokeStyle='#87eaff';c.lineWidth=4;c.beginPath();c.moveTo(Math.max(0,length-23),0);c.lineTo(length,0);c.stroke();
  }
  c.restore();impact(c,b,'water',age,special?1.4:.7);
 }
 function arena(c,boss,time) {
  const t=time*.001;
  c.save();
  const sky=c.createLinearGradient(0,0,0,580);sky.addColorStop(0,'#10172c');sky.addColorStop(.55,'#244053');sky.addColorStop(1,'#0c1e2b');c.fillStyle=sky;c.fillRect(0,0,900,580);
  for(let i=0;i<11;i++){
   const x=i*94-30;c.fillStyle=i%2?'#172b40':'#1c3348';c.beginPath();c.moveTo(x,400);c.lineTo(x+15,125+(i%3)*35);c.lineTo(x+48,105+(i%3)*35);c.lineTo(x+65,400);c.fill();
  }
  const ground=c.createRadialGradient(450,365,40,450,365,520);ground.addColorStop(0,'#456575');ground.addColorStop(1,'#10232f');c.fillStyle=ground;c.beginPath();c.ellipse(450,390,550,190,0,0,Math.PI*2);c.fill();
  c.strokeStyle='#8dcbdb40';c.lineWidth=2;
  for(let i=0;i<4;i++){c.beginPath();c.ellipse(450,390,180+i*105,60+i*35,0,0,Math.PI*2);c.stroke();}
  for(let i=0;i<32;i++){const x=(i*127+t*8)%900,y=110+(i*79-t*14+800)%420;c.fillStyle=i%3?'#b5e9ff55':'#ffe9a999';c.beginPath();c.arc(x,y,1+i%2,0,Math.PI*2);c.fill();}
  const aura=c.createRadialGradient(180,290,15,180,290,170);aura.addColorStop(0,boss.patternPhase===3?'#ff573b50':'#85b3ff38');aura.addColorStop(1,'#00000000');c.fillStyle=aura;c.fillRect(0,110,360,360);
  c.restore();
 }
 return {impact,water,arena};
})();
