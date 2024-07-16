import os
import logging 

from .models import db
from .oidc import config_oidc
from .oidc_bp import oidc_bp

logger = logging.getLogger("log")
logger.propagate = False

LOG_FOLDER_PATH = os.path.join(os.path.dirname(__file__), "../../logs/")
print(LOG_FOLDER_PATH)

def setup_auth(app, log, config=None):
    fileHandler = logging.FileHandler(os.path.join(LOG_FOLDER_PATH, log))
    logger.addHandler(fileHandler)
    logger.setLevel(logging.DEBUG)

    # load environment configuration
    # if 'WEBSITE_CONF' in os.environ:
    #     app.config.from_envvar('WEBSITE_CONF')

    # load app specified configuration
    if config is not None:
        if isinstance(config, dict):
            app.config.update(config)
        elif config.endswith('.py'):
            app.config.from_pyfile(config)

    db.init_app(app)
    # Create tables if they do not exist already
    with app.app_context():
        db.create_all()
    config_oidc(app, iss=config['OAUTH2_JWT_ISS'])
    
    app.register_blueprint(oidc_bp, url_prefix='')
    return app