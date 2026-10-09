"""V2 tables deliberately avoid silently reusing legacy biometric records."""
import time
from sqlalchemy import Column,String,Integer,Float,Boolean,Text,ForeignKey,CheckConstraint,Index
from app.database import Base

class User(Base):
 __tablename__='principals_v2'
 id=Column(Integer,primary_key=True)
 username=Column(String(50),unique=True,nullable=False)
 email=Column(String(254),unique=True,nullable=False)
 hashed_password=Column(String(255),nullable=False)
 face_embedding=Column(Text,nullable=False) # encrypted authenticated ciphertext
 role=Column(String(20),nullable=False,default='user')
 created_at=Column(Float,nullable=False,default=time.time)
 is_active=Column(Boolean,nullable=False,default=True)
 failure_day=Column(String(10),nullable=False,default='')
 failures=Column(Integer,nullable=False,default=0)
 __table_args__=(CheckConstraint("role in ('user','admin')"),CheckConstraint('failures>=0'))

class Session(Base):
 __tablename__='sessions_v2'
 id=Column(String(36),primary_key=True)
 user_id=Column(Integer,ForeignKey('principals_v2.id'),nullable=False,index=True)
 family_id=Column(String(36),nullable=False,index=True)
 access_digest=Column(String(64),unique=True,nullable=False)
 refresh_digest=Column(String(64),unique=True,nullable=False)
 created_at=Column(Float,nullable=False,default=time.time)
 expires_at=Column(Float,nullable=False)
 refresh_expires_at=Column(Float,nullable=False)
 is_revoked=Column(Boolean,nullable=False,default=False)
 ip_tag=Column(String(64),nullable=False)

class Challenge(Base):
 __tablename__='challenges_v2'
 id=Column(String(64),primary_key=True)
 purpose=Column(String(16),nullable=False)
 subject=Column(String(50),nullable=False)
 session_id=Column(String(36),nullable=True)
 kind=Column(String(16),nullable=False)
 ip_tag=Column(String(64),nullable=False)
 created_at=Column(Float,nullable=False)
 expires_at=Column(Float,nullable=False)
 used=Column(Boolean,nullable=False,default=False)
 __table_args__=(Index('challenge_rate_idx','ip_tag','created_at'),CheckConstraint("purpose in ('enroll','login','heartbeat')"))

class AuditLog(Base):
 __tablename__='events_v2'
 id=Column(Integer,primary_key=True)
 user_id=Column(Integer,ForeignKey('principals_v2.id'),nullable=True)
 actor_id=Column(Integer,ForeignKey('principals_v2.id'),nullable=True)
 action=Column(String(40),nullable=False)
 risk_score=Column(Float,nullable=True)
 ip_tag=Column(String(64),nullable=True)
 timestamp=Column(Float,nullable=False,default=time.time)
 meta=Column(Text,nullable=True)
 __table_args__=(Index('event_owner_time_idx','user_id','timestamp'),)
