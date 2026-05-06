from pathlib import Path

from flask import Flask

from gerenciador_app.config import SECRET_KEY
from gerenciador_app.db import initialize_database
from gerenciador_app.web.forms import csrf_token_field, validate_csrf_token
from gerenciador_app.web.routes import register_routes


def create_app():
    initialize_database()

    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )
    app.config["SECRET_KEY"] = SECRET_KEY
    app.before_request(validate_csrf_token)

    @app.context_processor
    def inject_form_helpers():
        return {"csrf_token_field": csrf_token_field}

    register_routes(app)

    return app
