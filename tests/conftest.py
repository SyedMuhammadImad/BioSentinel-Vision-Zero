"""Always use generated secrets and an isolated disposable database."""
import os,secrets,tempfile
from pathlib import Path
import pytest_asyncio
from cryptography.fernet import Fernet
_temporary=tempfile.TemporaryDirectory(prefix='biosentinel-tests-')
os.environ['BIOSENTINEL_SECRET_KEY']=secrets.token_urlsafe(48)
os.environ['BIOSENTINEL_ENCRYPTION_KEY']=Fernet.generate_key().decode()
os.environ['BIOSENTINEL_DATABASE_URL']='sqlite+aiosqlite:///'+(Path(_temporary.name)/'isolated.db').as_posix()
os.environ['BIOSENTINEL_RISK_MODE']='rules'
from sqlalchemy import text
from httpx import AsyncClient,ASGITransport
from app.database import Base,engine
from app.main import create_app
from tests.support import SyntheticVision

@pytest_asyncio.fixture
async def environment(monkeypatch):
 import app.auth.challenges as challenges
 monkeypatch.setattr(challenges.secrets,'choice',lambda options:'blink')
 async with engine.begin() as connection:
  await connection.run_sync(Base.metadata.drop_all)
 vision=SyntheticVision();application=create_app(vision)
 async with application.router.lifespan_context(application):
  async with AsyncClient(transport=ASGITransport(app=application),base_url='http://testserver') as client:
   yield client,vision,application
