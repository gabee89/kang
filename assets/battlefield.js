/* Code-drawn scenery, cached once; route and combat use the same map data. */
window.Battlefield=(()=>{
const xy=(x,y)=>[65+x*77,60+y*76];
const symbols={grass:'♣',fire:'▲',water:'≈',electric:'ϟ',neutral:'·'};
const palette={grass:'#91d479',fire:'#ffaf76',water:'#8adcf4',electric:'#f4df80',neutral:'#b1bd99'};
let map,back,length=0;
function position(t){t=Math.max(0,Math.min(length,t));for(let i=1;i<map.route.length;i++){const a=map.route[i-1],b=map.route[i],d=Math.hypot(b[0]-a[0],b[1]-a[1]);if(t<=d)return[a[0]+(b[0]-a[0])*t/d,a[1]+(b[1]-a[1])*t/d];t-=d;}return map.route.at(-1);}
function init(data){map=data;length=map.route.slice(1).reduce((sum,b,i)=>sum+Math.hypot(b[0]-map.route[i][0],b[1]-map.route[i][1]),0);back=document.createElement('canvas');back.width=900;back.height=580;const c=back.getContext('2d');
const gradient=c.createLinearGradient(0,0,900,580);gradient.addColorStop(0,'#537848');gradient.addColorStop(.5,'#365b3e');gradient.addColorStop(1,'#243d34');c.fillStyle=gradient;c.fillRect(0,0,900,580);
// Deterministic textures: all clients see the same forest.
for(let i=0;i<900;i++){const x=(i*137.43)%900,y=(i*73.19)%580;c.fillStyle=i%3?'#b7ce7b14':'#102e2330';c.fillRect(x,y,3+i%5,2);}
function ellipse(x,y,rx,ry,color){c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fill();}
// Pool with grassy banks and a little wooden landing.
ellipse(681,387,155,80,'#789965');ellipse(683,388,144,70,'#244d55');ellipse(685,383,135,61,'#397581');ellipse(689,378,116,48,'#458e98');
for(let i=0;i<18;i++){const x=590+i*12,y=365+(i*19)%56;c.strokeStyle='#a6d6bb50';c.lineWidth=2;c.beginPath();c.moveTo(x,y);c.lineTo(x+15,y);c.stroke();}for(let i=0;i<5;i++){c.fillStyle='#9f8258';c.fillRect(535,376+i*8,58,6);}ellipse(780,404,10,4,'#8db66e');ellipse(756,358,8,4,'#9ac179');
// Curving woodland route: dark banks, warm dirt, individual stones.
const points=map.route.map(p=>xy(...p));function path(){c.beginPath();points.forEach((p,i)=>i?c.lineTo(...p):c.moveTo(...p));}c.lineJoin='round';c.lineCap='round';path();c.strokeStyle='#193b2c';c.lineWidth=57;c.stroke();path();c.strokeStyle='#8d9860';c.lineWidth=48;c.stroke();path();c.strokeStyle='#cab68a';c.lineWidth=38;c.stroke();
for(let t=0;t<length;t+=.31){const [x,y]=xy(...position(t));c.fillStyle=Math.floor(t*10)%2?'#e0c99f':'#b6a27c';c.beginPath();c.roundRect(x-9+(t%1)*8,y-7,14,10,3);c.fill();}
for(const z of map.zones){c.strokeStyle=z.color;c.lineWidth=34;c.lineCap='butt';c.beginPath();for(let t=z.start;t<=z.end+.001;t+=.1){const p=xy(...position(t));if(t===z.start)c.moveTo(...p);else c.lineTo(...p);}c.stroke();}
const flank=xy(10,2.5);ellipse(flank[0],flank[1],21,25,'#4d4667');ellipse(flank[0],flank[1],12,18,'#b6a4d1');c.fillStyle='#eee2ff';c.font='bold 10px sans-serif';c.fillText('4R+ 샛길 기습',751,222);
// Pines, flowers and stones frame the route without hiding placement cells.
function tree(x,y,s){ellipse(x+4,y+19*s,22*s,9*s,'#152c2855');c.fillStyle='#65523b';c.fillRect(x-4*s,y,8*s,22*s);for(let j=0;j<3;j++){c.fillStyle=['#214c3b','#2b6243','#43805a'][j];c.beginPath();c.moveTo(x,y-40*s+j*15*s);c.lineTo(x-22*s+j*3*s,y+j*11*s);c.lineTo(x+22*s-j*3*s,y+j*11*s);c.closePath();c.fill();}}
for(let i=0;i<22;i++){tree(22+i*41,15+(i%3)*6,.65+(i%3)*.12);tree(20+i*42,573+(i%2)*7,.75);}
for(let i=0;i<9;i++){tree(8,105+i*47,.65);tree(886,102+i*45,.7);}
for(let i=0;i<48;i++){const x=110+(i*61)%670,y=176+(i*43)%275;if(map.cells.some(p=>{const q=xy(...p);return Math.abs(x-q[0])<52&&Math.abs(y-q[1])<49;})||Math.abs(y-250)<27)continue;ellipse(x,y,7,3,'#285135');c.fillStyle=['#efd7a0','#e49da0','#d0da83'][i%3];c.fillRect(x,y-5,3,4);}
// Portal cave and healer's cabin mark the actual route endpoints.
ellipse(65,51,28,22,'#607869');ellipse(65,55,19,16,'#132e2a');c.fillStyle='#b5e8cf';c.fillRect(61,48,8,15);
const [bx,by]=xy(...map.route.at(-1));c.fillStyle='#d8cfaf';c.fillRect(bx-20,by-13,40,34);c.fillStyle='#a96550';c.beginPath();c.moveTo(bx-27,by-13);c.lineTo(bx,by-35);c.lineTo(bx+27,by-13);c.fill();c.fillStyle='#423d32';c.fillRect(bx-6,by+5,12,16);c.fillStyle='#f4eac6';c.fillRect(bx-7,by-19,14,4);c.fillRect(bx-2,by-24,4,14);
for(let i=0;i<map.cells.length;i++){const [x,y]=xy(...map.cells[i]),role=map.terrain[i];ellipse(x,y+34,44,10,'#152b254d');c.fillStyle=role==='water'?'#597e80':'#60775a';c.beginPath();c.roundRect(x-map.tileWidth/2,y-36,map.tileWidth,72,9);c.fill();c.fillStyle=role==='neutral'?'#4c6249':palette[role]+'40';c.beginPath();c.roundRect(x-map.tileWidth/2+3,y-33,map.tileWidth-6,64,8);c.fill();c.strokeStyle=palette[role]+'70';c.lineWidth=1;c.stroke();c.textAlign='center';c.fillStyle=palette[role];c.font='bold 17px sans-serif';c.fillText(symbols[role],x,y+5);}
c.textAlign='left';c.font='bold 11px sans-serif';c.fillStyle='#f7eac6';c.fillText('숲의 입구 →',33,91);c.fillText('회복 기지',804,563);c.fillStyle='#e9ddc4';c.fillText('진흙 · 이동 -35%',435,222);c.fillText('바람 · 이동 +35%',222,542);
}
function draw(c,time){if(!back)return;c.drawImage(back,0,0);const t=time/1000;
// Moving chevrons and fireflies give the scene motion, including between waves.
c.textAlign='center';for(let s=(t*.7)%2;s<length;s+=2){const p=xy(...position(s)),q=xy(...position(Math.min(length,s+.1)));c.save();c.translate(...p);c.rotate(Math.atan2(q[1]-p[1],q[0]-p[0]));c.strokeStyle='#f9f0cb80';c.lineWidth=2;c.beginPath();c.moveTo(-4,-4);c.lineTo(0,0);c.lineTo(-4,4);c.stroke();c.restore();}
for(let i=0;i<13;i++){const x=120+(i*59)%680+Math.sin(t*.6+i)*9,y=115+(i*47)%345+Math.cos(t*.8+i)*7;c.globalAlpha=.3+.25*Math.sin(t*2+i);c.fillStyle='#eeef9e';c.beginPath();c.arc(x,y,2,0,Math.PI*2);c.fill();}c.globalAlpha=1;
}
return{init,draw,xy,position,symbols,palette,get data(){return map;}};
})();

