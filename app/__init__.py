# app/__init__.py
import os
from flask import Flask
from app.routes import main

def create_app():
    # chemin du projet
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # dossiers static et templates
    static_folder = os.path.join(project_root, 'static')
    template_folder = os.path.join(project_root, 'templates')

    app = Flask(
        __name__, 
        static_folder=static_folder, 
        static_url_path='/static',
        template_folder=template_folder  # <-- ici !
    )
    app.secret_key = '4f9c8a2d7b6e5f1a9c3d8e7f6a5b4c2d'
    app.register_blueprint(main)
    return app