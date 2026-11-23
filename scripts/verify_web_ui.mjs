import {chromium} from 'playwright';
import {mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
const out='.cache/day07-browser';await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8001');
await page.locator('#upload-panel').waitFor();
await page.screenshot({path:out+'/desktop.png',fullPage:true});
assert.equal(await page.locator('#submit').innerText(),'Analyze meeting ↗');
await page.setViewportSize({width:390,height:844});
await page.screenshot({path:out+'/mobile.png',fullPage:true});
assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
// Explicitly mocked UI fixtures test every section and hostile transcript rendering.
const id='a'.repeat(32),e={start:1,end:2,segment_id:'s1',speaker_id:'SPEAKER_00',quote:'Use JSON.'};
const state={id,name:'UI test fixture',status:'completed',stage:'Ready',error:null,result:{
 summary:{meeting_summary:'Summary fixture',summary_statements:[{evidence:[e]}],key_discussion_points:[],warnings:[]},
 transcript:{segments:[{start:1,end:2,speaker_id:'SPEAKER_00',text:'<img src=x onerror=alert(1)>'}],warnings:[]},
 actions:{action_items:[{task:'Prepare report',assignment_type:'assignment',owner:{mention:'Alice',evidence:[e]},deadline:{text:'Friday'},evidence:[e]}],pending_questions:[],warnings:[]},
 decisions:{topics:[{topic:'Export format',status:'agreed',final_agreed_decision:'Use JSON',events:[{type:'agreed',statement:'Use JSON',evidence:[e]}],unresolved_event_ids:[]}],warnings:[]}}};
state.result.actions.action_items[0].deadline.evidence=[];
await page.route('**/api/meetings',r=>r.fulfill({json:[state]}));
await page.route(`**/api/meetings/${id}`,r=>r.fulfill({json:state}));
await page.route(`**/api/meetings/${id}/questions`,r=>r.fulfill({json:{answer:'Use JSON.',limitation:null,claims:[{evidence:[e]}]}}));
await page.reload();await page.getByRole('button',{name:'UI test fixture',exact:true}).click();
for(const tab of ['actions','decisions','transcript','summary']){await page.locator(`[data-tab="${tab}"]`).click();assert.ok((await page.locator('#content').innerText()).length>0);}
await page.locator('[data-tab="transcript"]').click();assert.equal(await page.locator('#content img').count(),0);
await page.locator('[data-tab="qa"]').click();await page.locator('#question').fill('What was agreed?');await page.locator('#ask').click();await page.getByText('Use JSON.',{exact:true}).first().waitFor();
await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:out+'/qa-fixture.png',fullPage:true});
assert.deepEqual(errors,[]);await browser.close();console.log('Passed: desktop/mobile layout, all five sections, QA rendering, escaped transcript content; section/QA data explicitly mocked.');
