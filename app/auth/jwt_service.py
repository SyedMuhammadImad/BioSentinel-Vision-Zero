"""Typed JWTs, digest-only sessions and authenticated encrypted templates."""
import hashlib,hmac,json,re,secrets,time,uuid
from datetime import datetime,timezone
import numpy as np
from cryptography.fernet import Fernet,InvalidToken
import jwt
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from app.config import settings
from app.models import User,Session

ISSUER='biosentinel-local';AUDIENCE='biosentinel-api';ALGORITHM='HS256'
pwd_context=CryptContext(schemes=['bcrypt'],deprecated='auto')
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def client_tag(value):return hmac.new(settings.secret_key.encode(),value.encode(),hashlib.sha256).hexdigest()
def username(value):
 value=value.strip().lower()
 if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{2,49}',value):raise ValueError('Username must contain 3–50 letters, numbers, dots, underscores or hyphens')
 return value
def valid_password(value):
 if not isinstance(value,str) or not 8<=len(value.encode('utf-8'))<=72:raise ValueError('Password must contain 8–72 UTF-8 bytes')
 return value
def hash_password(value):return pwd_context.hash(valid_password(value))
def verify_password(plain,hashed):
 try:return pwd_context.verify(valid_password(plain),hashed)
 except (ValueError,TypeError):return False

def encode(user_id,sid,kind,lifetime):
 now=int(time.time())
 return jwt.encode({'sub':str(user_id),'sid':sid,'type':kind,'jti':str(uuid.uuid4()),'iat':now,'nbf':now,'exp':now+lifetime,'iss':ISSUER,'aud':AUDIENCE},settings.secret_key,algorithm=ALGORITHM)

def decode_token(token,expected='access'):
 try:
  if not isinstance(token,str) or len(token)>2048:return None
  claims=jwt.decode(token,settings.secret_key,algorithms=[ALGORITHM],issuer=ISSUER,audience=AUDIENCE,options={'require':['exp','iat','nbf','sub','aud','iss','sid','jti','type']})
  if claims.get('type')!=expected or not str(claims['sub']).isdigit() or int(claims['sub'])<1:return None
  if str(uuid.UUID(claims['sid']))!=claims['sid'] or str(uuid.UUID(claims['jti']))!=claims['jti']:return None
  if any(isinstance(claims.get(k),bool) or not isinstance(claims.get(k),int) for k in ('iat','nbf','exp')):return None
  if claims['iat']>time.time()+5 or claims['nbf']<claims['iat'] or claims['exp']<=claims['iat']:return None
  return claims
 except (JWTError,ValueError,TypeError,KeyError,AttributeError):return None

async def resolve(db,token,expected='access'):
 claims=decode_token(token,expected)
 if claims is None:return None
 session=await db.get(Session,claims['sid'])
 if session is None or session.is_revoked or session.user_id!=int(claims['sub']):return None
 stored=session.access_digest if expected=='access' else session.refresh_digest
 expires=session.expires_at if expected=='access' else session.refresh_expires_at
 if expires<=time.time() or not hmac.compare_digest(stored,digest(token)):return None
 user=await db.get(User,session.user_id)
 if user is None or not user.is_active:return None
 return user,session

async def save_session(db,user_id,ip_tag,family_id=None):
 sid=str(uuid.uuid4());now=time.time();access=encode(user_id,sid,'access',settings.access_seconds);refresh=encode(user_id,sid,'refresh',settings.refresh_seconds)
 session=Session(id=sid,user_id=user_id,family_id=family_id or sid,access_digest=digest(access),refresh_digest=digest(refresh),created_at=now,expires_at=now+settings.access_seconds,refresh_expires_at=now+settings.refresh_seconds,is_revoked=False,ip_tag=ip_tag)
 db.add(session);await db.flush()
 return access,refresh

def encrypt_template(embedding):
 from app.cv.embeddings import validate_embedding
 vector=validate_embedding(embedding)
 return Fernet(settings.encryption_key.encode()).encrypt(json.dumps(vector.tolist(),allow_nan=False).encode()).decode()
def decrypt_template(ciphertext):
 from app.cv.embeddings import validate_embedding
 try:return validate_embedding(json.loads(Fernet(settings.encryption_key.encode()).decrypt(ciphertext.encode())))
 except (InvalidToken,ValueError,TypeError,UnicodeError):raise ValueError('Enrollment template unavailable') from None

async def get_user_by_username(db,name):return (await db.execute(select(User).where(User.username==name))).scalar_one_or_none()
