from flask import (
    Blueprint, 
    request, 
    jsonify, 
    url_for, 
    Response,
    current_app
)
import json
import os
import pandas as pd
import sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from py_abac.storage.memory import MemoryStorage
from py_abac import PDP, EvaluationAlgorithm, Policy
from core.federated_retriever import LeafRetriever, RouterRetriever
from orgs.hospitalC.access_policy import ORG_POLICIES, DEPT_POLICIES, DEPT_GATE_POLICIES
from orgs.auth_skeleton.models import db, User

ORG = "C"
HOSP_DATA_PATH = "data/"
QDRANT_PATH = "qdrant/"
DEPTS = ["admissions", "neurology"]
ROLES = ["physician", "nurse", "technician", "researcher", "student"]

# Set up leaf retriever for each department with access-control policies
child_retrievers = []
for dept in DEPTS:
    dept_df = pd.read_csv(os.path.join(HOSP_DATA_PATH, f"{dept}.csv"))
    db_path = os.path.join(QDRANT_PATH, dept)

    # gate policies
    dept_gate_policies = [Policy.from_json(policy_json) for policy_json in DEPT_GATE_POLICIES[dept]]
    storage_gate = MemoryStorage()
    for policy in dept_gate_policies:
        storage_gate.add(policy)
    pdp_gate = PDP(storage_gate, EvaluationAlgorithm.ALLOW_OVERRIDES)

    # final policies
    dept_policies = [Policy.from_json(policy_json) for policy_json in DEPT_POLICIES[dept]]
    storage = MemoryStorage()
    for policy in dept_policies:
        storage.add(policy)
    pdp = PDP(storage, EvaluationAlgorithm.ALLOW_OVERRIDES)

    dept_retriever = LeafRetriever(
                                    id=dept, 
                                    db_path=db_path,
                                    df=dept_df,
                                    text_col=(None if dept=="admissions" else "text"),
                                    abac_gate=pdp_gate, 
                                    abac_pdp=pdp, 
                                    metadata={'org': ORG, 'dept_id': dept}
                                )
    child_retrievers.append(dept_retriever)

# Set up router retriever for Hospital C with above leaf retrievers as children
org_policies = [Policy.from_json(policy_json) for policy_json in ORG_POLICIES]
storage = MemoryStorage()
for policy in org_policies:
    storage.add(policy)
pdp = PDP(storage, EvaluationAlgorithm.ALLOW_OVERRIDES)
org_retriever = RouterRetriever(id=ORG, 
                                children=child_retrievers, 
                                abac_gate=pdp, 
                                metadata={'org': ORG, 'depts': DEPTS})
hosp_bp = Blueprint('hospitalC', __name__)

@hosp_bp.route('/api/retrieve', methods=['GET'])
def retrieve():
    if request.method == 'GET':
        print(f"/api/retrieve GET args={request.args}")
        query = request.args.get('query')
        userinfo = json.loads(request.args.get('userinfo'))
        search_kwargs = json.loads(request.args.get('search_kwargs'))
        docs = org_retriever.get_relevant_documents(query=query, userinfo=userinfo, search_kwargs=search_kwargs)
        print(f"{ORG} retrieved {len(docs)} docs.")
        return jsonify(docs=[doc.to_json() for doc in docs], query=query)
    return jsonify()

@hosp_bp.route('/certs', methods=['GET'])
def jwks_keys():
    keys = {'a': 1, 'b': 2}
    return jsonify(**keys) # TODO RSA256 signing keys

@hosp_bp.route('/.well-known/openid-configuration', methods=['GET'])
def openid_info():
    config = {
        "issuer": current_app.config['OAUTH2_JWT_ISS'],
        "authorization_endpoint": url_for('oidc.authorize', _external=True),
        "token_endpoint": url_for('oidc.issue_token', _external=True),
        "registration_endpoint": url_for('oidc.create_client', _external=True),
        "userinfo_endpoint": url_for('oidc.userinfo', _external=True),
        "revocation_endpoint": url_for('oidc.revoke_token', _external=True),
        "jwks_uri": url_for('hospitalC.jwks_keys', _external=True),
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
            "code token id_token",
            "none"
        ],
        "subject_types_supported": [
            "public"
        ],
        "id_token_signing_alg_values_supported": [
            "RS256",
            "HS256"
        ],
        "scopes_supported": [
            "openid",
            "profile",
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic"
        ],
        "claims_supported": [
            "aud",
            "exp",
            "iat",
            "iss",
            "sub",
            "name",
            "org",
            "role",
            "dept",
            "affiliations"
        ],
        "code_challenge_methods_supported": [
            "plain",
            "S256"
        ],
        "grant_types_supported": [
            "authorization_code",
            "refresh_token"
        ]
    }
    return Response(
        response=json.dumps(config, indent = 2),
        status=200,
        mimetype='application/json'
    )


@hosp_bp.route('/test/dump_users')
def dump_users():
    DUMMY_USERS = [
    ]

    for dummy in DUMMY_USERS:
        user = User.query.filter_by(username=dummy['username']).first()
        if not user:
            user = User(username=dummy['username'], org=ORG, dept=dummy['dept'], role=dummy['role'], affiliations=dummy.get('affiliations', []))
            db.session.add(user)
        else:
            user.username = dummy['username']
            user.org = ORG
            user.dept = dummy['dept']
            user.role = dummy['role']
            user.affiliations = dummy.get('affiliations', [])
        db.session.commit()

    return jsonify(DUMMY_USERS)