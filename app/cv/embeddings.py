"""Validated FaceNet cosine comparisons; model inference is owned by the provider."""
import numpy as np
from app.config import settings
def validate_embedding(value):
 vector=np.asarray(value,dtype=np.float64)
 if vector.shape!=(128,) or not np.isfinite(vector).all():raise ValueError('Expected a finite 128-dimensional FaceNet vector')
 norm=np.linalg.norm(vector)
 if not np.isfinite(norm) or norm<1e-10:raise ValueError('Invalid zero-norm embedding')
 return vector/norm
def compute_similarity(first,second):
 return float(np.clip(np.dot(validate_embedding(first),validate_embedding(second)),-1,1))
def is_match(first,second):
 score=compute_similarity(first,second);return score>=settings.match_threshold,score
