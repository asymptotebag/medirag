from flask import Flask
import os
import sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
from orgs.auth_skeleton.setup import setup_auth
from orgs.hospitalB.hosp_bp import hosp_bp

app = Flask(__name__)
app.config.update({'HOSPITAL_ID': 'hospitalB'})
app = setup_auth(app, "B.txt",
    config={
        'SECRET_KEY': 'secret',
        'OAUTH2_REFRESH_TOKEN_GENERATOR': True,
        'OAUTH2_JWT_ENABLED': True,
        'OAUTH2_JWT_ISS': 'http://127.0.0.1:5002',
        'OAUTH2_JWT_KEY': 'secret-key',
        'OAUTH2_JWT_ALG': 'HS256', # TODO
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///hospitalB.db.sqlite',
    }
)
app.register_blueprint(hosp_bp, url_prefix='')