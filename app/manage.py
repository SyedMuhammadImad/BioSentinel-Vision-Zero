"""Offline, explicit administrator provisioning for the dedicated database."""
import argparse,asyncio
from sqlalchemy import select,update
from app.database import transaction,engine
from app.models import User,Session
from app.auth.events import event
from app.auth.jwt_service import username as canonical_username

async def grant(username):
 try:
  async with transaction() as db:
   user=(await db.execute(select(User).where(User.username==canonical_username(username)))).scalar_one_or_none()
   if user is None:raise ValueError('Enroll the account first')
   if not user.is_active:raise ValueError('Inactive account cannot become an administrator')
   user.role='admin'
   await db.execute(update(Session).where(Session.user_id==user.id).values(is_revoked=True))
   event(db,user.id,'offline_admin_granted',actor_id=user.id)
  print('Administrator role recorded; sign in again. Existing sessions revoked.')
 finally:await engine.dispose()

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('action',choices=['grant-admin']);parser.add_argument('username')
 args=parser.parse_args()
 try:asyncio.run(grant(args.username))
 except ValueError as error:parser.exit(1,str(error)+'\n')

if __name__=='__main__':main()
