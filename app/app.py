from flask import abort, Flask, url_for, session, request, current_app
from flask import render_template, redirect
import os
import requests
import sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from app.auth import setup_auth
from app.pipeline import create_rag_chain_with_source

app = Flask(__name__)
app.secret_key = 'secret'
app.config.from_object('app.config')
oauth = setup_auth(app)

chat_history: list[tuple[str, str, list[dict[str, any]]]] = []  # query, answer, docs

@app.route('/')
def homepage():
    # force user to re-login on startup
    if session.get('user') is None:
        return render_template('home.html', user=None)
    else:
        return redirect('/logout')

@app.route('/success')
def success():
    return render_template('home.html', user=session.get('user')) # force user to re-login on startup

@app.route('/validate_uri', methods=['POST'])
def validate_uri():
    user_uri = request.form.get('uri')
    resp = requests.get(user_uri)
    resp.raise_for_status()
    resp_json = resp.json()
    if 'openid_server_uri' in resp_json:
        oidc_uri = resp_json['openid_server_uri']
        trusted_servers = current_app.config["TRUSTED_OPENID_SERVERS"]
        if oidc_uri in trusted_servers.keys():
            session['oidc_server'] = trusted_servers[oidc_uri]["name"]
            return redirect(url_for('login'))
    abort(404)


@app.route('/login')
def login():
    oidc_server = session['oidc_server'] if 'oidc_server' in session else None
    assert oidc_server is not None

    redirect_uri = url_for('auth', _external=True)
    return getattr(oauth, oidc_server).authorize_redirect(redirect_uri)


@app.route('/auth')
def auth():
    global rag_chain_with_source
    # print(f"rag_app /auth state={request.args.get('state')}")
    oidc_server = session['oidc_server'] if 'oidc_server' in session else None
    assert oidc_server is not None

    token = getattr(oauth, oidc_server).authorize_access_token()
    session['user'] = token['userinfo']
    print(f"rag_app /auth: userinfo={session['user']}")
    rag_chain_with_source = create_rag_chain_with_source(session['user'])
    return redirect('/success')


@app.route('/logout')
def logout():
    global rag_chain_with_source, chat_history
    session.pop('user', None)
    session.pop('oidc_server', None)
    rag_chain_with_source = None
    chat_history = []
    return redirect('/')


@app.route('/queries', methods=['GET', 'POST'])
def queries():
    return render_template("chat.html", chat_history=[], chat_len=0)

# handles the query at the root retriever
@app.route('/handle_query', methods=['POST'])
def handle_query():
    global chat_history

    if not rag_chain_with_source:
        return redirect('/success')

    if (query := request.form.get('query', None)) is not None:
        if len(query) > 0:
            print(f"rag_app invoking query={query}")
            response = rag_chain_with_source.invoke(query)
            chat_history.append((query, response["answer"], response["documents"]))

    return render_template("chat.html", chat_history=chat_history, chat_len=len(chat_history))