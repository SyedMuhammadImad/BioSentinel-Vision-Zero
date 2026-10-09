"""Local launcher with private generated settings and model caches."""
import argparse,json,os,secrets
from pathlib import Path
from cryptography.fernet import Fernet

def configure(root):
 root=root.resolve();root.mkdir(parents=True,exist_ok=True)
 config=root/'runtime.json'
 if not config.exists():
  payload={'signing_key':secrets.token_urlsafe(48),'encryption_key':Fernet.generate_key().decode()}
  with config.open('x',encoding='utf-8') as file:json.dump(payload,file)
  try:config.chmod(0o600)
  except OSError:pass
 payload=json.loads(config.read_text(encoding='utf-8'))
 os.environ.setdefault('BIOSENTINEL_SECRET_KEY',payload['signing_key'])
 os.environ.setdefault('BIOSENTINEL_ENCRYPTION_KEY',payload['encryption_key'])
 os.environ.setdefault('BIOSENTINEL_DATABASE_URL','sqlite+aiosqlite:///'+(root/'biosentinel.db').as_posix())
 for name,folder in [('DEEPFACE_HOME','models'),('KERAS_HOME','keras'),('YOLO_CONFIG_DIR','yolo'),('MPLCONFIGDIR','matplotlib')]:
  directory=root/folder;directory.mkdir(exist_ok=True);os.environ.setdefault(name,str(directory))
 for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS'):os.environ.setdefault(name,'2')
 os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
 os.environ.setdefault('TF_USE_LEGACY_KERAS','1')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--private-dir',type=Path,default=Path('private'))
 parser.add_argument('--weights-dir',type=Path,default=Path('weights'))
 parser.add_argument('--port',type=int,default=8000)
 parser.add_argument('--grant-admin',metavar='USERNAME')
 args=parser.parse_args();configure(args.private_dir)
 os.environ['BIOSENTINEL_WEIGHTS_DIR']=str(args.weights_dir.resolve())
 if args.grant_admin:
  import asyncio
  from app.manage import grant
  asyncio.run(grant(args.grant_admin));return
 import uvicorn
 uvicorn.run('app.main:app',host='127.0.0.1',port=args.port,proxy_headers=False)

if __name__=='__main__':main()
