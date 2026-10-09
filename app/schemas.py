from typing import Literal
from pydantic import BaseModel,Field,ConfigDict
class ChallengeRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 purpose:Literal['enroll','login','heartbeat']
 username:str=Field(min_length=3,max_length=50)
class RefreshRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 refresh_token:str=Field(min_length=20,max_length=2048)
class TokenResponse(BaseModel):
 access_token:str
 refresh_token:str
 token_type:str='bearer'
 expires_in:int
class UserOut(BaseModel):
 id:int
 username:str
 email:str
 role:str
 is_active:bool
