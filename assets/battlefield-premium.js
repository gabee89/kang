/* Follow the meadow passages in the background; no paved-road overlay. */
window.Battlefield=(()=>{
const xy=(x,y)=>[65+x*77,60+y*76];
const symbols={grass:'♣',fire:'▲',water:'≈',electric:'ϟ',ghost:'◌'};
const palette={grass:'#a9d796',fire:'#e8b083',water:'#a3dce4',electric:'#eed79a',ghost:'#c7b4ed'};
let map,length=0,cumulative=[],artReady=false;
const terrain=new Image(),reduced=matchMedia('(prefers-reduced-motion: reduce)');
function position(value,direction=1){
 if(!map)return[0,0];
 const t=Math.max(0,Math.min(length,direction===-1?length-value:value));
 let lo=0,hi=cumulative.length-1;
 while(lo+1<hi){const m=(lo+hi)>>1;if(cumulative[m]<=t)lo=m;else hi=m;}
 const a=map.route[lo],b=map.route[Math.min(lo+1,map.route.length-1)],d=cumulative[Math.min(lo+1,cumulative.length-1)]-cumulative[lo],f=d?(t-cumulative[lo])/d:0;
 return[a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f];
}
function init(data){
 map=data;cumulative=[0];data.route.slice(1).forEach((p,i)=>cumulative.push(cumulative.at(-1)+Math.hypot(p[0]-data.route[i][0],p[1]-data.route[i][1])));length=cumulative.at(-1);
 terrain.onload=()=>{artReady=true;};terrain.onerror=()=>{artReady=false;};terrain.src='/assets/terrain-regions-v4.webp';
}
function span(plan={}){const direction=plan.direction===-1?-1:1;return{direction,start:plan.entry==='shortcut'?map.flankProgress:direction===1?0:length,end:direction===1?length:0};}
function draw(c,time,plan){
 if(!map)return;
 if(artReady)c.drawImage(terrain,0,0,900,580);else{c.fillStyle='#4b775c';c.fillRect(0,0,900,580);}
 const {direction,start,end}=span(plan||{}),low=Math.min(start,end),high=Math.max(start,end);
 let points=[position(low),...map.route.filter((p,i)=>cumulative[i]>low&&cumulative[i]<high),position(high)];
 if(direction===-1)points.reverse();
 c.save();c.lineCap='round';c.lineJoin='round';c.beginPath();points.forEach((p,i)=>{const [x,y]=xy(...p);i?c.lineTo(x,y):c.moveTo(x,y);});
 c.strokeStyle='#c2f4ee24';c.lineWidth=12;c.stroke();c.strokeStyle='#e7fffa85';c.lineWidth=2;c.setLineDash([8,9]);c.stroke();c.setLineDash([]);
 const travel=Math.abs(end-start),phase=reduced.matches?0:(time*.00055)%1.5;
 for(let d=phase;d<travel;d+=1.5){const s=start+direction*d,p=xy(...position(s)),q=xy(...position(Math.max(0,Math.min(length,s+direction*.06))));c.save();c.translate(...p);c.rotate(Math.atan2(q[1]-p[1],q[0]-p[0]));c.strokeStyle='#eafff6bb';c.lineWidth=2;c.beginPath();c.moveTo(-5,-4);c.lineTo(0,0);c.lineTo(-5,4);c.stroke();c.restore();}
 for(const [s,label,color] of [[start,'진입','#d9f9bc'],[end,'도착','#f5dba4']]){const [x,y]=xy(...position(s));c.strokeStyle=color;c.lineWidth=2;c.beginPath();c.arc(x,y,12,0,Math.PI*2);c.stroke();c.textAlign='center';c.font='bold 10px sans-serif';c.strokeStyle='#1c3c32';c.lineWidth=3;c.strokeText(label,x,y+25);c.fillStyle=color;c.fillText(label,x,y+25);}
 c.restore();
}
function placement(c,player,selected,catalog){
 if(!map||!selected)return;
 const group=player.units.filter(u=>u.cell===selected.cell),limit=catalog[selected.dex]?.evolution?3:2;
 c.save();c.font='bold 10px sans-serif';c.textAlign='center';
 map.cells.forEach((cell,i)=>{const [x,y]=xy(...cell),others=player.units.filter(u=>u.cell===i&&u.cell!==selected.cell),valid=!others.length||others[0].dex!==selected.dex||others.length+group.length<=limit,current=i===selected.cell;
 c.fillStyle=current?'#f7e2a04d':valid?'#b8edbf26':'#d9918c26';c.strokeStyle=current?'#ffecb5':valid?'#b8efc7aa':'#d9918c88';c.lineWidth=current?2:1;c.beginPath();c.roundRect(x-36,y-34,72,68,12);c.fill();c.stroke();c.fillStyle='#f3f5df';const names={grass:'풀숲',fire:'화염',water:'호수',electric:'전기',ghost:'고스트'}; const label=(i+1)+' · '+names[map.terrain[i]]; c.font='bold 12px sans-serif'; c.strokeStyle='#142620'; c.lineWidth=3; c.strokeText(label,x,y+29); c.fillText(label,x,y+29);});c.restore();
}
return{init,draw,placement,xy,position,symbols,palette,get data(){return map;},get artReady(){return artReady;}};
})();
