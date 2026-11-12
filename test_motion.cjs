const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={window:{},performance:{now:()=>0},Battlefield:{data:{cells:[[0,0],[10,0]]},xy:(x,y)=>[x,y]}};
vm.runInNewContext(fs.readFileSync(__dirname+'/assets/motion.js','utf8'),sandbox);
const motion=sandbox.window.Motion;
const state=(progress,cell=0)=>({players:[{id:1,enemies:[{id:7,progress}],units:[{id:9,cell}]}]});
motion.ingest(state(0),0);motion.ingest(state(1,1),100);
assert(Math.abs(motion.enemyProgress(1,{id:7},150)-.6)<1e-9);
assert(Math.abs(motion.enemyProgress(1,{id:7},160)-.7)<1e-9);
assert.equal(motion.unitPoint(1,{id:9,cell:1},100)[0],0);
assert.equal(motion.unitPoint(1,{id:9,cell:1},190)[0],5);
assert.equal(motion.unitPoint(1,{id:9,cell:1},280)[0],10);
motion.ingest(state(2,1),200);
assert(Math.abs(motion.enemyProgress(1,{id:7},200)-1.1)<1e-9);
assert(Math.abs(motion.enemyProgress(1,{id:7},1000)-2.3)<1e-9);
motion.ingest(state(2,1),300);
assert.equal(motion.enemyProgress(1,{id:7},1000),2);
motion.reset();assert.equal(motion.enemyProgress(1,{id:7,progress:10},200),10);
console.log('PASS: smooth monster frames, bounded extrapolation, stop updates, unit movement and reset');

