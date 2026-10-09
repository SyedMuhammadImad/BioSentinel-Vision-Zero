"""Enrollment binds validated account fields to a fresh verified frame sequence."""
from fastapi import APIRouter,HTTPException,Request,Form,File,UploadFile
from email_validator import validate_email,EmailNotValidError
from sqlalchemy import select,or_
from sqlalchemy.exc import IntegrityError
from app.models import User
from app.database import transaction
from app.auth.jwt_service import valid_password,hash_password,encrypt_template
from app.auth.challenges import consume
from app.auth.events import event
from app.middleware.audit import peer_tag
from app.routers.login import clean_username,sequence,user_out
from app.schemas import UserOut

router=APIRouter(prefix='/enroll',tags=['enrollment'])
@router.post('/',response_model=UserOut,status_code=201)
async def enroll(request:Request,username_value:str=Form(alias='username'),email:str=Form(),password:str=Form(),challenge_id:str=Form(),timestamps:str=Form(),frames:list[UploadFile]=File()):
 name=clean_username(username_value);tag=peer_tag(request)
 try:
  valid_password(password)
  if len(email)>254:raise ValueError
  address=validate_email(email,check_deliverability=False).normalized.lower()
 except (ValueError,EmailNotValidError):raise HTTPException(400,'Use a valid email address and an 8–72 byte password') from None
 kind=await consume(challenge_id,'enroll',name,tag)
 embedding=await sequence(request,frames,timestamps,kind)
 hashed=hash_password(password);encrypted=encrypt_template(embedding)
 try:
  async with transaction() as db:
   if await db.scalar(select(User.id).where(or_(User.username==name,User.email==address))):raise HTTPException(409,'Account details already registered')
   user=User(username=name,email=address,hashed_password=hashed,face_embedding=encrypted,role='user',is_active=True)
   db.add(user);await db.flush();event(db,user.id,'enrolled',tag);result=user_out(user)
 except IntegrityError:raise HTTPException(409,'Account details already registered') from None
 return result
