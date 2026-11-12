/* Visual interpolation only: server positions and combat remain authoritative. */
window.Motion=(()=>{
const enemies=new Map(),units=new Map();const delay=90,duration=180;
const key=(owner,id)=>owner+':'+id;
const ease=t=>t*t*(3-2*t);
function reset(){enemies.clear();units.clear();}
function point(track,now){const t=ease(Math.max(0,Math.min(1,(now-track.start)/duration)));return track.from.map((v,i)=>v+(track.to[i]-v)*t);}
function ingest(state,now=performance.now()){
 const liveEnemies=new Set(),liveUnits=new Set();
 for(const p of state.players){for(const e of p.enemies){const id=key(p.id,e.id);liveEnemies.add(id);const samples=enemies.get(id)||[];samples.push({time:now,progress:e.progress});enemies.set(id,samples.slice(-5));}
 if(!Battlefield.data)continue;
 for(const u of p.units){const id=key(p.id,u.id);liveUnits.add(id);const destination=Battlefield.xy(...Battlefield.data.cells[u.cell]),old=units.get(id);if(!old)units.set(id,{cell:u.cell,from:destination,to:destination,start:now});else if(old.cell!==u.cell)units.set(id,{cell:u.cell,from:point(old,now),to:destination,start:now});}}
 for(const id of enemies.keys())if(!liveEnemies.has(id))enemies.delete(id);
 for(const id of units.keys())if(!liveUnits.has(id))units.delete(id);
}
function enemyProgress(owner,enemy,now){const samples=enemies.get(key(owner,enemy.id));if(!samples?.length)return enemy.progress;const at=now-delay;if(at<=samples[0].time)return samples[0].progress;for(let i=1;i<samples.length;i++){const a=samples[i-1],b=samples[i];if(at<=b.time){const t=(at-a.time)/Math.max(1,b.time-a.time);return a.progress+(b.progress-a.progress)*t;}}const b=samples.at(-1),a=samples.at(-2);if(!a)return b.progress;const velocity=(b.progress-a.progress)/Math.max(1,b.time-a.time);return b.progress+Math.max(0,velocity)*Math.min(30,Math.max(0,at-b.time));}
function unitPoint(owner,unit,now){const track=units.get(key(owner,unit.id));return track?point(track,now):Battlefield.xy(...Battlefield.data.cells[unit.cell]);}
return{ingest,reset,enemyProgress,unitPoint};
})();

