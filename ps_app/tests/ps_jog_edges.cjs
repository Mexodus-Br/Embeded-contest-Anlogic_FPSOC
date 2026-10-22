const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('web/ps/app.js','utf8');
const begin=source.match(/^async function beginJog\(.*$/m)[0];
const end=source.match(/^async function endJog\(.*$/m)[0];
const id=source.match(/function commandId\(\)\{[\s\S]*?\n\}/)[0];
async function scenario(kind){
 const context={assert,Uint8Array,kind,crypto:{getRandomValues:a=>require('node:crypto').webcrypto.getRandomValues(a)}};
 return vm.runInNewContext(`
 let jog=null,state={boot_id:'boot',stop_epoch:'0',monotonic_us:'1000'},release,calls=[],timers=0;
 const $=()=>({value:'1'}),message=()=>{},clearInterval=()=>{},setInterval=()=>{timers++;return 1;};
 async function refresh(){await new Promise(resolve=>release=resolve);}
 async function api(path){calls.push(path);return {};}
 async function stop(){calls.push('STOP');state.stop_epoch='1';}
 ${id}
 ${begin}
 ${end}
 (async()=>{
   const pending=beginJog({disabled:false,dataset:{axis:'x',sign:'1'}},{preventDefault(){}});
   await Promise.resolve();
   if(kind==='release')await endJog();
   if(kind==='epoch')state.stop_epoch='1';
   if(kind==='boot')state.boot_id='new_boot';
   release();await pending;
   if(kind==='healthy'){assert.deepEqual(calls,['/jog/start']);assert.equal(timers,1);await endJog();}
   else {assert(!calls.includes('/jog/start'));assert.equal(timers,0);}
   assert.equal(jog,null);
   if(kind==='release'){const saved=crypto;crypto=undefined;assert.throws(commandId);crypto=saved;}
   return {case:kind,passed:true};
 })()`,context);
}
(async()=>{const results=[];for(const kind of ['release','epoch','boot','healthy'])results.push(await scenario(kind));console.log(JSON.stringify(results));})().catch(e=>{console.error(e);process.exitCode=1;});
