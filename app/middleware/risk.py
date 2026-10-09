"""Authenticated heartbeat signals; failures never become benign defaults."""
import time
from datetime import datetime,timezone
from sqlalchemy import select,func
from app.database import AsyncSessionLocal
from app.models import AuditLog,User
from app.risk.engine import RiskUnavailable

async def assemble_signals(user_id,similarity,ip_tag,session):
 try:
  async with AsyncSessionLocal() as db:
   user=await db.get(User,user_id)
   if user is None:raise RiskUnavailable('Account missing')
   count=await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.user_id==user_id,AuditLog.timestamp>=time.time()-300))
   day=datetime.now(timezone.utc).date().isoformat()
   return {'face_similarity':similarity,'failed_attempts_today':user.failures if user.failure_day==day else 0,'actions_per_minute':float(count)/5.,'ip_changed':ip_tag!=session.ip_tag}
 except Exception:raise RiskUnavailable('Risk signal storage unavailable') from None
