"""Security events and lockout persist atomically, including denied requests."""
import time
from datetime import datetime,timezone
from sqlalchemy import update
from app.database import transaction
from app.models import User,Session,AuditLog
from app.config import settings

def event(db,user_id,action,ip_tag=None,actor_id=None,score=None):
 db.add(AuditLog(user_id=user_id,action=action,ip_tag=ip_tag,actor_id=actor_id,risk_score=score))

async def failure(user_id,ip_tag):
 async with transaction() as db:
  user=await db.get(User,user_id)
  if user is None:return
  day=datetime.now(timezone.utc).date().isoformat()
  if user.failure_day!=day:user.failure_day=day;user.failures=0
  user.failures+=1;event(db,user.id,'login_failed',ip_tag)
  if user.failures>=settings.max_failures:
   user.is_active=False
   await db.execute(update(Session).where(Session.user_id==user.id).values(is_revoked=True))
   event(db,user.id,'failure_lockout',ip_tag)

async def revoke(user_id,ip_tag,action='stepup',lock=False,score=None,session_id=None):
 async with transaction() as db:
  user=await db.get(User,user_id)
  if user is None:return
  if lock:user.is_active=False
  query=update(Session).where(Session.user_id==user_id)
  if session_id is not None:query=query.where(Session.id==session_id)
  await db.execute(query.values(is_revoked=True));event(db,user_id,action,ip_tag,score=score)
