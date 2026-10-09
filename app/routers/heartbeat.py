"""Fresh face sequence, deterministic risk floor and persisted enforcement."""
from fastapi import APIRouter,Depends,HTTPException,Request,Form,File,UploadFile
from app.auth.challenges import consume
from app.auth.jwt_service import decrypt_template,resolve
from app.auth.events import revoke,event
from app.database import transaction
from app.middleware.rbac import get_current_identity
from app.middleware.audit import peer_tag
from app.middleware.risk import assemble_signals
from app.cv.embeddings import is_match
from app.risk.engine import evaluate_risk,RiskUnavailable
from app.routers.login import sequence

router=APIRouter(tags=['monitoring'])
@router.post('/heartbeat')
async def heartbeat(request:Request,challenge_id:str=Form(),timestamps:str=Form(),frames:list[UploadFile]=File(),identity=Depends(get_current_identity)):
 user,session=identity;tag=peer_tag(request)
 kind=await consume(challenge_id,'heartbeat',user.username,tag,session.id)
 try:
  embedding=await sequence(request,frames,timestamps,kind)
  matched,similarity=is_match(embedding,decrypt_template(user.face_embedding))
  signals=await assemble_signals(user.id,similarity,tag,session)
  score,reason=await evaluate_risk(signals)
 except (ValueError,RiskUnavailable):
  await revoke(user.id,tag,'heartbeat_unavailable',session_id=session.id)
  raise HTTPException(503,'Verification unavailable; session revoked') from None
 except HTTPException:
  await revoke(user.id,tag,'heartbeat_denied',session_id=session.id);raise
 if not matched or score>=90:
  await revoke(user.id,tag,'critical_lockout',lock=True,score=score)
  raise HTTPException(403,'Account locked; administrator recovery required')
 if score>=70:
  await revoke(user.id,tag,'stepup',score=score)
  raise HTTPException(401,'Full authentication required')
 async with transaction() as db:
  if await resolve(db,request.state.access_token) is None:raise HTTPException(401,'Session revoked during verification')
  event(db,user.id,'heartbeat_ok',tag,score=score)
 return {'status':'verified','face_similarity':round(similarity,4),'risk_score':score,'reason':reason}
