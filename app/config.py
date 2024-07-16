# client_id and client_secret values for the RAG system
# on each hospital OpenID Connect authentication server

# NOTE: fill these values out after registering an OIDC client for MediRAG
# at the /create_client endpoint of each hospital server.
HOSPITALA_CLIENT_ID = "TODO"
HOSPITALA_CLIENT_SECRET = "TODO"
HOSPITALB_CLIENT_ID = "TODO"
HOSPITALB_CLIENT_SECRET = "TODO"
HOSPITALC_CLIENT_ID = "TODO"
HOSPITALC_CLIENT_SECRET = "TODO"


# TODO we might use urllib actual URI objects instead of strings
TRUSTED_OPENID_SERVERS = {
                        'http://127.0.0.1:5001': {"name": 'hospitalA', 
                                                  "server_metadata_url": 'http://127.0.0.1:5001/.well-known/openid-configuration'}, 
                        'http://127.0.0.1:5002': {"name": 'hospitalB', 
                                                  "server_metadata_url": 'http://127.0.0.1:5002/.well-known/openid-configuration'}, 
                        'http://127.0.0.1:5003': {"name": 'hospitalC', 
                                                  "server_metadata_url": 'http://127.0.0.1:5003/.well-known/openid-configuration'}
                    }

REGISTERED_HOSPITAL_ENDPOINTS = {"http://127.0.0.1:5001/api/retrieve", "http://127.0.0.1:5002/api/retrieve", "http://127.0.0.1:5003/api/retrieve"}