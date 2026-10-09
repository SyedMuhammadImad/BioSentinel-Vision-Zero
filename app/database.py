"""Dedicated database; atomic writes commit before a success response is issued."""
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy import event,text
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from sqlalchemy.orm import declarative_base
from app.config import settings

filename=settings.database_url.removeprefix('sqlite+aiosqlite:///')
if filename != ':memory:':Path(filename).expanduser().resolve().parent.mkdir(parents=True,exist_ok=True)
engine=create_async_engine(settings.database_url,connect_args={'timeout':10},echo=False)
@event.listens_for(engine.sync_engine,'connect')
def configure(connection,_):
 cursor=connection.cursor();cursor.execute('PRAGMA foreign_keys=ON');cursor.execute('PRAGMA busy_timeout=10000');cursor.close()
AsyncSessionLocal=async_sessionmaker(engine,expire_on_commit=False)
Base=__import__('sqlalchemy.orm',fromlist=['declarative_base']).declarative_base()

async def create_tables():
 from app import models
 async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def transaction():
 async with AsyncSessionLocal() as session:
  try:
   await session.execute(text('BEGIN IMMEDIATE'))
   yield session
   await session.commit()
  except BaseException:
   await session.rollback();raise

async def get_db():
 async with AsyncSessionLocal() as session:yield session
