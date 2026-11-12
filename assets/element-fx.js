/* Element-shaped particles, including flames, leaves, water and electricity. */
window.ElementFX=(()=>{
const mix=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];
function leaf(c,x,y,a,s){c.save();c.translate(x,y);c.rotate(a);c.fillStyle='#b5ee74';c.strokeStyle='#4b9d50';c.lineWidth=1.2;c.beginPath();c.moveTo(-s,0);c.quadraticCurveTo(0,-s,s,0);c.quadraticCurveTo(0,s,-s,0);c.fill();c.stroke();c.strokeStyle='#efffbc';c.beginPath();c.moveTo(-s,0);c.lineTo(s,0);c.stroke();c.restore();}
function flame(c,x,y,s,a){c.save();c.translate(x,y);c.rotate(a);const g=c.createLinearGradient(0,-s*2,0,s);g.addColorStop(0,'#ff63304d');g.addColorStop(.4,'#ff8c2c');g.addColorStop(1,'#fff0a4');c.fillStyle=g;c.beginPath();c.moveTo(0,-s*2);c.bezierCurveTo(s*.2,-s*.6,s*1.3,-s*.1,s*.6,s*.7);c.quadraticCurveTo(0,s*1.3,-s*.65,s*.5);c.bezierCurveTo(-s*1.3,-s*.5,-s*.2,-s*.9,0,-s*2);c.fill();c.fillStyle='#fff6c7';c.beginPath();c.ellipse(0,s*.35,s*.28,s*.55,0,0,Math.PI*2);c.fill();c.restore();}
function bolt(c,a,b,age,width=3){c.strokeStyle='#fff3a2';c.lineWidth=width;c.beginPath();c.moveTo(...a);for(let i=1;i<=9;i++){const p=mix(a,b,i/9);c.lineTo(p[0]+(i<9?Math.sin(i*11+age*30)*10:0),p[1]+(i<9?Math.cos(i*7+age*20)*8:0));}c.stroke();}
function projectile(c,a,b,role,age,special=false){c.save();const t=Math.min(1,age/(special?.35:.5)),angle=Math.atan2(b[1]-a[1],b[0]-a[0]),n=special?6:3;
if(role==='electric'){bolt(c,a,b,age,special?6:2);c.restore();return;}
for(let i=0;i<n;i++){const trail=Math.max(0,t-i*.045),p=mix(a,b,trail),spread=Math.sin(i*2.4+age*12)*(special?9:4);p[0]+=Math.cos(angle+Math.PI/2)*spread;p[1]+=Math.sin(angle+Math.PI/2)*spread;c.globalAlpha=(1-i/(n+1))*(1-age*.5);
if(role==='fire')flame(c,...p,(special?7:4)*(1-i/(n+3)),angle+Math.PI/2);
else if(role==='grass')leaf(c,...p,angle+age*11+i,(special?6:4));
else if(role==='water'){c.fillStyle=i%2?'#baf8ff':'#4bbbe8';c.beginPath();c.ellipse(...p,special?6:4,special?4:3,angle,0,Math.PI*2);c.fill();c.strokeStyle='#f1ffff';c.lineWidth=1;c.stroke();}
else if(role==='ice'){c.save();c.translate(...p);c.rotate(age*5+i);c.strokeStyle='#d2ffff';c.lineWidth=2;for(let j=0;j<3;j++){c.rotate(Math.PI/3);c.beginPath();c.moveTo(-9,0);c.lineTo(9,0);c.stroke();}c.restore();}
else{const g=c.createRadialGradient(...p,1,...p,special?12:7);g.addColorStop(0,'#e7cbff');g.addColorStop(.35,role==='ghost'?'#8643d6':'#ed91e6');g.addColorStop(1,'#7d43c300');c.fillStyle=g;c.beginPath();c.arc(...p,special?12:7,0,Math.PI*2);c.fill();}}
if(age>.4){for(let i=0;i<(special?6:3);i++){const r=9+(age-.4)*26,a=i*2.399,p=[b[0]+Math.cos(a)*r,b[1]+Math.sin(a)*r];c.globalAlpha=1-age;if(role==='fire')flame(c,...p,special?5:3,a);else if(role==='grass')leaf(c,...p,a+age*9,special?5:3);else{c.fillStyle=role==='water'?'#b2eeff':role==='ice'?'#daffff':'#ddbbff';c.beginPath();c.arc(...p,special?4:2,0,Math.PI*2);c.fill();}}}
c.restore();}
function evolution(c,a,age){c.save();c.translate(...a);c.globalAlpha=Math.sin(age*Math.PI)*.65;const g=c.createRadialGradient(0,0,1,0,0,105);g.addColorStop(0,'#ffffdd');g.addColorStop(.35,'#ecf3a2aa');g.addColorStop(1,'#fff8c000');c.fillStyle=g;c.fillRect(-110,-110,220,220);for(let i=0;i<16;i++){const angle=i*Math.PI/8+age*3,r=25+age*100;c.save();c.rotate(angle);c.fillStyle=i%2?'#c9eaff':'#fff7af';c.beginPath();c.moveTo(r,0);c.lineTo(r+25,3);c.lineTo(r+65,0);c.lineTo(r+25,-3);c.fill();c.restore();}c.globalAlpha=1-age;for(let i=0;i<22;i++){const t=i*2.4+age*7,r=18+age*90;leaf(c,Math.cos(t)*r,Math.sin(t)*r,t,3);}c.restore();}
return{projectile,evolution,flame,leaf,bolt};
})();

