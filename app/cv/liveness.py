"""Temporal challenge geometry. This is not a certified replay-attack defense."""
from dataclasses import dataclass
import numpy as np
from app.cv.embeddings import validate_embedding,compute_similarity

LEFT=[33,160,158,133,153,144];RIGHT=[362,385,387,263,373,380]
INSTRUCTIONS={'blink':'Start facing forward with eyes open; close both eyes briefly, then open them again.',
 'turn_left':'Start facing forward; move your nose toward the right edge of the camera image, then return to the center.',
 'turn_right':'Start facing forward; move your nose toward the left edge of the camera image, then return to the center.'}

@dataclass(frozen=True)
class Observation:
 landmarks: np.ndarray
 embedding: np.ndarray
 width: int
 height: int

def geometry(observation):
 landmarks=np.asarray(observation.landmarks,dtype=float)
 if landmarks.ndim!=2 or landmarks.shape[0]<468 or landmarks.shape[1]<2 or not np.isfinite(landmarks).all():raise ValueError('Invalid landmarks')
 points=landmarks[:,:2]
 if (points<0).any() or (points>1).any() or min(observation.width,observation.height)<32:raise ValueError('Invalid landmark coordinates')
 pixels=points*np.array([observation.width,observation.height])
 def eye(indices):
  p=pixels[indices];width=np.linalg.norm(p[0]-p[3])
  if width<2:raise ValueError('Degenerate eye geometry')
  ratio=(np.linalg.norm(p[1]-p[5])+np.linalg.norm(p[2]-p[4]))/(2*width)
  if not 0<=ratio<=1:raise ValueError('Invalid eye geometry')
  return float(ratio)
 left,right=eye(LEFT),eye(RIGHT)
 a,b=points[234,0],points[454,0];width=abs(b-a)
 if width*observation.width<20:raise ValueError('Degenerate face geometry')
 offset=(points[1,0]-min(a,b))/width
 if not 0<=offset<=1:raise ValueError('Invalid head geometry')
 return left,right,float(offset)

def verify_sequence(observations,kind,timestamps):
 if kind not in INSTRUCTIONS or not 8<=len(observations)<=24 or len(timestamps)!=len(observations):raise ValueError('Invalid challenge sequence')
 if any(isinstance(t,bool) or not isinstance(t,(int,float)) for t in timestamps):raise ValueError('Invalid frame timing')
 times=np.asarray(timestamps,dtype=float)
 if not np.isfinite(times).all() or times[0]<0 or (np.diff(times)<=0).any() or times[-1]>6000 or not 600<=times[-1]-times[0]<=6000:raise ValueError('Invalid frame timing')
 reference=validate_embedding(observations[0].embedding)
 geometry_values=[]
 for observation in observations:
  if compute_similarity(reference,observation.embedding)<.6:raise ValueError('Face identity changed within the sequence')
  geometry_values.append(geometry(observation))
 # Two baseline frames, two consecutive action frames, then two baseline frames.
 def baseline(g):
  l,r,x=g
  return .4<=x<=.6 and l>=.25 and r>=.25
 def action(g):
  l,r,x=g
  if kind=='blink':return l<.20 and r<.20 and .4<=x<=.6
  return x>.65 if kind=='turn_left' else x<.35
 if not all(baseline(g) for g in geometry_values[:2]):raise ValueError('Begin with both eyes open and face centered')
 if not all(baseline(g) for g in geometry_values[-2:]):raise ValueError('Finish with both eyes open and face centered')
 for i in range(2,len(geometry_values)-3):
  if action(geometry_values[i]) and action(geometry_values[i+1]):
   if any(baseline(geometry_values[j]) and baseline(geometry_values[j+1]) for j in range(i+2,len(geometry_values)-1)):
    # Use an open/centered terminal frame for the enrolled/login template.
    return validate_embedding(observations[-1].embedding)
 raise ValueError('Requested action and return transition were not observed')
