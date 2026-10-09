"""Administrator-only recovery and audit summaries without biometric/token data."""
from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy import select,update
from app.models import User,Session,AuditLog
from app.database import transaction,AsyncSessionLocal
from app.auth.events import event
from app.auth.jwt_service import resolve
from app.middleware.rbac import require_role
from app.middleware.audit import peer_tag
from app.routers.login import user_out
router=APIRouter(prefix='/admin',tags=['administration'])

@router.post('/unblock/{user_id}')
async def unblock(user_id:int,request:Request,identity=Depends(require_role('admin'))):
 async with transaction() as db:
  current=await resolve(db,request.state.access_token)
  if current is None or current[0].role!='admin':raise HTTPException(403,'Administrator access required')
  user=await db.get(User,user_id)
  if user is None:raise HTTPException(404,'Account not found')
  user.is_active=True;user.failures=0
  await db.execute(update(Session).where(Session.user_id==user_id).values(is_revoked=True))
  event(db,user_id,'admin_unblock',peer_tag(request),actor_id=current[0].id)
 return {'status':'unblocked','user_id':user_id}

@router.get('/users')
async def users(identity=Depends(require_role('admin'))):
 async with AsyncSessionLocal() as db:rows=(await db.execute(select(User).order_by(User.id).limit(100))).scalars().all()
 return [user_out(user) for user in rows]

@router.get('/events')
async def events(identity=Depends(require_role('admin'))):
 async with AsyncSessionLocal() as db:rows=(await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(100))).scalars().all()
 return [{'id':row.id,'user_id':row.user_id,'actor_id':row.actor_id,'action':row.action,'risk_score':row.risk_score,'timestamp':row.timestamp} for row in rows]
