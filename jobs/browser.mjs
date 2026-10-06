import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const [stock,root,linux]=process.argv.slice(2),out=path.join(root,'artifacts/result');
const require=createRequire(path.join(stock,'package/package.json'));
process.on('uncaughtException',()=>{console.error('Browser gate import failure');process.exit(1)});
process.on('unhandledRejection',()=>{console.error('Browser gate controlled failure');process.exit(1)});
const {chromium}=require('playwright-core');
const fixture=spawn('wsl.exe',['-e','bash',linux+'/jobs/browser-fixture.sh',linux],{stdio:['pipe','pipe','pipe']});
let stdout='',stderr='';fixture.stdout.on('data',b=>stdout+=b);fixture.stderr.on('data',b=>stderr+=b);
async function until(check,timeout=15000){let start=Date.now();while(!check()){if(Date.now()-start>timeout)throw Error('Fixture readiness failed: '+stderr);await new Promise(r=>setTimeout(r,50));}}
let browser,stage='readiness';
try{
 await until(()=>stdout.includes('\n'));
 const ready=JSON.parse(stdout.trim());stdout='';
 stage='browser launch';
 const url='http://127.0.0.1:'+ready.port;
 browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:800}}),page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 stage='anonymous request';assert.equal((await context.request.get(url+'/api/owner-state')).status(),401);
 stage='login';await page.goto(url);await page.evaluate(value=>{document.querySelector('#token').value=value},ready.token);await page.locator('#login button').click();
 await page.locator('#workspace').waitFor({state:'visible'});
 await page.waitForFunction(()=>document.querySelector('#summary').textContent.includes('revision current'));
 async function command(action){const marker='DONE '+action;stdout='';fixture.stdin.write(action+'\n');await until(()=>stdout.includes(marker));}
 stage='automatic freshness';const start=Date.now();await command('checkpoint');
 await page.waitForFunction(()=>document.querySelector('#projects').textContent.includes('Browser automatic revision 2'),null,{timeout:5000});
 const elapsedMs=Date.now()-start;assert(elapsedMs<=5000);
 stage='crash stale';await command('crash');await page.waitForFunction(()=>document.querySelector('#summary').textContent.includes('STALE'),null,{timeout:5000});
 await command('reconcile');await page.waitForFunction(()=>document.querySelector('#projects').textContent.includes('Browser automatic revision 3')&&document.querySelector('#summary').textContent.includes('revision current'),null,{timeout:5000});
 stage='corrupt stale';await command('corrupt');await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Freshness unavailable')&&document.querySelector('#summary').textContent.includes('STALE'),null,{timeout:5000});
 await command('reconcile');await page.waitForFunction(()=>document.querySelector('#summary').textContent.includes('revision current'),null,{timeout:5000});
 stage='task history';await command('history');await page.waitForFunction(()=>document.querySelector('.task-ledger').textContent.includes('accepted'),null,{timeout:5000});const ledger=page.locator('.task-ledger');const history=await ledger.textContent();for(const value of ['three-lines','Authorization','attempt-1','attempt-2','Owner requests revision','accepted','evidence','Fixture counts three lines','<img src=x onerror=alert(1)>'])assert(history.includes(value));assert.equal(await ledger.locator('img').count(),0);await ledger.locator('summary').first().click();await ledger.locator('details summary').first().click();await page.waitForTimeout(2200);assert(await ledger.locator('pre').first().isVisible());await page.screenshot({path:path.join(out,'browser-authenticated.png')});
 stage='logout';await page.locator('#logout').click();await page.locator('#login').waitFor({state:'visible'});assert.equal(await page.locator('#projects').textContent(),'');
 assert.equal((await context.request.get(url+'/api/owner-state')).status(),401);
 assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'browser-proof.json'),JSON.stringify({engine:'Microsoft Edge Chromium',elapsedMs,taskHistoryVisible:true,untrustedTextEscaped:true,authenticated:true,anonymousDenied:true,logoutRevoked:true,crashStaleObserved:true,reconcileObserved:true,corruptionStaleObserved:true,pageErrors:errors,modelChannelProof:false},null,2));
}catch(e){fs.writeFileSync(path.join(out,'browser-failure.json'),JSON.stringify({stage,errorClass:e.name,diagnostic:['browser launch','anonymous request'].includes(stage)?String(e.message).replace(/[A-Za-z0-9_-]{32,}/g,'[redacted]').slice(0,1200):'suppressed after login'}));console.error('Browser gate failed at '+stage);process.exitCode=1;}finally{if(browser)await browser.close();fixture.stdin.write('quit\n');fixture.stdin.end();await new Promise(r=>{fixture.on('exit',r);setTimeout(()=>{fixture.kill();r();},5000)});fs.rmSync(path.join(out,'browser-ready.json'),{force:true});}
