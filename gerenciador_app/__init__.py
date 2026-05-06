from pathlib import Path

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from gerenciador_app.config import IS_PRODUCTION, IS_VERCEL, SECRET_KEY
from gerenciador_app.db import initialize_database
from gerenciador_app.web.forms import csrf_token_field, validate_csrf_token
from gerenciador_app.web.routes import register_routes


def create_app():
    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )
    # Ajusta host e protocolo quando a aplicacao roda atras do proxy do Vercel.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.update(
        SECRET_KEY=SECRET_KEY,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=IS_PRODUCTION or IS_VERCEL,
        PREFERRED_URL_SCHEME="https" if IS_PRODUCTION or IS_VERCEL else "http",
    )
    database_ready = False

    @app.before_request
    def ensure_database_ready():
        nonlocal database_ready
        if database_ready:
            return None

        # Evita exigir acesso ao banco durante o import/build do Vercel.
        initialize_database()
        database_ready = True
        return None

    app.before_request(validate_csrf_token)

    @app.context_processor
    def inject_form_helpers():
        return {"csrf_token_field": csrf_token_field}

    register_routes(app)

    return app
