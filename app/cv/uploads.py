"""Bound uploaded bytes, decoded pixel counts and distinct frame sequences."""
import hashlib,io,json,warnings
import numpy as np
from PIL import Image,UnidentifiedImageError
from fastapi import HTTPException

MAX_FRAME_BYTES=1_000_000;MAX_SEQUENCE_BYTES=8_000_000;MAX_PIXELS=1_000_000
def decode_image(contents):
 if not contents or len(contents)>MAX_FRAME_BYTES:raise ValueError('Frame byte limit exceeded')
 try:
  with warnings.catch_warnings():
   warnings.simplefilter('error',Image.DecompressionBombWarning)
   with Image.open(io.BytesIO(contents)) as image:
    width,height=image.size
    if image.format not in ('JPEG','PNG') or getattr(image,'n_frames',1)!=1 or min(width,height)<32 or width*height>MAX_PIXELS:raise ValueError('Invalid image dimensions or format')
    return np.array(image.convert('RGB'),dtype=np.uint8)
 except (UnidentifiedImageError,OSError,Image.DecompressionBombWarning,Image.DecompressionBombError):raise ValueError('Invalid image') from None

async def read_sequence(files,timestamps):
 if not 8<=len(files)<=24:raise HTTPException(400,'Supply 8–24 ordered frames')
 try:
  times=json.loads(timestamps)
  if not isinstance(times,list) or len(times)!=len(files) or any(isinstance(x,bool) or not isinstance(x,(int,float)) for x in times):raise ValueError('Invalid timing')
  contents=[];seen=set();total=0
  for file in files:
   data=await file.read(MAX_FRAME_BYTES+1);total+=len(data)
   if len(data)>MAX_FRAME_BYTES:raise HTTPException(413,'Frame exceeds the upload limit')
   if total>MAX_SEQUENCE_BYTES:raise HTTPException(413,'Sequence exceeds the upload limit')
   fingerprint=hashlib.sha256(data).digest()
   if fingerprint in seen:raise ValueError('Repeated frames are not accepted')
   seen.add(fingerprint);contents.append(decode_image(data))
  if len({frame.shape for frame in contents})!=1:raise ValueError('Frame dimensions changed')
  return contents,times
 except (ValueError,TypeError,json.JSONDecodeError):raise HTTPException(400,'Invalid frame sequence or timing') from None
 finally:
  for file in files:await file.close()
