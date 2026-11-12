/* One signature projectile per cast; nearby hits stay small and readable. */
window.UltimateFX=(()=>{
const mix=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];
function line(c,a,b,color,width){c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.beginPath();c.moveTo(...a);c.lineTo(...b);c.stroke();}
function ring(c,p,r,color,width=1.5){c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.arc(...p,r,0,Math.PI*2);c.stroke();}
function fireGlyph(c,p,size,age){c.save();c.translate(...p);const paths=[[-1,-.35,1,-.35],[0,-1,0,-.1],[0,-.1,-.85,1],[0,-.1,.85,1]];for(const [color,w] of [['#e95830',7],['#ffae40',4],['#fff3ae',1.5]])for(const s of paths)line(c,[s[0]*size,s[1]*size],[s[2]*size,s[3]*size],color,w);for(let i=0;i<5;i++){const a=i*1.4+age*2;ElementFX.flame(c,Math.cos(a)*size*.7,Math.sin(a)*size*.8,3,Math.sin(age*9+i)*.3);}c.restore();}
function draw(c,e,a,b,age){c.save();c.globalAlpha=Math.min(.85,(1-age)*2);const travel=Math.max(0,Math.min(1,(age-.08)/.55)),p=mix(a,b,travel),move=e.move;
if(move==='불대문자'){
 for(let i=3;i>=1;i--){const q=mix(a,b,Math.max(0,travel-i*.045));c.globalAlpha=.13;fireGlyph(c,q,14,age);}
 c.globalAlpha=Math.min(.9,(1-age)*2);fireGlyph(c,p,19,age);
 if(travel===1)ring(c,b,16+age*12,'#ffbe76',2);
}else if(move==='화염방사'){
 for(let i=0;i<10;i++){const q=mix(a,b,i/10*travel);ElementFX.flame(c,...q,4+Math.sin(i+age*12)*1.5,Math.atan2(b[1]-a[1],b[0]-a[0])+Math.PI/2);}
}else if(move==='솔라빔'){
 ring(c,a,8+Math.sin(age*12)*3,'#d4f69e');if(age>.18&&age<.8){line(c,a,b,'#8dd77d',7);line(c,a,b,'#f3ffca',2);for(let i=0;i<4;i++)ElementFX.leaf(c,b[0]+Math.cos(i+age*5)*16,b[1]+Math.sin(i+age*5)*16,i,4);}
}else if(move==='하이드로펌프'){
 line(c,a,p,'#5bbce1',9);line(c,a,p,'#c8faff',3);for(let i=0;i<3;i++)ring(c,p,5+((age+i*.2)%1)*16,'#b4eaff',1.5);
}else if(move==='10만볼트'){
 ElementFX.bolt(c,a,b,age,3);for(let i=0;i<2;i++)ElementFX.bolt(c,b,[b[0]+(i?15:-15),b[1]-12],age,1.5);
}else if(move==='번개'){
 ElementFX.bolt(c,[b[0]-8,Math.max(30,b[1]-115)],b,age,4);ElementFX.bolt(c,[b[0]+18,Math.max(35,b[1]-65)],b,age,1.5);ring(c,b,10+age*12,'#fff0aa');
}else if(move==='섀도볼'){
 const g=c.createRadialGradient(...p,1,...p,14);g.addColorStop(0,'#38204b');g.addColorStop(.5,'#9556c8');g.addColorStop(1,'#bf8cea00');c.fillStyle=g;c.beginPath();c.arc(...p,14,0,Math.PI*2);c.fill();ring(c,p,11,'#d6b2f1');if(travel===1)ring(c,b,14+age*9,'#a774cf');
}else if(move==='눈보라'){
 for(let i=0;i<7;i++){const t=i*2.4+age*4,r=8+i*3,q=[b[0]+Math.cos(t)*r,b[1]+Math.sin(t)*r];c.strokeStyle='#c9f5fa';c.lineWidth=1.5;for(let j=0;j<3;j++)line(c,[q[0]-Math.cos(j*Math.PI/3)*4,q[1]-Math.sin(j*Math.PI/3)*4],[q[0]+Math.cos(j*Math.PI/3)*4,q[1]+Math.sin(j*Math.PI/3)*4],'#c9f5fa',1.5);}
}else if(move==='사이코키네시스'){
 c.save();c.translate(...b);c.rotate(age*3);for(let i=0;i<3;i++){c.strokeStyle=['#e59adb','#cf9aee','#f7caee'][i];c.lineWidth=1.5;c.beginPath();c.ellipse(0,0,14+i*4,6+i*3,i,0,Math.PI*2);c.stroke();}c.restore();
}else if(move==='파괴광선'){
 if(age<.25)ring(c,a,5+age*35,'#ffdab2',2);else{line(c,a,b,'#e7a16a',10);line(c,a,b,'#fff6d1',3);ring(c,b,9+age*12,'#ffd299',2);}
}else{
 const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);for(let i=0;i<3;i++)line(c,[p[0]-Math.cos(angle)*17,p[1]-7+i*7],[p[0],p[1]-7+i*7],'#f6e5c4',2);ring(c,b,8+age*9,'#fff1d5',2);
}
// At most three secondary marks, rather than eight overlapping large explosions.
for(const t of e.targets.slice(1,4)){if(age>.55){const q=Battlefield.xy(...Battlefield.position(t));ring(c,q,4+(age-.55)*12,'#e8f1bc',1);}}
c.restore();}
return{draw,fireGlyph};
})();

