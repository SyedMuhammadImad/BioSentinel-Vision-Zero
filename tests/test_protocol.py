import asyncio,json,secrets,time
import pytest
from sqlalchemy import select,func,text
from app.database import AsyncSessionLocal,transaction,engine
from app.models import User,Session,Challenge,AuditLog
from app.auth.jwt_service import decrypt_template,decode_token,digest,encode
from tests.support import frames,timing

async def issue(client,purpose,name='tester',pair=None):
 headers={'Authorization':'Bearer '+pair['access_token']} if pair else {}
 result=await client.post('/auth/challenge',json={'purpose':purpose,'username':name},headers=headers)
 assert result.status_code==200,result.text
 return result.json()['challenge_id']

async def enroll(client,name='tester',password=None,email=None):
 password=password or secrets.token_urlsafe(20);nonce=await issue(client,'enroll',name)
 result=await client.post('/enroll/',data={'username':name,'email':email or name+'@example.com','password':password,'challenge_id':nonce,'timestamps':timing()},files=frames())
 assert result.status_code==201,result.text
 return result.json(),password

async def login(client,password,name='tester'):
 nonce=await issue(client,'login',name)
 result=await client.post('/auth/login',data={'username':name,'password':password,'challenge_id':nonce,'timestamps':timing()},files=frames())
 return result

def bearer(pair):return {'Authorization':'Bearer '+pair['access_token']}

@pytest.mark.asyncio
async def test_enroll_login_encrypted_digest_storage_logout(environment):
 client,vision,_=environment;user,password=await enroll(client)
 result=await login(client,password);assert result.status_code==200;pair=result.json()
 assert (await client.get('/auth/me',headers=bearer(pair))).json()['username']=='tester'
 async with AsyncSessionLocal() as db:
  row=await db.get(User,user['id']);session=(await db.execute(select(Session))).scalar_one()
  assert password not in row.hashed_password and row.hashed_password.startswith('$2b$')
  assert row.face_embedding.startswith('gAAAA') and '[' not in row.face_embedding
  assert decrypt_template(row.face_embedding).shape==(128,)
  assert session.access_digest==digest(pair['access_token']) and session.refresh_digest==digest(pair['refresh_token'])
 assert (await client.post('/auth/logout',headers=bearer(pair))).status_code==200
 assert (await client.get('/auth/me',headers=bearer(pair))).status_code==401
 assert (await client.post('/auth/refresh',json={'refresh_token':pair['refresh_token']})).status_code==401

@pytest.mark.asyncio
async def test_refresh_not_access_rotation_and_reuse(environment):
 client,_,_=environment;_,password=await enroll(client);pair=(await login(client,password)).json()
 assert (await client.get('/auth/me',headers={'Authorization':'Bearer '+pair['refresh_token']})).status_code==401
 assert (await client.post('/auth/refresh',json={'refresh_token':pair['access_token']})).status_code==401
 result=await client.post('/auth/refresh',json={'refresh_token':pair['refresh_token']});assert result.status_code==200;new=result.json()
 assert new['access_token']!=pair['access_token']
 assert (await client.get('/auth/me',headers=bearer(pair))).status_code==401
 assert (await client.get('/auth/me',headers=bearer(new))).status_code==200
 assert (await client.post('/auth/refresh',json={'refresh_token':pair['refresh_token']})).status_code==401
 assert (await client.get('/auth/me',headers=bearer(new))).status_code==401

@pytest.mark.asyncio
async def test_forged_missing_expired_and_unpersisted_tokens(environment):
 client,_,_=environment;user,password=await enroll(client);pair=(await login(client,password)).json()
 original=pair['access_token'];tampered=original[:-2]+('ab' if original[-2:]!='ab' else 'cd')
 claims=decode_token(original)
 invalid=[tampered,encode(user['id'],claims['sid'],'access',-1),encode(user['id'],__import__('uuid').uuid4().__str__(),'access',900)]
 import jwt
 from app.config import settings
 for key,value in [('type','refresh'),('sub','bogus'),('aud','other'),('iss','other'),('sid','bad'),('exp',True),('iat',int(time.time())+60)]:
  payload={**claims,key:value};invalid.append(jwt.encode(payload,settings.secret_key,algorithm='HS256'))
 invalid.append(jwt.encode({key:value for key,value in claims.items() if key!='exp'},settings.secret_key,algorithm='HS256'))
 invalid.append(jwt.encode(claims,secrets.token_urlsafe(48),algorithm='HS256'))
 for token in invalid:assert (await client.get('/auth/me',headers={'Authorization':'Bearer '+token})).status_code==401
 assert (await client.get('/auth/me')).status_code==401

