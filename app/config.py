"""Runtime configuration; no shared credentials or permissive production defaults."""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import os
from cryptography.fernet import Fernet

@dataclass(frozen=True)
class Settings:
 secret_key: str
 encryption_key: str
 database_url: str
 weights: Path
 risk_mode: str
 lm_url: str
 lm_model: str
 match_threshold: float = .6
 access_seconds: int = 900
 refresh_seconds: int = 604800
 challenge_seconds: int = 45
 max_failures: int = 3

def load_settings():
 secret=os.environ.get('BIOSENTINEL_SECRET_KEY','')
 if len(secret)<32 or len(set(secret))<10 or any(x in secret.lower() for x in ('redacted','change_me','placeholder')):
  raise RuntimeError('Set BIOSENTINEL_SECRET_KEY to a private random value of at least 32 characters')
 encryption=os.environ.get('BIOSENTINEL_ENCRYPTION_KEY','')
 try:Fernet(encryption.encode('ascii'))
 except Exception:raise RuntimeError('Set BIOSENTINEL_ENCRYPTION_KEY to a separate generated Fernet key') from None
 database=os.environ.get('BIOSENTINEL_DATABASE_URL','sqlite+aiosqlite:///./private/biosentinel.db')
 if not database.startswith('sqlite+aiosqlite:///') or '?' in database:raise RuntimeError('This prototype requires a dedicated SQLite database')
 mode=os.environ.get('BIOSENTINEL_RISK_MODE','rules')
 if mode not in ('rules','gemma'):raise RuntimeError('BIOSENTINEL_RISK_MODE must be rules or gemma')
 url=os.environ.get('BIOSENTINEL_LM_URL','http://127.0.0.1:1234/v1')
 parsed=urlsplit(url)
 if parsed.scheme not in ('http','https') or parsed.hostname not in ('localhost','127.0.0.1','::1') or parsed.username or parsed.password or parsed.query or parsed.fragment:
  raise RuntimeError('Risk model URL must refer to a local server without credentials or query parameters')
 return Settings(secret,encryption,database,Path(os.environ.get('BIOSENTINEL_WEIGHTS_DIR','weights')).resolve(),mode,url.rstrip('/'),os.environ.get('BIOSENTINEL_LM_MODEL','gemma'))

settings=load_settings()
