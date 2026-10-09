"""Compatibility names backed by validated runtime settings."""
from app.config import settings
MATCH_THRESHOLD=settings.match_threshold
RISK_SCORE_STEPUP_THRESHOLD=70
RISK_SCORE_LOCKOUT_THRESHOLD=90
FACE_CONFIDENCE_THRESHOLD=.75
LM_STUDIO_URL=settings.lm_url
GEMMA_TEMPERATURE=0.0
DATABASE_URL=settings.database_url
ACCESS_TOKEN_EXPIRE_MINUTES=settings.access_seconds//60
REFRESH_TOKEN_EXPIRE_DAYS=settings.refresh_seconds//86400
MAX_FAILED_LOGIN_ATTEMPTS=settings.max_failures
SECRET_KEY=settings.secret_key
ALGORITHM='HS256'
