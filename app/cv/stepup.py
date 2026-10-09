"""Retained YOLO-to-RetinaFace cascade with explicit one-face selection."""
import numpy as np
from app.cv.detector import FaceDetector,FaceDetection
class StepUpDetector:
 def __init__(self):self.primary=FaceDetector()
 def detect(self,frame):
  found=self.primary.detect(frame)
  if found:return found[0]
  from retinaface import RetinaFace
  results=RetinaFace.detect_faces(frame)
  if not isinstance(results,dict) or not results:raise ValueError('No face detected')
  faces=[face for face in results.values() if np.isfinite(face['score']) and face['score']>=.75]
  if len(faces)!=1:raise ValueError('Exactly one confident face is required')
  face=faces[0];height,width=frame.shape[:2];x1,y1,x2,y2=map(int,face['facial_area'])
  x1=max(0,x1);y1=max(0,y1);x2=min(width,x2);y2=min(height,y2)
  if x2-x1<20 or y2-y1<20:raise ValueError('Face crop too small')
  return FaceDetection((x1,y1,x2,y2),float(face['score']),frame[y1:y2,x1:x2])
