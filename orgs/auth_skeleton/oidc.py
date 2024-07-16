from authlib.integrations.flask_oauth2 import (
    AuthorizationServer, ResourceProtector
)
from authlib.integrations.sqla_oauth2 import (
    create_query_client_func,
    create_save_token_func,
    create_bearer_token_validator,
)
from authlib.oauth2.rfc6749.grants import (
    AuthorizationCodeGrant as _AuthorizationCodeGrant,
)
from authlib.oidc.core.grants import (
    OpenIDCode as _OpenIDCode,
)
from authlib.oidc.core import UserInfo
from werkzeug.security import gen_salt
from .models import (
    db,
    User,
    OpenIDClient,
    OpenIDAuthorizationCode,
    OpenIDToken
)

def generate_user_info(user, scope):
    user_info = UserInfo(sub=str(user.id), name=user.username)

    if "profile" in scope:
        user_info["org"] = user.org
        user_info["dept"] = user.dept
        user_info["role"] = user.role
        user_info["affiliations"] = user.affiliations
        
    return user_info

class AuthorizationCodeGrant(_AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        'client_secret_basic',
        'client_secret_post',
    ]

    def save_authorization_code(self, code, request):
        nonce = request.data.get('nonce')
        auth_code = OpenIDAuthorizationCode(
            code=code,
            client_id=request.client.client_id,
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            user_id=request.user.id,
            nonce=nonce,
        )
        db.session.add(auth_code)
        db.session.commit()
        return code

    def query_authorization_code(self, code, client):
        auth_code = OpenIDAuthorizationCode.query.filter_by(
            code=code, client_id=client.client_id).first()
        if auth_code and not auth_code.is_expired():
            return auth_code

    def delete_authorization_code(self, authorization_code):
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        return User.query.get(authorization_code.user_id)


class OpenIDCode(_OpenIDCode):
    def __init__ (self, iss, require_nonce):
        super().__init__(require_nonce)
        self.iss = iss

    def exists_nonce(self, nonce, request):
        exists = OpenIDAuthorizationCode.query.filter_by(
            client_id=request.client_id, nonce=nonce
        ).first()
        return bool(exists)

    def get_jwt_config(self, grant):
        return {
            'key': 'secret-key',
            'alg': 'HS256',
            'iss': self.iss,
            'exp': 3600,
        }

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)

query_client_oidc = create_query_client_func(db.session, OpenIDClient)
save_token_oidc = create_save_token_func(db.session, OpenIDToken)
authenticator = AuthorizationServer(
    query_client=query_client_oidc,
    save_token=save_token_oidc,
)
require_oidc = ResourceProtector()

def config_oidc(app, iss):
    authenticator.init_app(app)

    # support all openid grants
    authenticator.register_grant(AuthorizationCodeGrant, [
        OpenIDCode(iss=iss, require_nonce=True),
    ])

    # protect resource
    bearer_cls = create_bearer_token_validator(db.session, OpenIDToken)
    require_oidc.register_token_validator(bearer_cls())