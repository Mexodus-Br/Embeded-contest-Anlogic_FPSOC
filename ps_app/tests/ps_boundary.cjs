const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('web/ps/app.js','utf8');
const functions=['beginJog','endJog','stop'].map(n=>source.match(new RegExp('^async function '+n+'\\(.*$','m'))[0]).join('\n');
const id=source.match(/function commandId\(\)\{[\s\S]*?\n\}/)[0];
const config=process.env.PS_BROWSER_TEST?JSON.parse(process.env.PS_BROWSER_TEST):null;
async function main(){
 const calls=[];
 async function request(path,method='GET',body){
   calls.push(path);
   if(!config)return path==='/stop'?{stop_epoch:'1'}:{};
   const response=await fetch(config.base+'/api/v1'+path,{method,headers:{Cookie:config.cookie,Origin:config.base,'X-CSRF-Token':config.csrf,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
   const result=await response.json();assert.equal(response.status,200,JSON.stringify(result));return result;
 }
 const initial=config?await request('/state'):{boot_id:'boot',stop_epoch:'0',monotonic_us:'1000'};
 const context={request,initial,calls,assert,Uint8Array,crypto:{getRandomValues:a=>require('node:crypto').webcrypto.getRandomValues(a)}};
 const result=await vm.runInNewContext(`
 let jog=null,state=initial,pendingStop=null,releaseRefresh,refreshCount=0,timers=0;
 const $=()=>({value:'1'}),message=()=>{},invalidate=()=>{},clearInterval=()=>{};
 const setInterval=()=>{timers++;return 1;};
 async function refresh(){if(++refreshCount===1)await new Promise(resolve=>releaseRefresh=resolve);if(${!!config})state=await request('/state');}
 const api=request;
 ${id}
 ${functions}
 (async()=>{
   // No randomUUID is installed in this browser context; getRandomValues is enough.
   const ids=Array.from({length:100},commandId);assert.equal(new Set(ids).size,100);assert(ids.every(x=>/^[a-f0-9]{32}$/.test(x)));
   const start=beginJog({disabled:false,dataset:{axis:'x',sign:'1'}},{preventDefault(){}});
   await Promise.resolve();await endJog();releaseRefresh();await start;
   assert(!calls.includes('/jog/start'));assert.equal(timers,0);assert.equal(jog,null);
   return {passed:true,case:'release_before_state_response',calls,timers,uuid_over_http:true};
 })()`,context);
 console.log(JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
