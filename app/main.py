"""Local biometric authentication prototype with a usable browser interface."""
import asyncio,logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool
from app.config import settings
from app.database import create_tables,engine,AsyncSessionLocal
from app.cv.provider import LocalVisionProvider,ProviderUnavailable
from app.middleware.guards import RequestGuards
from app.routers import enroll,login,heartbeat,admin
logger=logging.getLogger(__name__)

def create_app(vision_provider=None):
 vision=vision_provider if vision_provider is not None else LocalVisionProvider()
 @asynccontextmanager
 async def lifespan(application):
  await create_tables();application.state.vision_slot=asyncio.Semaphore(1)
  if not vision.ready:
   try:await run_in_threadpool(vision.setup)
   except ProviderUnavailable:logger.error('Vision unavailable; authentication stays disabled until model setup is fixed')
  yield
  await run_in_threadpool(vision.close);await engine.dispose()
 application=FastAPI(title='BioSentinel',description='Local biometric authentication prototype; physical attack resistance is not certified.',version='2.0.0',lifespan=lifespan,docs_url=None,redoc_url=None)
 application.state.vision=vision
 application.add_middleware(RequestGuards)
 @application.exception_handler(SQLAlchemyError)
 async def storage_error(request,error):
  logger.error('Database operation failed; request denied')
  return JSONResponse({'detail':'Authentication storage unavailable'},503)
 application.include_router(enroll.router);application.include_router(login.router);application.include_router(heartbeat.router);application.include_router(admin.router)
 @application.get('/health')
 async def health():
  database_ready=False
  try:
   async with AsyncSessionLocal() as db:
    await db.execute(text('SELECT 1'));database_ready=True
  except SQLAlchemyError:pass
  ready=vision.ready and database_ready
  return JSONResponse({'status':'ready' if ready else 'unavailable','vision_ready':vision.ready,'database_ready':database_ready,'risk_mode':settings.risk_mode,'risk_model_health':'checked per request' if settings.risk_mode=='gemma' else 'not required','service':'BioSentinel','version':'2.0.0'},200 if ready else 503)
 static=Path(__file__).resolve().parent/'static'
 application.mount('/static',StaticFiles(directory=static),name='static')
 @application.get('/',include_in_schema=False)
 async def home():return FileResponse(static/'index.html')
 return application

app=create_app()
