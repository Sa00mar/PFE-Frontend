import os
from flask import Flask
from app.routes import main


def create_app():
    # static folder is at project root/static, not app/static
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    static_folder = os.path.join(project_root, 'static')

    app = Flask(__name__, static_folder=static_folder, static_url_path='/static')
    app.secret_key = 'ma_cle_secrete'  # nécessaire pour session
    app.register_blueprint(main)
    return app