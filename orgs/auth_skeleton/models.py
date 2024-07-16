import time
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import PickleType
from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)

db = SQLAlchemy()

# hospital user (e.g. doctor, nurse, admin staff, ...)
class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True)
    org = db.Column(db.String(40))
    dept = db.Column(db.String(40))
    role = db.Column(db.String(40))
    affiliations = db.Column(MutableList.as_mutable(PickleType),
                                    default=[])

    def __str__(self):
        return self.username if self.username is not None else "None"

    def get_user_id(self):
        return self.id

"""
OpenID Connect Authentication Server Tables
"""

# clients for the hospital OIDC server (i.e. the rag-app root retriever)
class OpenIDClient(db.Model, OAuth2ClientMixin):
    __tablename__ = 'openid_client'

    id = db.Column(db.Integer, primary_key=True)

class OpenIDAuthorizationCode(db.Model, OAuth2AuthorizationCodeMixin):
    __tablename__ = 'openid_code'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')

class OpenIDToken(db.Model, OAuth2TokenMixin):
    __tablename__ = 'openid_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')