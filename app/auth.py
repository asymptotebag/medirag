
from authlib.integrations.flask_client import OAuth
import os
import sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from app.config import TRUSTED_OPENID_SERVERS
from base64 import urlsafe_b64encode

def setup_auth(app):
    oauth = OAuth(app)
    for server_uri, server_dict in TRUSTED_OPENID_SERVERS.items():
        oauth.register(
            name=server_dict["name"], 
            server_metadata_url=server_dict["server_metadata_url"],
            jwks={ # TODO until we implement RSA
                "keys": [{
                    "kty": "oct",
                    "alg": "HS256",
                    "k": urlsafe_b64encode(str.encode("secret-key")),
                }]
            },
            client_kwargs={
                'scope': 'openid profile'
            }
        )
    return oauth
