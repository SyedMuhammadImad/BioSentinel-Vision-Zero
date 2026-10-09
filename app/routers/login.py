"""Full-factor login, refresh rotation and revocation; no raw tokens are stored."""
import secrets,time
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException,Request,Form,File,UploadFile
from sqlalchemy import select,update
from app.database import transaction,AsyncSessionLocal
from app.models import Session,User
from app.auth.jwt_service import hash_password,verify_password,valid_password,username,get_user_by_username,save_session,resolve,digest,decode_token
from app.auth.challenges import issue,consume
from app.auth.events import event,failure
from app.middleware.audit import peer_tag
from app.middleware.rbac import get_current_identity
from app.config import settings
from app.schemas import ChallengeRequest,RefreshRequest,TokenResponse,UserOut

router=APIRouter(prefix='/auth',tags=['authentication'])
_dummy_hash=hash_password(secrets.token_urlsafe(24))
def user_out(user):return {'id':user.id,'username':user.username,'email':user.email,'role':user.role,'is_active':user.is_active}
def tokens(pair):return {'access_token':pair[0],'refresh_token':pair[1],'token_type':'bearer','expires_in':settings.access_seconds}
def clean_username(value):
 try:return username(value)
 except ValueError:raise HTTPException(400,'Invalid username') from None

@router.post('/challenge')
async def challenge(request:Request,body:ChallengeRequest):
 subject=clean_username(body.username);session_id=None
 if not request.app.state.vision.ready:raise HTTPException(503,'Local vision models are not ready')
 if body.purpose=='heartbeat':
  header=request.headers.get('authorization','')
  if not header.lower().startswith('bearer '):raise HTTPException(401,'Authentication required')
  async with AsyncSessionLocal() as db:identity=await resolve(db,header[7:])
  if identity is None or identity[0].username!=subject:raise HTTPException(401,'Invalid session')
  session_id=identity[1].id
 return await issue(body.purpose,subject,peer_tag(request),session_id)

async def sequence(request,files,timestamps,kind):
 from app.cv.uploads import read_sequence
 from app.cv.provider import ProviderUnavailable,RejectedFace
 from app.cv.liveness import verify_sequence
 from starlette.concurrency import run_in_threadpool
 import asyncio
 frames,times=await read_sequence(files,timestamps)
 try:await asyncio.wait_for(request.app.state.vision_slot.acquire(),timeout=.1)
 except TimeoutError:raise HTTPException(429,'Vision processing is busy; request a new challenge') from None
 def analyze():return verify_sequence([request.app.state.vision.observe(frame) for frame in frames],kind,times)
 try:return await run_in_threadpool(analyze)
 except ProviderUnavailable:raise HTTPException(503,'Local vision processing unavailable') from None
 except (ValueError,RejectedFace):raise HTTPException(401,'Challenge verification failed; request a new challenge and follow the action') from None
 finally:request.app.state.vision_slot.release()

@router.post('/login',response_model=TokenResponse)
async def login(request:Request,username_value:str=Form(alias='username'),password:str=Form(),challenge_id:str=Form(),timestamps:str=Form(),frames:list[UploadFile]=File()):
 name=clean_username(username_value);tag=peer_tag(request)
 kind=await consume(challenge_id,'login',name,tag)
 # Password failure records must commit even though the request will be denied.
 async with AsyncSessionLocal() as db:user=await get_user_by_username(db,name)
 valid=verify_password(password,user.hashed_password if user else _dummy_hash)
 if user is None or not user.is_active or not valid:
  if user is not None and user.is_active:await failure(user.id,tag)
  raise HTTPException(401,'Authentication failed')
 try:embedding=await sequence(request,frames,timestamps,kind)
 except HTTPException as error:
  if error.status_code in (400,401,413):await failure(user.id,tag)
  raise
 from app.auth.jwt_service import decrypt_template
 from app.cv.embeddings import is_match
 try:matched,_=is_match(embedding,decrypt_template(user.face_embedding))
 except ValueError:raise HTTPException(503,'Enrollment template unavailable') from None
 if not matched:await failure(user.id,tag);raise HTTPException(401,'Authentication failed')
 async with transaction() as db:
  current=await db.get(User,user.id)
  if current is None or not current.is_active:raise HTTPException(401,'Authentication failed')
  pair=await save_session(db,current.id,tag);current.failures=0;current.failure_day=datetime.now(timezone.utc).date().isoformat();event(db,current.id,'login_success',tag)
 return tokens(pair)

@router.post('/refresh',response_model=TokenResponse)
async def refresh(request:Request,body:RefreshRequest):
 tag=peer_tag(request);pair=None;accepted=False
 async with transaction() as db:
  identity=await resolve(db,body.refresh_token,'refresh')
  if identity is not None:
   user,session=identity;session.is_revoked=True
   pair=await save_session(db,user.id,tag,session.family_id);event(db,user.id,'refresh_rotated',tag);accepted=True
  else:
   # A genuine replay of a consumed refresh revokes its successor family.
   claims=decode_token(body.refresh_token,'refresh')
   previous=await db.get(Session,claims['sid']) if claims else None
   if previous is not None and previous.is_revoked and previous.refresh_expires_at>time.time() and previous.refresh_digest==digest(body.refresh_token):
    await db.execute(update(Session).where(Session.family_id==previous.family_id).values(is_revoked=True));event(db,previous.user_id,'refresh_reuse',tag)
 if not accepted:raise HTTPException(401,'Invalid or consumed refresh session')
 return tokens(pair)

@router.post('/logout')
async def logout(request:Request,identity=Depends(get_current_identity)):
 async with transaction() as db:
  current=await resolve(db,request.state.access_token)
  if current is None:raise HTTPException(401,'Invalid session')
  current[1].is_revoked=True;event(db,current[0].id,'logout',peer_tag(request))
 return {'status':'signed_out'}

@router.get('/me',response_model=UserOut)
async def me(identity=Depends(get_current_identity)):return user_out(identity[0])
