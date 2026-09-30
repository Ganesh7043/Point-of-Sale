import os
from flask import Flask

from .database import init_db
from .routes import bp


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')

    with app.app_context():
        init_db()
    app.register_blueprint(bp)

    return app
