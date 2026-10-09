"""Bound request bodies before multipart parsing and apply response protections."""
from fastapi import HTTPException
from starlette.responses import JSONResponse
class RequestGuards:
 def __init__(self,app):self.app=app
 async def __call__(self,scope,receive,send):
  if scope['type']!='http':return await self.app(scope,receive,send)
  maximum=8_500_000;headers=dict(scope['headers'])
  try:length=int(headers.get(b'content-length',b'0'))
  except ValueError:length=maximum+1
  consumed=0
  async def bounded_receive():
   nonlocal consumed
   message=await receive();consumed+=len(message.get('body',b''))
   if consumed>maximum:raise HTTPException(413,'Request exceeds upload limit')
   return message
  async def protected_send(message):
   if message['type']=='http.response.start':
    message['headers']+= [(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff'),(b'content-security-policy',b"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"),(b'permissions-policy',b'camera=(self), microphone=()')]
   await send(message)
  if length<0 or length>maximum:return await JSONResponse({'detail':'Request exceeds upload limit'},413)(scope,receive,protected_send)
  await self.app(scope,bounded_receive,protected_send)
