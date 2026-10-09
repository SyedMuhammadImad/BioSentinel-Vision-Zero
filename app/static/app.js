"use strict";
const $=id=>document.getElementById(id);
let stream=null,session=null,identity=null,busy=false,modelsReady=false,refreshing=null;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function nextVideoFrame(video){
 if(video.readyState<2)throw new Error('The camera has not produced an image yet. Try again shortly.');
 if(!video.requestVideoFrameCallback)return pause(40);
 await new Promise((resolve,reject)=>{
  // Browsers may suspend presentation callbacks when the preview scrolls offscreen.
  // Draw from the live stream after a bounded wait; the server rejects frozen sequences.
  let callback;const timeout=setTimeout(()=>{video.cancelVideoFrameCallback(callback);resolve();},40);
  callback=video.requestVideoFrameCallback(()=>{clearTimeout(timeout);resolve();});
 });
}
function message(text){$('message').textContent=text;$('message').hidden=!text;}
function controls(){
 document.querySelectorAll('button').forEach(button=>{button.disabled=busy;});
 document.querySelectorAll('[data-auth]').forEach(button=>{button.disabled=busy||!stream||!modelsReady;});
 $('stop-camera').disabled=busy||!stream;$('start-camera').disabled=busy||!!stream;
 $('signed-out').hidden=!!session;$('signed-in').hidden=!session;$('admin').hidden=!session||identity?.role!=='admin';
}
function forget(){session=null;identity=null;refreshing=null;$('identity').textContent='';$('risk-result').textContent='';$('accounts').replaceChildren();$('events').textContent='';controls();}
async function request(path,options={}){
 const response=await fetch(path,{cache:'no-store',credentials:'omit',...options});
 let data;try{data=await response.json();}catch{throw new Error('The server returned an unreadable response.');}
 if(!response.ok){const error=new Error(typeof data.detail==='string'?data.detail:'Request rejected. Check the supplied details.');error.status=response.status;throw error;}
 return data;
}
function json(body){return {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};}
function headers(){return {Authorization:'Bearer '+session.access_token};}
async function refresh(){
 if(refreshing)return refreshing;
 if(!session)throw new Error('Sign in first.');
 const previous=session.refresh_token;
 refreshing=request('/auth/refresh',json({refresh_token:previous})).then(pair=>{session={...pair,expires_at:Date.now()+pair.expires_in*1000};return session;}).catch(error=>{forget();throw error;}).finally(()=>{refreshing=null;});
 return refreshing;
}
async function ensure(){if(!session)throw new Error('Sign in first.');if(session.expires_at-Date.now()<30000)await refresh();}
async function startCamera(){
 if(!navigator.mediaDevices?.getUserMedia)throw new Error('Camera access requires localhost or HTTPS and a supported browser.');
 stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:320},height:{ideal:240}},audio:false});
 $('camera').srcObject=stream;await $('camera').play();controls();
}
function stopCamera(){if(stream)stream.getTracks().forEach(track=>track.stop());stream=null;$('camera').srcObject=null;controls();}
async function capture(purpose,username){
 if(!stream)throw new Error('Start the camera first.');
 if(purpose==='heartbeat')await ensure();
 const options=json({purpose,username});if(purpose==='heartbeat')options.headers={...options.headers,...headers()};
 const challenge=await request('/auth/challenge',options);
 $('challenge').textContent=challenge.instruction+' Capture starts shortly.';await pause(500);
 const canvas=document.createElement('canvas');canvas.width=320;canvas.height=240;const context=canvas.getContext('2d');
 const form=new FormData();const times=[];const start=performance.now();
 for(let i=0;i<24;i++){
  if(!stream||!stream.getVideoTracks().some(track=>track.readyState==='live'))throw new Error('Camera stopped during capture.');
  await nextVideoFrame($('camera'));
  context.drawImage($('camera'),0,0,canvas.width,canvas.height);
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.82));if(!blob)throw new Error('Camera frame could not be captured.');
  form.append('frames',blob,'frame-'+i+'.jpg');times.push(Math.round(performance.now()-start));
  $('challenge').textContent=challenge.instruction+' Capturing '+(i+1)+' of 24 frames…';if(i<23)await pause(100);
 }
 form.append('challenge_id',challenge.challenge_id);form.append('timestamps',JSON.stringify(times));$('challenge').textContent='Checking the captured sequence…';return form;
}
async function action(fn){if(busy)return;busy=true;message('');controls();try{await fn();}catch(error){message(error.message||'Unable to connect. Try again.');}finally{busy=false;controls();}}
$('start-camera').addEventListener('click',()=>action(startCamera));$('stop-camera').addEventListener('click',stopCamera);
$('enroll-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
 const username=$('enroll-name').value.trim().toLowerCase();const form=await capture('enroll',username);
 form.append('username',username);form.append('email',$('enroll-email').value);form.append('password',$('enroll-password').value);
 await request('/enroll/',{method:'POST',body:form});$('enroll-password').value='';$('login-name').value=username;$('challenge').textContent='Account created. Sign in with a new camera challenge.';
});});
$('login-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
 const username=$('login-name').value.trim().toLowerCase();const form=await capture('login',username);form.append('username',username);form.append('password',$('login-password').value);
 const pair=await request('/auth/login',{method:'POST',body:form});session={...pair,expires_at:Date.now()+pair.expires_in*1000};
 try{identity=await request('/auth/me',{headers:headers()});}catch(error){forget();throw error;}
 $('login-password').value='';$('identity').textContent='Signed in as '+identity.username+' ('+identity.role+').';$('challenge').textContent='Signed in. Verify your face again when needed.';
});});
$('heartbeat').addEventListener('click',()=>action(async()=>{
 const form=await capture('heartbeat',identity.username);
 try{const result=await request('/heartbeat',{method:'POST',headers:headers(),body:form});$('risk-result').textContent='Face verified. Risk score: '+result.risk_score+'. '+result.reason;$('challenge').textContent='Verification complete.';}
 catch(error){if([401,403,503].includes(error.status))forget();throw error;}
}));
$('refresh-session').addEventListener('click',()=>action(async()=>{await refresh();$('risk-result').textContent='Session refreshed; previous tokens are revoked.';}));
$('logout').addEventListener('click',()=>action(async()=>{
 try{await ensure();await request('/auth/logout',{method:'POST',headers:headers()});forget();$('challenge').textContent='Signed out. The server session is revoked.';}
 catch(error){if(error.status===401)forget();throw error;}
}));
$('load-admin').addEventListener('click',()=>action(async()=>{
 await ensure();const users=await request('/admin/users',{headers:headers()});const events=await request('/admin/events',{headers:headers()});$('accounts').replaceChildren();
 for(const user of users){const row=document.createElement('div');row.className='account';const text=document.createElement('p');text.textContent=user.username+' — '+(user.is_active?'active':'locked');row.append(text);
  if(!user.is_active){const button=document.createElement('button');button.textContent='Unblock '+user.username;button.addEventListener('click',()=>action(async()=>{await ensure();await request('/admin/unblock/'+user.id,{method:'POST',headers:headers()});row.remove();$('risk-result').textContent='Account unblocked; its old sessions remain revoked.';}));row.append(button);} $('accounts').append(row);
 }
 $('events').textContent=JSON.stringify(events,null,2);
}));
window.addEventListener('pagehide',()=>{if(stream)stream.getTracks().forEach(track=>track.stop());});
request('/health').then(result=>{modelsReady=result.vision_ready;$('service').textContent='Local vision models ready. Risk mode: '+result.risk_mode+'.';controls();}).catch(()=>{modelsReady=false;$('service').textContent='Authentication unavailable: local model setup needs attention. See the setup guide.';controls();});
controls();
