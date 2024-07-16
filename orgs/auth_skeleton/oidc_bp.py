import time
import pandas as pd
from flask import (
    Blueprint, 
    request, 
    session, 
    url_for,
    render_template, 
    redirect, 
    jsonify,
    current_app
)
from werkzeug.security import gen_salt
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from .models import db, User, OpenIDClient
from .oidc import authenticator, require_oidc, generate_user_info

oidc_bp = Blueprint('oidc', __name__, template_folder='templates')

def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def split_by_crlf(s):
    return [v for v in s.splitlines() if v]

@oidc_bp.route('/')
def home():
    return redirect(url_for('oidc.login'))

@oidc_bp.route('/oidc/clients', methods=('GET', 'POST'))
def list_clients():
    clients = OpenIDClient.query.all()
    return render_template('oidc/clients.html', hosp=current_app.config['HOSPITAL_ID'], clients=clients)

@oidc_bp.route('/oidc/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['user_id'] = user.id
        # if user is not just to log in, but need to head back to the auth page, then go for it
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect('/oidc/login')
    user = current_user()
    return render_template('oidc/login.html', hosp=current_app.config['HOSPITAL_ID'], user=user)

@oidc_bp.route('/oidc/logout')
def logout():
    del session['user_id']
    return redirect('/')

@oidc_bp.route('/oidc/create_client', methods=('GET', 'POST'))
def create_client():
    if request.method == 'GET':
        return render_template('oidc/create_client.html', hosp=current_app.config['HOSPITAL_ID'])

    client_id = gen_salt(24)
    client_id_issued_at = int(time.time())
    client = OpenIDClient(
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
    )

    form = request.form
    # client_metadata_from_form = {
    #     "client_name": form["client_name"],
    #     "client_uri": form["client_uri"],
    #     "grant_types": split_by_crlf(form["grant_type"]),
    #     "redirect_uris": split_by_crlf(form["redirect_uri"]),
    #     "response_types": split_by_crlf(form["response_type"]),
    #     "scope": form["scope"],
    #     "token_endpoint_auth_method": form["token_endpoint_auth_method"]
    # }
    client_metadata = {  # fill in constants
        "client_name": form["client_name"],
        "client_uri": form["client_uri"],
        "grant_types": ["authorization_code"],
        "redirect_uris": ["http://127.0.0.1:5000/auth"],
        "response_types": ["code", "token"],
        "scope": "openid profile",
        "token_endpoint_auth_method": "client_secret_basic",
    }
    client.set_client_metadata(client_metadata)

    # if form['token_endpoint_auth_method'] == 'none':
    #     client.client_secret = ''
    # else:
    client.client_secret = gen_salt(48)

    db.session.add(client)
    db.session.commit()
    return redirect('/oidc/clients')

@oidc_bp.route('/oidc/authorize', methods=['GET', 'POST'])
def authorize():
    user = current_user()
    # if user is not currently logged in, they need to log in before authorizing
    if not user:
        return redirect(url_for('oidc.login', next=request.url))
    if request.method == 'GET':
        try:
            grant = authenticator.get_consent_grant(end_user=user)
        except OAuth2Error as error:
            return error.error
        return render_template('oidc/authorize.html', user=user, grant=grant)
    if request.form['confirm']:
        grant_user = user
    else:
        grant_user = None
    return authenticator.create_authorization_response(grant_user=grant_user)

@oidc_bp.route('/oidc/token', methods=['POST'])
def issue_token():
    return authenticator.create_token_response()

@oidc_bp.route('/oidc/revoke', methods=['POST'])
def revoke_token():
    return authenticator.create_endpoint_response('revocation')

@oidc_bp.route('/oidc/userinfo', methods=['GET'])
@require_oidc(["profile"])
def userinfo():
    return jsonify(generate_user_info(user=current_token.user, scope=current_token.scope))