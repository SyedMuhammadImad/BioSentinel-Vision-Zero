"""Real local CV adapter; optional packages are imported only during model setup."""
import threading,os,logging
os.environ.setdefault('TF_USE_LEGACY_KERAS','1')
logger=logging.getLogger(__name__)
from pathlib import Path
import numpy as np
from app.config import settings
from app.cv.liveness import Observation
from app.cv.embeddings import validate_embedding

class ProviderUnavailable(RuntimeError):pass
class RejectedFace(ValueError):pass

class LocalVisionProvider:
 def __init__(self):self.ready=False;self.landmarker=None;self.lock=threading.Lock()
 def setup(self):
  if not all((settings.weights/name).is_file() for name in ('yolov8n-face.pt','face_landmarker.task')):raise ProviderUnavailable('Required local model assets are missing')
  try:
   import mediapipe as mp
   from mediapipe.tasks.python import BaseOptions
   from mediapipe.tasks.python.vision import FaceLandmarker,FaceLandmarkerOptions,RunningMode
   from deepface import DeepFace
   from retinaface import RetinaFace
   from app.cv.stepup import StepUpDetector
   self.detector=StepUpDetector();self.detector.primary.load()
   self.landmarker=FaceLandmarker.create_from_options(FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(settings.weights/'face_landmarker.task')),running_mode=RunningMode.IMAGE,num_faces=2,min_face_detection_confidence=.5))
   self.deepface=DeepFace;self.mp=mp
   DeepFace.build_model(model_name='Facenet')
   DeepFace.build_model(model_name='Fasnet',task='spoofing')
   RetinaFace.build_model()
   self.ready=True
  except Exception as error:
   logger.error('Local vision setup failed (%s); check model files and runtime compatibility',type(error).__name__)
   self.close();raise ProviderUnavailable('Local vision model setup failed') from None
 def observe(self,frame):
  if not self.ready:raise ProviderUnavailable('Local vision models are not ready')
  if not isinstance(frame,np.ndarray) or frame.dtype!=np.uint8 or frame.ndim!=3 or frame.shape[2]!=3:raise RejectedFace('Invalid RGB frame')
  try:
   with self.lock:
    bgr=np.ascontiguousarray(frame[:,:,::-1]);self.detector.detect(bgr)
    result=self.landmarker.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB,data=np.ascontiguousarray(frame)))
    if len(result.face_landmarks)!=1:raise RejectedFace('Exactly one landmark face is required')
    # Full-frame detection must actually run: skipping detection bypasses the anti-spoof check.
    represented=self.deepface.represent(img_path=bgr,model_name='Facenet',detector_backend='opencv',enforce_detection=True,anti_spoofing=True)
    if len(represented)!=1:raise RejectedFace('Exactly one verified face is required')
    vector=validate_embedding(represented[0]['embedding'])
    points=np.array([[p.x,p.y,p.z] for p in result.face_landmarks[0]],dtype=float)
    return Observation(points,vector,frame.shape[1],frame.shape[0])
  except (RejectedFace,ValueError) as error:raise RejectedFace(str(error)) from None
  except Exception:raise ProviderUnavailable('Vision processing unavailable') from None
 def close(self):
  self.ready=False
  if self.landmarker is not None:self.landmarker.close();self.landmarker=None