@pytest.mark.asyncio
async def test_challenge_binding_consumption_expiry_and_concurrent_reuse(environment):
 client,_,_=environment;nonce=await issue(client,'enroll')
 async with AsyncSessionLocal() as db:challenge=await db.get(Challenge,digest(nonce));assert challenge.id!=nonce
 from app.auth.challenges import consume
 from app.auth.jwt_service import client_tag
 from fastapi import HTTPException
 for purpose,name,ip in [('login','tester','127.0.0.1'),('enroll','other','127.0.0.1'),('enroll','tester','other')]:
  with pytest.raises(HTTPException):await consume(nonce,purpose,name,client_tag(ip))
 outcomes=await asyncio.gather(consume(nonce,'enroll','tester',client_tag('127.0.0.1')),consume(nonce,'enroll','tester',client_tag('127.0.0.1')),return_exceptions=True)
 assert sum(isinstance(x,str) for x in outcomes)==1 and sum(isinstance(x,HTTPException) for x in outcomes)==1
 expired=await issue(client,'enroll')
 async with transaction() as db:(await db.get(Challenge,digest(expired))).expires_at=time.time()-1
 with pytest.raises(HTTPException):await consume(expired,'enroll','tester',client_tag('127.0.0.1'))

@pytest.mark.asyncio
async def test_atomic_failed_attempt_lockout_and_recovery(environment):
 client,_,_=environment;user,password=await enroll(client);pair=(await login(client,password)).json()
 from app.auth.events import failure
 from app.auth.jwt_service import client_tag
 await asyncio.gather(*(failure(user['id'],client_tag('127.0.0.1')) for _ in range(3)))
 async with AsyncSessionLocal() as db:
  stored=await db.get(User,user['id']);assert stored.failures==3 and stored.is_active is False
  assert await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action=='login_failed'))==3
 assert (await client.get('/auth/me',headers=bearer(pair))).status_code==401
 assert (await login(client,password)).status_code==401
 admin,admin_password=await enroll(client,'operator')
 async with transaction() as db:(await db.get(User,admin['id'])).role='admin'
 admin_pair=(await login(client,admin_password,'operator')).json()
 assert (await client.post('/admin/unblock/'+str(user['id']),headers=bearer(admin_pair))).status_code==200
 assert (await client.get('/auth/me',headers=bearer(pair))).status_code==401
 assert (await login(client,password)).status_code==200
 events=(await client.get('/admin/events',headers=bearer(admin_pair))).json();assert any(e['action']=='admin_unblock' and e['actor_id']==admin['id'] for e in events)

@pytest.mark.asyncio
async def test_admin_role_from_db_and_generic_denials(environment):
 client,_,_=environment;user,password=await enroll(client);pair=(await login(client,password)).json()
 for path in ['/admin/users','/admin/events']:assert (await client.get(path,headers=bearer(pair))).status_code==403
 assert (await client.post('/admin/unblock/999',headers=bearer(pair))).status_code==403
 wrong=await login(client,secrets.token_urlsafe(20));assert wrong.status_code==401
 unknown=await login(client,secrets.token_urlsafe(20),'unknown');assert unknown.status_code==401
 assert wrong.json()==unknown.json()
 async with transaction() as db:(await db.get(User,user['id'])).role='admin'
 assert (await client.get('/admin/users',headers=bearer(pair))).status_code==200

@pytest.mark.asyncio
async def test_nonce_replay_and_static_image_never_login(environment):
 client,vision,_=environment;_,password=await enroll(client);vision.mode='static'
 nonce=await issue(client,'login');payload={'username':'tester','password':password,'challenge_id':nonce,'timestamps':timing()}
 assert (await client.post('/auth/login',data=payload,files=frames())).status_code==401
 vision.mode='normal'
 assert (await client.post('/auth/login',data=payload,files=frames())).status_code==401
 assert (await login(client,password)).status_code==200

