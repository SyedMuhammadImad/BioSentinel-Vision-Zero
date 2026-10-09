"""Persistent single-use challenges bound to purpose, account, IP and session."""
import secrets,time
from sqlalchemy import select,func,delete
from fastapi import HTTPException
from app.database import transaction
from app.models import Challenge
from app.config import settings
from app.auth.jwt_service import digest
from app.cv.liveness import INSTRUCTIONS

async def issue(purpose,subject,ip_tag,session_id=None):
 nonce=secrets.token_urlsafe(32);now=time.time();kind=secrets.choice(tuple(INSTRUCTIONS))
 async with transaction() as db:
  await db.execute(delete(Challenge).where(Challenge.expires_at<now-3600))
  count=await db.scalar(select(func.count()).select_from(Challenge).where(Challenge.ip_tag==ip_tag,Challenge.created_at>now-60))
  if count>=20:raise HTTPException(429,'Too many challenges; wait a minute')
  db.add(Challenge(id=digest(nonce),purpose=purpose,subject=subject,session_id=session_id,kind=kind,ip_tag=ip_tag,created_at=now,expires_at=now+settings.challenge_seconds,used=False))
 return {'challenge_id':nonce,'challenge_type':kind,'instruction':INSTRUCTIONS[kind],'expires_in':settings.challenge_seconds}

async def consume(nonce,purpose,subject,ip_tag,session_id=None):
 if not isinstance(nonce,str) or not 32<=len(nonce)<=128:raise HTTPException(401,'Invalid or expired challenge')
 accepted=False;kind=None
 async with transaction() as db:
  challenge=await db.get(Challenge,digest(nonce))
  if challenge is not None and not challenge.used and challenge.expires_at>time.time() and challenge.purpose==purpose and challenge.subject==subject and challenge.ip_tag==ip_tag and challenge.session_id==session_id:
   challenge.used=True;kind=challenge.kind;accepted=True
 if not accepted:raise HTTPException(401,'Invalid, consumed or expired challenge')
 return kind
