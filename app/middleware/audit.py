"""Use the actual connected peer; client-supplied forwarding headers are untrusted."""
from app.auth.jwt_service import client_tag
def peer_tag(request):
 return client_tag(request.client.host if request.client else 'unknown')
