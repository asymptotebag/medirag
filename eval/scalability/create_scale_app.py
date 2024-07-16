from flask import Flask, Blueprint, jsonify, request
import json
import os
import sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

ORG_RETRIEVER = None

hosp_bp = Blueprint('scale', __name__)
@hosp_bp.route('/api/retrieve', methods=['GET'])
def retrieve():
    if request.method == 'GET':
        print(f"/api/retrieve GET args={request.args}")
        query = request.args.get('query')
        userinfo = json.loads(request.args.get('userinfo'))
        search_kwargs = json.loads(request.args.get('search_kwargs'))
        docs = ORG_RETRIEVER.get_relevant_documents(query=query, userinfo=userinfo, search_kwargs=search_kwargs)
        print(f"retrieved {len(docs)} docs.")
        return jsonify(docs=[doc.to_json() for doc in docs], query=query)
    return jsonify()

def create_scale_app(name, uri, org_retriever):
    global ORG_RETRIEVER
    ORG_RETRIEVER = org_retriever

    print(f"CREATING SCALE APP name={name} uri={uri}")
    app = Flask(__name__)
    app.config.update({'HOSPITAL_ID': f'{name}'})
    app.register_blueprint(hosp_bp, url_prefix='')

    return app

