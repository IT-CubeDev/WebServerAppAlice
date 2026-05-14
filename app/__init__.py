from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from config import BASE_DIR, Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
csrf = CSRFProtect()


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    cfg = config_object or Config
    app.config.from_object(cfg)

    (BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401

    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.api import bp as api_bp
    from app.alice.webhook import bp as alice_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(alice_bp)
    csrf.exempt(alice_bp)
    csrf.exempt(api_bp)

    with app.app_context():
        db.create_all()

    return app