@pytest.mark.asyncio
async def test_heartbeat_success_session_binding_and_mismatch_lockout(environment):
 client,vision,_=environment;user,password=await enroll(client);pair=(await login(client,password)).json()
 nonce=await issue(client,'heartbeat',pair=pair)
 response=await client.post('/heartbeat',headers=bearer(pair),data={'challenge_id':nonce,'timestamps':timing()},files=frames());assert response.status_code==200 and response.json()['risk_score']==0
 other=(await login(client,password)).json();nonce=await issue(client,'heartbeat',pair=pair)
 assert (await client.post('/heartbeat',headers=bearer(other),data={'challenge_id':nonce,'timestamps':timing()},files=frames())).status_code==401
 vision.identity=1;nonce=await issue(client,'heartbeat',pair=pair)
 assert (await client.post('/heartbeat',headers=bearer(pair),data={'challenge_id':nonce,'timestamps':timing()},files=frames())).status_code==403
 assert (await client.get('/auth/me',headers=bearer(other))).status_code==401

@pytest.mark.asyncio
async def test_provider_and_risk_outages_fail_closed(environment,monkeypatch):
 client,vision,_=environment;_,password=await enroll(client);vision.mode='unavailable'
 assert (await login(client,password)).status_code==503
 vision.mode='normal';vision.index=0
 recovered=await login(client,password);assert recovered.status_code==200,recovered.text
 pair=recovered.json()
 from app.risk.engine import RiskUnavailable
 async def unavailable(signals):raise RiskUnavailable('Synthetic outage')
 monkeypatch.setattr('app.routers.heartbeat.evaluate_risk',unavailable)
 nonce=await issue(client,'heartbeat',pair=pair)
 assert (await client.post('/heartbeat',headers=bearer(pair),data={'challenge_id':nonce,'timestamps':timing()},files=frames())).status_code==503
 assert (await client.get('/auth/me',headers=bearer(pair))).status_code==401

@pytest.mark.asyncio
async def test_database_failure_does_not_issue_or_accept_tokens(environment):
 client,_,_=environment;_,password=await enroll(client);pair=(await login(client,password)).json()
 async with engine.begin() as connection:await connection.execute(text('DROP TABLE events_v2'))
 assert (await login(client,password)).status_code==503
 async with engine.begin() as connection:await connection.execute(text('DROP TABLE sessions_v2'))
 assert (await client.get('/auth/me',headers=bearer(pair))).status_code==503

@pytest.mark.asyncio
async def test_request_and_upload_bounds_and_missing_models(environment):
 client,vision,_=environment
 response=await client.post('/auth/challenge',content=b'{}',headers={'Content-Type':'application/json','Content-Length':'9000000'});assert response.status_code==413
 nonce=await issue(client,'enroll');bad=frames();bad[0]=('frames',('bad.png',b'not an image','image/png'))
 response=await client.post('/enroll/',data={'username':'tester','email':'tester@example.com','password':secrets.token_urlsafe(20),'challenge_id':nonce,'timestamps':timing()},files=bad);assert response.status_code==400
 vision.ready=False;assert (await client.get('/health')).status_code==503
 assert (await client.post('/auth/challenge',json={'purpose':'login','username':'tester'})).status_code==503

@pytest.mark.asyncio
async def test_challenge_rate_limit_and_response_headers(environment):
 client,_,_=environment
 for _ in range(20):await issue(client,'enroll')
 assert (await client.post('/auth/challenge',json={'purpose':'enroll','username':'tester'})).status_code==429
 response=await client.get('/');assert response.status_code==200
 assert response.headers['cache-control']=='no-store' and "script-src 'self'" in response.headers['content-security-policy']
 assert response.headers['x-content-type-options']=='nosniff'

@pytest.mark.asyncio
async def test_duplicate_account_rejected_even_when_inactive(environment):
 client,_,_=environment;user,password=await enroll(client)
 async with transaction() as db:(await db.get(User,user['id'])).is_active=False
 nonce=await issue(client,'enroll')
 result=await client.post('/enroll/',data={'username':'tester','email':'other@example.com','password':password,'challenge_id':nonce,'timestamps':timing()},files=frames());assert result.status_code==409
