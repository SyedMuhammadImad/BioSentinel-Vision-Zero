"""Standalone browser fixture. Never imported by the production application."""
import os,secrets,json,sys,tempfile,asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from cryptography.fernet import Fernet
if __name__!='__main__':raise RuntimeError('Launch this test fixture as a separate process')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temporary=tempfile.TemporaryDirectory(prefix='biosentinel-browser-')
os.environ['BIOSENTINEL_SECRET_KEY']=secrets.token_urlsafe(48)
os.environ['BIOSENTINEL_ENCRYPTION_KEY']=Fernet.generate_key().decode()
os.environ['BIOSENTINEL_DATABASE_URL']='sqlite+aiosqlite:///'+(Path(temporary.name)/'test.db').as_posix()
os.environ['BIOSENTINEL_RISK_MODE']='rules'
from app.main import create_app
from tests.support import SyntheticVision,observation
from app.auth.jwt_service import hash_password,encrypt_template
from app.database import transaction
from app.models import User
import app.auth.challenges as challenges
challenges.secrets.choice=lambda _:'blink'
application=create_app(SyntheticVision());original=application.router.lifespan_context
credentials=json.loads(Path(os.environ['BIOSENTINEL_BROWSER_CREDENTIALS_FILE']).read_text())
@asynccontextmanager
async def seeded(app):
 async with original(app):
  async with transaction() as db:
   for name,active,role in [('operator',True,'admin'),('lockeduser',False,'user')]:
    db.add(User(username=name,email=name+'@example.com',hashed_password=hash_password(credentials['operator_password']),face_embedding=encrypt_template(observation().embedding),role=role,is_active=active))
  yield
application.router.lifespan_context=seeded
import uvicorn
uvicorn.run(application,host='127.0.0.1',port=9150,proxy_headers=False,access_log=False)
