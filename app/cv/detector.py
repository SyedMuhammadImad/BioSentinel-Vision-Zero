"""One-face detection; ambiguity and malformed boxes are rejected."""
from dataclasses import dataclass
import numpy as np
from app.config import settings

@dataclass(frozen=True)
class FaceDetection:
 bbox: tuple
 confidence: float
 face_crop: np.ndarray

class FaceDetector:
 def __init__(self):self.model=None
 def load(self):
  from ultralytics import YOLO
  self.model=YOLO(str(settings.weights/'yolov8n-face.pt'))
 def detect(self,frame):
  if self.model is None:self.load()
  faces=[];height,width=frame.shape[:2]
  for result in self.model(frame,verbose=False):
   if result.boxes is None:continue
   for box in result.boxes:
    score=float(box.conf[0])
    if not np.isfinite(score):raise ValueError('Invalid face confidence')
    if score<.75:continue
    coordinates=np.asarray(box.xyxy[0].cpu(),dtype=float)
    if coordinates.shape!=(4,) or not np.isfinite(coordinates).all():raise ValueError('Invalid face box')
    x1,y1,x2,y2=map(int,coordinates);x1=max(0,x1);y1=max(0,y1);x2=min(width,x2);y2=min(height,y2)
    if x2-x1<20 or y2-y1<20:raise ValueError('Face crop too small')
    faces.append(FaceDetection((x1,y1,x2,y2),score,frame[y1:y2,x1:x2]))
  if len(faces)>1:raise ValueError('Exactly one face is required')
  return faces
