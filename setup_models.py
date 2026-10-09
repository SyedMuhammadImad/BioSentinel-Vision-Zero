"""Fetch the two versioned model assets and verify their tested hashes."""
import argparse,hashlib,os,urllib.request,uuid
from pathlib import Path
ASSETS={
 'face_landmarker.task':('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task','64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff'),
 'yolov8n-face.pt':('https://github.com/akanametov/yolo-face/releases/download/1.0.0/yolov8n-face.pt','d545bf1add5aa736a4febac4f4f9245a6d596cd0fe70d5d57989fe0cb9e626ca')}

def fetch(directory):
 directory.mkdir(parents=True,exist_ok=True)
 for name,(url,expected) in ASSETS.items():
  target=directory/name
  if target.exists():
   with target.open('rb') as file:actual=hashlib.file_digest(file,'sha256').hexdigest()
   if actual!=expected:raise ValueError('Existing model hash differs: '+name)
   print(name+': verified');continue
  temporary=directory/(name+'.'+uuid.uuid4().hex+'.part');digest=hashlib.sha256();total=0
  try:
   with urllib.request.urlopen(url,timeout=60) as response,temporary.open('xb') as file:
    while block:=response.read(65536):
     total+=len(block)
     if total>50_000_000:raise ValueError('Model download exceeds limit')
     file.write(block);digest.update(block)
   if digest.hexdigest()!=expected:raise ValueError('Model download hash differs: '+name)
   os.replace(temporary,target);print(name+': downloaded and verified')
  finally:
   if temporary.exists():temporary.unlink()

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,default=Path('weights'))
 fetch(parser.parse_args().directory)
