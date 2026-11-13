/* Local animation atlases: frame animation plus attack poses work on canvas. */
window.Actors=(()=>{
const typeNames={normal:'노말',fire:'불',water:'물',grass:'풀',electric:'전기',ice:'얼음',poison:'독',flying:'비행',bug:'벌레',ground:'땅',rock:'바위',fighting:'격투',dragon:'드래곤'};let manifest={},images={},clock=0;const scratch=document.createElement('canvas');scratch.width=scratch.height=96;const sc=scratch.getContext('2d');
async function init(data){manifest=data;await Promise.all(Object.keys(data).map(id=>new Promise(resolve=>{const im=new Image();images[id]=im;im.onload=resolve;im.onerror=resolve;im.src='/assets/sprites/'+id+'.png';})));}
function sprite(c,dex,x,y,size,time,white=0){const im=images[dex],d=manifest[dex];if(!im?.naturalWidth||!d)return false;const frame=Math.floor(time/d.frameMs)%d.frames;c.imageSmoothingEnabled=true;c.imageSmoothingQuality='high';c.save();c.shadowColor='#173c36aa';c.shadowBlur=3;c.shadowOffsetY=2;c.drawImage(im,frame*96,0,96,96,x-size/2,y-size/2,size,size);c.restore();if(white>0){sc.clearRect(0,0,96,96);sc.globalCompositeOperation='source-over';sc.drawImage(im,frame*96,0,96,96,0,0,96,96);sc.globalCompositeOperation='source-in';sc.fillStyle='#fff';sc.fillRect(0,0,96,96);c.save();c.globalAlpha=white;c.drawImage(scratch,x-size/2,y-size/2,size,size);c.restore();}return true;}
function monsters(c,p,time){clock=time;for(const e of p.enemies){const [x,y]=Battlefield.xy(...Battlefield.position(Motion.enemyProgress(p.id,e,time),e.direction||1)),boss=e.boss,size=e.bossRank==='boss'?130:boss?112:74,bob=Math.sin(time*.008+e.id)*1.1;
c.save();c.textAlign='center';c.fillStyle='#102a2866';c.beginPath();c.ellipse(x,y+14,boss?30:17,boss?9:5,0,0,Math.PI*2);c.fill();
if(e.burn>0)ElementFX.projectile(c,[x-8,y+12],[x+4,y-4],'fire',.4,false);
if(e.stun>0)ElementFX.projectile(c,[x-18,y-8],[x+18,y+8],'electric',(time%650)/650,false);
if(e.slow>0){c.strokeStyle='#99e8ff';c.lineWidth=2;c.beginPath();c.ellipse(x,y+15,22,8,0,0,Math.PI*2);c.stroke();}
if(e.poison>0||e.curse>0){c.fillStyle='#b88bee88';c.beginPath();c.arc(x+Math.sin(time*.005)*15,y-12,8,0,Math.PI*2);c.fill();}
if(e.wet>0){c.fillStyle='#8be4ff';c.beginPath();c.ellipse(x+17,y+1,3,6,0,0,Math.PI*2);c.fill();}
if(e.expose>0){c.strokeStyle='#f5a0dc';c.lineWidth=2;c.strokeRect(x-20,y-26,40,40);}
if(e.poison>0){c.font='bold 10px sans-serif';c.fillStyle='#d5b6f5';c.fillText('독'+(e.poisonStacks||1),x,y-34);}
if(e.shield>0){c.strokeStyle='#a4d5fa';c.lineWidth=2;c.beginPath();c.ellipse(x,y-5,25,30,0,0,Math.PI*2);c.stroke();}
if(e.golden||boss){c.strokeStyle=e.bossRank==='boss'?'#ff8065':'#ffe08a';c.lineWidth=2;c.beginPath();c.ellipse(x,y+10,boss?35:21,boss?13:7,0,0,Math.PI*2);c.stroke();}
if(!sprite(c,e.dex,x,y-9+bob,size,time,CombatFX.hit(p.id,e.id,time)?.8:0)){c.fillStyle=boss?'#d68771':'#b6bc79';c.beginPath();c.ellipse(x,y,17,19,0,0,Math.PI*2);c.fill();c.fillStyle='#263626';c.fillRect(x-7,y-4,4,5);c.fillRect(x+4,y-4,4,5);}
const w=boss?84:44;c.fillStyle='#192c29';c.fillRect(x-w/2,y-size*.5-15,w,5);c.fillStyle=e.bossRank==='boss'?'#ff7d68':e.golden?'#f8d86b':'#b8dd80';c.fillRect(x-w/2,y-size*.5-15,w*Math.max(0,e.hp/e.maxHp),5);
c.restore();}}
function units(c,p,selected,catalog,time){const map=Battlefield.data,w=map.tileWidth||56,h=map.tileHeight||72;for(const u of p.units){const d=catalog[u.dex];if(!d)continue;const stack=p.units.filter(v=>v.cell===u.cell),index=stack.findIndex(v=>v.id===u.id),n=stack.length;const [x,y]=Motion.unitPoint(p.id,u,time),pose=CombatFX.pose(p.id,u,time),terrain=map.terrain[u.cell],color=Battlefield.palette[d.role]||'#bcace8';c.save();c.textAlign='center';if(u.id===selected){c.strokeStyle='#eeff9e';c.lineWidth=2;c.beginPath();c.ellipse(x,y+12,23,8,0,0,Math.PI*2);c.stroke();}const offsets=n===1?[[0,0]]:n===2?[[-14,0],[14,0]]:[[-14,-8],[14,-8],[0,15]],off=offsets[index]||[0,0];c.fillStyle='#173b344d';c.beginPath();c.ellipse(x,y+12,19,5,0,0,Math.PI*2);c.fill();c.save();c.translate(x+off[0]+pose.dx,y-6+off[1]+pose.dy);c.rotate(pose.angle||0);const dex=pose.evolving&&pose.age<.38?pose.fromDex:u.dex;const white=pose.evolving?Math.max(0,Math.sin(pose.age*Math.PI))*.85:0;sprite(c,dex,0,0,(map.spriteSize||76)*(n>1?.76:1)*pose.scale,time,white);c.restore();if(index===0){c.font='bold 8px sans-serif';c.strokeStyle='#15342c';c.lineWidth=3;const label=n>1?'×'+n:'';if(label){c.strokeText(label,x+w/2-8,y+h/2+7);c.fillStyle='#f5f8dc';c.fillText(label,x+w/2-8,y+h/2+7);}c.fillStyle='#112b2a';c.fillRect(x-22,y+h/2+3,44,3);c.fillStyle=u.energy>=100?'#fff4ae':'#8addff';c.fillRect(x-22,y+h/2+3,44*(u.energy||0)/100,3);}c.restore();}}
return{init,sprite,monsters,units,get ready(){return Object.values(images).filter(i=>i.naturalWidth).length;}};
})();


