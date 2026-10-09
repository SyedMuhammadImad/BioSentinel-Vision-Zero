"""Authorization requires a live persisted access session; role comes from the DB."""
from fastapi import Depends,HTTPException,Request
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.exc import SQLAlchemyError
from app.database import AsyncSessionLocal
from app.auth.jwt_service import resolve
security=HTTPBearer(auto_error=False)
async def get_current_identity(request:Request,credentials:HTTPAuthorizationCredentials=Depends(security)):
 if credentials is None or credentials.scheme.lower()!='bearer':raise HTTPException(401,'Authentication required')
 try:
  async with AsyncSessionLocal() as db:identity=await resolve(db,credentials.credentials)
 except SQLAlchemyError:raise HTTPException(503,'Authentication storage unavailable') from None
 if identity is None:raise HTTPException(401,'Invalid or expired session')
 request.state.identity=identity;request.state.access_token=credentials.credentials
 return identity
async def get_current_user(identity=Depends(get_current_identity)):return identity[0]
def require_role(*roles):
 async def checker(identity=Depends(get_current_identity)):
  if identity[0].role not in roles:raise HTTPException(403,'This action requires administrator access')
  return identity
 return checker
