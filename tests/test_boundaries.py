"""Adversarial geometry, upload, encryption and scoring boundaries."""
import io,json,dataclasses
import numpy as np
import pytest
import httpx
from PIL import Image
from starlette.datastructures import UploadFile
from fastapi import HTTPException
from cryptography.fernet import Fernet
from tests.support import observation
from app.cv.liveness import verify_sequence,LEFT
from app.cv.uploads import decode_image,read_sequence
from app.auth.jwt_service import encrypt_template,decrypt_template
from app.risk import engine as risk

def sequence(kind='blink'):
 rows=[observation() for _ in range(8)]
 for i in (2,3):rows[i]=observation(eye=.1) if kind=='blink' else observation(offset=.75 if kind=='turn_left' else .25)
 return rows,[i*100 for i in range(8)]

@pytest.mark.parametrize('kind',['blink','turn_left','turn_right'])
def test_temporal_actions(kind):
 rows,times=sequence(kind)
 assert np.allclose(verify_sequence(rows,kind,times),rows[-1].embedding)

@pytest.mark.parametrize('attack',['static','closed','one_eye','degenerate','nan','identity','no_return','wrong_action','flat_time','bool_time','short_time','late_time'])
def test_temporal_rejects(attack):
 rows,times=sequence()
 if attack=='static':rows=[observation() for _ in rows]
 elif attack=='closed':rows=[observation(eye=.1) for _ in rows]
 elif attack=='one_eye':
  for i in (2,3):rows[i].landmarks[LEFT]=observation().landmarks[LEFT]
 elif attack=='degenerate':rows[2].landmarks[LEFT]=.5
 elif attack=='nan':rows[3].landmarks[0,0]=np.nan
 elif attack=='identity':rows[4]=observation(identity=1)
 elif attack=='no_return':rows[-1]=observation(eye=.1)
 elif attack=='wrong_action':rows,times=sequence('turn_right')
 elif attack=='flat_time':times[3]=times[2]
 elif attack=='bool_time':times[0]=False
 elif attack=='short_time':times=[i*10 for i in range(8)]
 elif attack=='late_time':times[-1]=7000
 with pytest.raises(ValueError):verify_sequence(rows,'blink',times)

def test_encryption_authentication(monkeypatch):
 vector=observation().embedding;encrypted=encrypt_template(vector)
 assert np.allclose(decrypt_template(encrypted),vector)
 for broken in [encrypted[:-4],encrypted[:40]+'!'+encrypted[41:],'[]','']:
  with pytest.raises(ValueError):decrypt_template(broken)
 import app.auth.jwt_service as jwt
 monkeypatch.setattr(jwt,'settings',dataclasses.replace(jwt.settings,encryption_key=Fernet.generate_key().decode()))
 with pytest.raises(ValueError):decrypt_template(encrypted)

@pytest.mark.parametrize('shape,format', [((20,32),'PNG'),((1001,1000),'PNG'),((32,32),'GIF')])
def test_decode_limits(shape,format):
 memory=io.BytesIO();Image.new('RGB',shape).save(memory,format=format)
 with pytest.raises(ValueError):decode_image(memory.getvalue())

@pytest.mark.asyncio
async def test_repeated_uploads_closed():
 memory=io.BytesIO();Image.new('RGB',(32,32)).save(memory,format='PNG')
 files=[UploadFile(io.BytesIO(memory.getvalue()),filename='frame.png') for _ in range(8)]
 with pytest.raises(HTTPException):await read_sequence(files,json.dumps(list(range(8))))
 assert all(file.file.closed for file in files)

def signals(**updates):return {'face_similarity':.9,'failed_attempts_today':0,'actions_per_minute':0,'ip_changed':False,**updates}

@pytest.mark.parametrize('raw',[{}, {'risk_score':True,'reason':'bad'}, {'risk_score':float('nan'),'reason':'bad'}, {'risk_score':101,'reason':'bad'}, {'risk_score':0,'reason':''}, {'risk_score':0,'reason':'fine','extra':1}])
def test_invalid_model_scores(raw):
 with pytest.raises(risk.RiskUnavailable):risk.validate_score(raw)

@pytest.mark.parametrize('updates',[{'face_similarity':True},{'face_similarity':float('nan')},{'failed_attempts_today':-1},{'actions_per_minute':float('inf')},{'ip_changed':'no'}])
def test_invalid_signals(updates):
 with pytest.raises(risk.RiskUnavailable):risk.rule_score(signals(**updates))

@pytest.mark.asyncio
async def test_model_cannot_reduce_enforcement(monkeypatch):
 monkeypatch.setattr(risk,'settings',dataclasses.replace(risk.settings,risk_mode='gemma'))
 async def low(_):return {'risk_score':0,'reason':'low'}
 monkeypatch.setattr(risk,'query_gemma',low)
 assert (await risk.evaluate_risk(signals(face_similarity=.2)))[0]==95
 assert (await risk.evaluate_risk(signals(face_similarity=.65,ip_changed=True)))[0]==85

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['valid','malformed','oversized','http_error','offline'])
async def test_bounded_local_model_adapter(monkeypatch,mode):
 real_client=httpx.AsyncClient
 def handle(request):
  assert request.url.host=='127.0.0.1'
  body=json.loads(request.content)
  assert body['temperature']==0 and 'embedding' not in request.content.decode()
  if mode=='offline':raise httpx.ConnectError('offline',request=request)
  if mode=='http_error':return httpx.Response(503)
  if mode=='oversized':return httpx.Response(200,content=b' '*17000)
  answer='not JSON' if mode=='malformed' else json.dumps({'risk_score':20,'reason':'bounded'})
  return httpx.Response(200,json={'choices':[{'message':{'content':answer}}]})
 monkeypatch.setattr(risk.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handle),**kwargs))
 if mode=='valid':assert await risk.query_gemma(signals())=={'risk_score':20,'reason':'bounded'}
 else:
  with pytest.raises(risk.RiskUnavailable):await risk.query_gemma(signals())
