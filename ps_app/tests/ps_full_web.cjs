const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const config=JSON.parse(process.env.PS_FULL_WEB_CONFIG),browser=await chromium.launch({headless:true,...(process.env.PS_TEST_BROWSER?{executablePath:process.env.PS_TEST_BROWSER}:{})});
 const observe=async()=>{const r=await fetch(config.base+'/api/v1/state',{headers:{Cookie:config.observer_cookie}});assert(r.ok);return r.json();};
try{const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(config.base+'/#token='+config.token);await page.locator('#workspace').waitFor({state:'visible'});
 // The HTTP test owns the control lease; deliberately release it before the UI claim.
 await page.locator('#claim').click();
 await page.locator('#current-source').filter({hasText:'encoder_0x30_calibrated_fk'}).waitFor();
 await page.locator('[data-tab="parameters"]').click();await page.waitForFunction(()=>document.querySelector('#parameter-json').value.includes('synthetic_calibration'));const edited=JSON.parse(JSON.stringify(config.parameters));edited.id='web_calibration_v2';
 await page.locator('#parameter-json').fill(JSON.stringify(edited,null,2));await page.locator('#save-parameters').click();await page.waitForFunction(()=>document.querySelector('#parameter-version').textContent==='web_calibration_v2');assert.equal((await observe()).position.valid,false);
 await page.waitForTimeout(350);await page.locator('#verify-calibration').click();await page.waitForFunction(()=>document.querySelector('#current-source').textContent.includes('encoder_0x30_calibrated_fk'));await page.locator('[data-tab="motion"]').click();
 await page.locator('#work-zero').click();await page.waitForFunction(()=>document.querySelector('#work-xyz').textContent==='0.000 / 0.000 / 0.000 mm');
 await page.locator('#points').fill('1, 0, 0\n0, 0, 0');await page.locator('#repeat-count').fill('2');await page.locator('#preview').click();await page.waitForFunction(()=>!document.querySelector('#execute').disabled);
 await page.locator('#execute').click();await page.waitForFunction(()=>document.querySelector('#command-status').textContent.includes('已完成'),{timeout:15000});
 await page.waitForFunction(()=>!document.querySelector('#teach').disabled);await page.locator('#teach').click();await page.waitForFunction(()=>document.querySelector('#points').value.split('\n').length>=3);
 await page.locator('#manual-mode').click();await page.locator('#jog-speed').fill('1');let button=page.locator('[data-axis="x"][data-sign="1"]');await button.hover();await page.mouse.down();await page.waitForTimeout(450);await page.mouse.up();await page.waitForFunction(()=>document.querySelector('#phase').textContent==='静止待操作');
 await page.waitForFunction(()=>!document.querySelector('#work-zero').disabled);const beforeZero=await observe();assert(beforeZero.position.machine_xyz_mm[0]>.01);
 await page.locator('#work-zero').click();await page.waitForFunction(()=>document.querySelector('#work-xyz').textContent==='0.000 / 0.000 / 0.000 mm');const afterZero=await observe();assert.deepEqual(afterZero.position.machine_xyz_mm,beforeZero.position.machine_xyz_mm);assert.deepEqual(afterZero.position.steps,beforeZero.position.steps);
 await page.locator('[data-tab="logs"]').click();await page.locator('#query-logs').click();await page.waitForFunction(()=>!document.querySelector('#download-logs').disabled);assert(await page.locator('#log-rows tr').count()>0);
 const download=page.waitForEvent('download');await page.locator('#download-logs').click();const saved=await download;assert(saved.suggestedFilename().endsWith('.jsonl'));const exported=require('node:fs').readFileSync(await saved.path(),'utf8').trim().split('\n').map(x=>JSON.parse(x));assert.equal(exported[0].record_type,'snapshot');assert(exported.slice(1).some(e=>e.event==='jog_stopping'&&e.command_id));
 // Recovery and explicit re-verification precede a fresh manual intent.
 await page.locator('#hardware-controls summary').click();await page.locator('[data-hardware="recover"]').click();await page.waitForTimeout(300);
 await page.locator('[data-tab="parameters"]').click();await page.locator('#verify-calibration').click();await page.waitForFunction(()=>document.querySelector('#current-source').textContent.includes('encoder_0x30_calibrated_fk'));
 await page.locator('[data-tab="motion"]').click();button=page.locator('[data-axis="x"][data-sign="1"]');await button.hover();await page.mouse.down();await page.waitForTimeout(250);
 await page.context().setOffline(true);await page.waitForTimeout(800);
 const stopped=await observe();console.log('OFFLINE_STOP_OBSERVATION',JSON.stringify({phase:stopped.phase,backend:stopped.backend,stop_epoch:stopped.stop_epoch}));assert.equal(stopped.phase,'idle');assert(BigInt(stopped.stop_epoch)>0n);
 await page.mouse.up();await page.context().setOffline(false);await page.waitForTimeout(400);assert.equal((await observe()).phase,'idle');
 assert.deepEqual(errors,[]);console.log('PASS browser dual coordinates, zero, repeat task, teach, real jog release, log query/download');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
