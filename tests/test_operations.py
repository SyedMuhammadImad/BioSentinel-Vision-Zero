"""Storage-backed races, operational provisioning and transport boundaries."""
import asyncio,time,secrets
import pytest
from sqlalchemy import select
from app.database import transaction,AsyncSessionLocal
from app.models import User,Session,AuditLog
from app.auth.jwt_service import resolve,digest
from tests.test_protocol import enroll,login,issue,bearer

@pytest.mark.asyncio
async def test_expired_database_session_and_refresh_race(environment):
 client,_,_=environment;_,password=await enroll(client);pair=(await login(client,password)).json()
 async with transaction() as db:
  session=(await db.execute(select(Session).where(Session.access_digest==digest(pair['access_token'])))).scalar_one();session.expires_at=time.time()-1
 assert (await client.get('/auth/me',headers=bearer(pair))).status_code==401
 responses=await asyncio.gather(*[client.post('/auth/refresh',json={'refresh_token':pair['refresh_token']}) for _ in range(2)])
 assert sorted(r.status_code for r in responses)==[200,401]
 next_pair=next(r.json() for r in responses if r.status_code==200)
 assert (await client.get('/auth/me',headers=bearer(next_pair))).status_code==401

@pytest.mark.asyncio
async def test_offline_admin_provisioning_audited_and_revokes(environment):
 from app.manage import grant
 client,_,_=environment;user,password=await enroll(client);pair=(await login(client,password)).json()
 await grant('tester')
 assert (await client.get('/auth/me',headers=bearer(pair))).status_code==401
 async with AsyncSessionLocal() as db:
  assert (await db.get(User,user['id'])).role=='admin'
  assert (await db.execute(select(AuditLog).where(AuditLog.action=='offline_admin_granted'))).scalar_one().actor_id==user['id']
 with pytest.raises(ValueError):await grant('missinguser')
 async with transaction() as db:(await db.get(User,user['id'])).is_active=False
 with pytest.raises(ValueError):await grant('tester')

@pytest.mark.asyncio
async def test_untrusted_forwarded_headers_do_not_change_peer(environment):
 from app.middleware.audit import peer_tag
 from starlette.requests import Request
 def tag(headers):return peer_tag(Request({'type':'http','client':('127.0.0.1',1234),'headers':headers}))
 assert tag([])==tag([(b'x-forwarded-for',b'203.0.113.1'),(b'forwarded',b'for=203.0.113.2')])

@pytest.mark.asyncio
async def test_streaming_body_cap_without_content_length(environment):
 client,_,_=environment
 async def chunks():
  for _ in range(10):yield b'x'*1_000_000
 result=await client.post('/auth/challenge',content=chunks(),headers={'Content-Type':'application/json'})
 assert result.status_code==413,result.text
 assert result.headers['cache-control']=='no-store'
