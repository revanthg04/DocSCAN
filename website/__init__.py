from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager, current_user
from openai import OpenAI

db = SQLAlchemy()
DB_NAME = "database.db"

OPENAI_API_KEY = "hjshjhdjah kjshkjdhjs"
client = OpenAI(api_key=OPENAI_API_KEY)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User

    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Make `current_user` available in all templates
    @app.context_processor
    def inject_user():
        return dict(user=current_user)

    return app
