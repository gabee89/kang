/* Soft diorama terrain with an arc-length sampled shared combat route. */
window.Battlefield=(()=>{
const xy=(x,y)=>[65+x*77,60+y*76];
const symbols={grass:'♣',fire:'▲',water:'≈',electric:'ϟ',neutral:'·'};
const palette={grass:'#a9d796',fire:'#e8b083',water:'#a3dce4',electric:'#eed79a',neutral:'#c4ceb0'};
let map,back,length=0,cumulative=[],artReady=false;const terrain=new Image();
function position(value){if(!map)return[0,0];const t=Math.max(0,Math.min(length,value));let lo=0,hi=cumulative.length-1;while(lo+1<hi){const m=(lo+hi)>>1;if(cumulative[m]<=t)lo=m;else hi=m;}const a=map.route[lo],b=map.route[Math.min(lo+1,map.route.length-1)],d=cumulative[Math.min(lo+1,cumulative.length-1)]-cumulative[lo],f=d?(t-cumulative[lo])/d:0;return[a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f];}
function ellipse(c,x,y,rx,ry,color){c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fill();}
function route(c,offset=0){c.beginPath();map.route.forEach((p,i)=>{const [x,y]=xy(...p);if(i)c.lineTo(x,y+offset);else c.moveTo(x,y+offset);});}
function portal(c,p,scale=1,flank=false,time=0){c.save();c.translate(...p);c.scale(scale,scale);ellipse(c,0,18,31,11,'#0b272a66');
const rock=c.createLinearGradient(-25,-25,25,25);rock.addColorStop(0,'#d4d9c5');rock.addColorStop(.45,'#8faaa2');rock.addColorStop(1,'#3e6260');
c.fillStyle=rock;c.beginPath();c.moveTo(-29,18);c.lineTo(-28,-10);c.quadraticCurveTo(-25,-38,0,-39);c.quadraticCurveTo(26,-38,28,-9);c.lineTo(30,18);c.closePath();c.fill();c.strokeStyle='#d6ddc488';c.lineWidth=2;c.stroke();
const glow=c.createRadialGradient(0,-7,2,0,-7,28);glow.addColorStop(0,flank?'#c9b8f4':'#caf8e7');glow.addColorStop(.5,flank?'#7d77c8':'#56b6ab');glow.addColorStop(1,'#143a42');c.fillStyle=glow;c.beginPath();c.ellipse(0,-5,19,29,0,0,Math.PI*2);c.fill();
c.strokeStyle=flank?'#c2a9df99':'#d6f9da99';c.lineWidth=1.2;for(let i=0;i<3;i++){c.beginPath();c.ellipse(0,-5,8+i*3,14+i*4,Math.sin(time*.0006+i)*.15,0,Math.PI*2);c.stroke();}for(let i=0;i<5;i++){c.fillStyle='#dcead4';c.fillRect(-23+i*11,-28+(i%2)*3,3,4);}c.restore();}
function base(c,p){c.save();c.translate(...p);ellipse(c,0,20,42,15,'#11282966');
// Foundation, rounded masonry walls and a softly lit tiled roof.
c.fillStyle='#577a7a';c.beginPath();c.roundRect(-37,4,74,25,10);c.fill();c.fillStyle='#a8bbb0';c.beginPath();c.roundRect(-35,-5,70,27,8);c.fill();
const wall=c.createLinearGradient(-28,-35,28,22);wall.addColorStop(0,'#f0ead1');wall.addColorStop(.6,'#c5d6c7');wall.addColorStop(1,'#7b9a94');c.fillStyle=wall;c.beginPath();c.roundRect(-27,-35,54,50,8);c.fill();
const roof=c.createLinearGradient(-30,-62,27,-14);roof.addColorStop(0,'#ddac7c');roof.addColorStop(.4,'#ae795d');roof.addColorStop(1,'#704f49');c.fillStyle=roof;c.beginPath();c.moveTo(-38,-31);c.quadraticCurveTo(-20,-56,0,-67);c.quadraticCurveTo(23,-54,38,-31);c.lineTo(28,-20);c.lineTo(0,-47);c.lineTo(-28,-20);c.closePath();c.fill();
c.strokeStyle='#f0ceb28c';c.lineWidth=1.3;for(let i=0;i<5;i++){c.beginPath();c.moveTo(-27+i*6,-29-i*6);c.lineTo(i*5,-49+i*2);c.stroke();}
c.fillStyle='#244c57';c.beginPath();c.roundRect(-9,-5,18,22,[8,8,1,1]);c.fill();c.fillStyle='#b6e5df';c.fillRect(-22,-15,8,10);c.fillRect(14,-15,8,10);c.strokeStyle='#e7e8ce';c.lineWidth=2;c.strokeRect(-22,-15,8,10);c.strokeRect(14,-15,8,10);
ellipse(c,0,-25,10,10,'#477f82');c.fillStyle='#f6efcf';c.fillRect(-5,-27,10,3);c.fillRect(-1.5,-31,3,11);c.restore();}
function pedestal(c,p,role){const [x,y]=p,w=map.tileWidth;const compact=map.tileHeight===52;c.save();c.translate(0,compact?y*.25:0);c.scale(1,compact?.75:1);ellipse(c,x+2,y+32,w*.49,7,'#123f3338');c.fillStyle='#486b66';c.beginPath();c.roundRect(x-w/2,y-29,w,64,10);c.fill();
const g=c.createLinearGradient(x-20,y-35,x+20,y+27);g.addColorStop(0,'#e5e7cb');g.addColorStop(.28,'#b8c8af');g.addColorStop(1,'#6f9b87');c.fillStyle=g;c.beginPath();c.roundRect(x-w/2,y-35,w,64,10);c.fill();c.strokeStyle='#eef1d880';c.lineWidth=1;c.stroke();
c.fillStyle=role==='neutral'?'#44685b44':palette[role]+'65';c.beginPath();c.roundRect(x-w/2+4,y-31,w-8,55,8);c.fill();c.textAlign='center';c.fillStyle=role==='neutral'?'#405e54':palette[role];c.font='bold 14px sans-serif';c.shadowColor='#274b45';c.shadowBlur=1;c.fillText(symbols[role],x,y+2);c.shadowBlur=0;c.restore();}
function paint(){if(!map)return;back=document.createElement('canvas');back.width=1800;back.height=1160;const c=back.getContext('2d');c.scale(2,2);c.imageSmoothingEnabled=true;
if(artReady)c.drawImage(terrain,0,0,900,580);else{c.fillStyle='#4b775c';c.fillRect(0,0,900,580);}
// Soft cool wash makes tiny combat sprites readable against the sunlit terrain.
c.fillStyle='#133e2d18';c.fillRect(0,0,900,580);c.lineJoin='round';c.lineCap='round';route(c,5);c.strokeStyle='#183c3675';c.lineWidth=50;c.stroke();route(c,2);c.strokeStyle='#668176';c.lineWidth=44;c.stroke();route(c);c.strokeStyle='#e2dec4';c.lineWidth=39;c.stroke();
const paving=c.createLinearGradient(0,20,0,560);paving.addColorStop(0,'#d9d2b8');paving.addColorStop(.5,'#bdc2ac');paving.addColorStop(1,'#acb6a0');route(c);c.strokeStyle=paving;c.lineWidth=34;c.stroke();
for(let s=.12;s<length;s+=.16){const p=xy(...position(s)),q=xy(...position(Math.min(length,s+.03))),angle=Math.atan2(q[1]-p[1],q[0]-p[0]);c.save();c.translate(...p);c.rotate(angle);const band=Math.floor(s*20)%2?7:-7;c.fillStyle='#5f7b6844';c.beginPath();c.roundRect(-5,band-3,11,11,3);c.fill();c.fillStyle=['#e2dcc4','#c6ccb6','#d3d5be'][Math.floor(s*30)%3];c.beginPath();c.roundRect(-5,band-5,11,10,3);c.fill();c.strokeStyle='#fbf5de88';c.lineWidth=.6;c.stroke();c.restore();}
for(const z of map.zones){c.strokeStyle=z.color+'80';c.lineWidth=28;c.beginPath();for(let s=z.start;s<=z.end;s+=.08){const p=xy(...position(s));if(s===z.start)c.moveTo(...p);else c.lineTo(...p);}c.stroke();}
// A raised timber crossing adds material variation on the lower winding road.
const bridgeAt=length*.82;for(let i=0;i<9;i++){const p=xy(...position(bridgeAt+i*.12)),q=xy(...position(bridgeAt+i*.12+.02));c.save();c.translate(...p);c.rotate(Math.atan2(q[1]-p[1],q[0]-p[0]));c.fillStyle='#3f62575c';c.fillRect(-4,-18,9,40);const wood=c.createLinearGradient(-4,-15,5,15);wood.addColorStop(0,'#cbb38c');wood.addColorStop(1,'#8d8367');c.fillStyle=wood;c.beginPath();c.roundRect(-4,-18,9,35,2);c.fill();c.strokeStyle='#eee0b58c';c.lineWidth=.8;c.stroke();c.restore();}
for(let i=0;i<map.cells.length;i++)pedestal(c,xy(...map.cells[i]),map.terrain[i]);
portal(c,xy(...map.route[0]),1,false);portal(c,xy(...position(map.flankProgress)),.68,true);base(c,xy(...map.route.at(-1)));
c.font='bold 10px sans-serif';c.textAlign='center';c.strokeStyle='#234d43';c.lineWidth=3;c.fillStyle='#eff2cf';for(const [text,p] of [['몬스터 포털',xy(...map.route[0])],['방어 기지',xy(...map.route.at(-1))]]){c.strokeText(text,p[0],p[1]+36);c.fillText(text,p[0],p[1]+36);}
}
function init(data){map=data;cumulative=[0];data.route.slice(1).forEach((p,i)=>cumulative.push(cumulative.at(-1)+Math.hypot(p[0]-data.route[i][0],p[1]-data.route[i][1])));length=cumulative.at(-1);paint();terrain.onload=()=>{artReady=true;paint();};terrain.onerror=()=>{artReady=false;};terrain.src='/assets/terrain-v3.webp';}
function draw(c,time){if(!back)return;c.imageSmoothingEnabled=true;c.drawImage(back,0,0,900,580);c.save();c.globalAlpha=.46;c.strokeStyle='#f3f3d7';c.lineWidth=1.3;for(let s=(time*.00065)%2.1;s<length;s+=2.1){const p=xy(...position(s)),q=xy(...position(Math.min(length,s+.04)));c.save();c.translate(...p);c.rotate(Math.atan2(q[1]-p[1],q[0]-p[0]));c.beginPath();c.moveTo(-3,-3);c.lineTo(0,0);c.lineTo(-3,3);c.stroke();c.restore();}
const start=xy(...map.route[0]);c.strokeStyle='#cefae577';for(let i=0;i<3;i++){c.beginPath();c.ellipse(start[0],start[1]-5,8+i*3,14+i*4,Math.sin(time*.0006+i)*.15,0,Math.PI*2);c.stroke();}c.restore();}
return{init,draw,xy,position,symbols,palette,get data(){return map;},get artReady(){return artReady;}};
})();

