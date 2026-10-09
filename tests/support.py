"""Synthetic observations for protocol tests, never a production authentication provider."""
import io
import numpy as np
from PIL import Image
from app.cv.liveness import Observation,LEFT,RIGHT
from app.cv.provider import ProviderUnavailable

def observation(eye=.3,offset=.5,identity=0):
 points=np.full((478,3),.5);points[:,2]=0
 for indices,start in [(LEFT,.3),(RIGHT,.6)]:
  p=np.array([[start,.5],[start+.03,.5-eye*32/480],[start+.06,.5-eye*32/480],[start+.1,.5],[start+.06,.5+eye*32/480],[start+.03,.5+eye*32/480]])
  points[indices,:2]=p
 points[234,0]=.2;points[454,0]=.8;points[1,0]=.2+.6*offset
 vector=np.zeros(128);vector[identity]=1
 return Observation(points,vector,320,240)

class SyntheticVision:
 ready=True
 def __init__(self):self.index=0;self.mode='normal';self.identity=0
 def setup(self):self.ready=True
 def close(self):self.ready=False
 def observe(self,frame):
  position=self.index%24;self.index+=1
  if self.mode=='unavailable':raise ProviderUnavailable('Synthetic outage')
  result=observation(.1 if position in (2,3) and self.mode!='static' else .3,identity=self.identity)
  if self.mode=='degenerate':result.landmarks[LEFT]=.5
  if self.mode=='nan':result.embedding[0]=float('nan')
  return result

def frames():
 result=[]
 for i in range(24):
  image=Image.new('RGB',(64,64),(i*7,120,80));memory=io.BytesIO();image.save(memory,format='PNG')
  result.append(('frames',(f'frame-{i}.png',memory.getvalue(),'image/png')))
 return result

def timing():return __import__('json').dumps([i*100 for i in range(24)])
