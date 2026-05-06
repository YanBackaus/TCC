import os
import secrets
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse


PAGE_INICIAL = "inicial"
PAGE_EPI = "epi"
PAGE_ESTOQUE = "estoque"
PAGE_MOVIMENTACOES = "movimentacoes"
PAGE_SOLICITACOES = "solicitacoes"
PAGE_USUARIOS = "usuarios"
PAGE_CONFIGURACOES = "configuracoes"
PAGE_PERFIL = "perfil"
STANDARD_USER_TYPE = 0
ADMIN_TYPE = 1
IS_VERCEL = os.environ.get("VERCEL") == "1"
APP_ENV = os.environ.get("APP_ENV", os.environ.get("VERCEL_ENV", "development")).lower()
IS_PRODUCTION = APP_ENV in {"prod", "production"}
AUTO_CREATE_DATABASE = os.environ.get("AUTO_CREATE_DATABASE", "1") == "1"


def _database_settings_from_environment():
    database_url = (os.environ.get("MYSQL_URL") or os.environ.get("DATABASE_URL") or "").strip()
    default_database_name = os.environ.get("DB_NAME", "Gerenciador")
    default_port = int(os.environ.get("DB_PORT", "3306"))

    if not database_url:
        return {
            "host": os.environ.get("DB_HOST", "127.0.0.1"),
            "port": default_port,
            "user": os.environ.get("DB_USER", "root"),
            "password": os.environ.get("DB_PASSWORD", ""),
            "database": default_database_name,
        }

    parsed_url = urlparse(database_url)
    if parsed_url.scheme not in {"mysql", "mysql+mysqlconnector", "mariadb"}:
        raise RuntimeError(
            "Use MYSQL_URL ou DATABASE_URL com o esquema mysql://, mysql+mysqlconnector:// ou mariadb://."
        )

    return {
        "host": parsed_url.hostname or os.environ.get("DB_HOST", "127.0.0.1"),
        "port": parsed_url.port or default_port,
        "user": unquote(parsed_url.username or os.environ.get("DB_USER", "root")),
        "password": unquote(parsed_url.password or os.environ.get("DB_PASSWORD", "")),
        "database": parsed_url.path.lstrip("/") or default_database_name,
    }


DATABASE_SETTINGS = _database_settings_from_environment()
SERVER_CONFIG = {
    "host": DATABASE_SETTINGS["host"],
    "port": DATABASE_SETTINGS["port"],
    "user": DATABASE_SETTINGS["user"],
    "password": DATABASE_SETTINGS["password"],
}
DATABASE_NAME = DATABASE_SETTINGS["database"]
DATABASE_CONFIG = {**SERVER_CONFIG, "database": DATABASE_NAME}
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY")
if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError("Defina SECRET_KEY antes de iniciar o sistema em producao.")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)

if IS_PRODUCTION and (SERVER_CONFIG["user"] == "root" or not SERVER_CONFIG["password"]):
    raise RuntimeError("Defina DB_USER e DB_PASSWORD seguros antes de iniciar em producao.")

PURCHASE_DEPARTMENT_EMAIL = os.environ.get("PURCHASE_DEPARTMENT_EMAIL", "compras@empresa.com")
PASSWORD_RESET_SALT = os.environ.get("PASSWORD_RESET_SALT", "gerenciador-reset-password")
PASSWORD_RESET_EXPIRATION_SECONDS = int(os.environ.get("PASSWORD_RESET_EXPIRATION_SECONDS", "3600"))

MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1") == "1"
MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "0") == "1"
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME or "no-reply@empresa.com")
MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "0") == "1"


def _default_smtp_inbox_dir():
    if IS_VERCEL:
        return Path(tempfile.gettempdir()) / ".smtp-test-inbox"
    return BASE_DIR / ".smtp-test-inbox"


def _default_app_base_url():
    explicit_app_base_url = os.environ.get("APP_BASE_URL", "").strip()
    if explicit_app_base_url:
        return explicit_app_base_url

    for env_var_name in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        host = os.environ.get(env_var_name, "").strip()
        if host:
            return f"https://{host}"

    return ""


TEST_SMTP_INBOX_DIR = Path(os.environ.get("TEST_SMTP_INBOX_DIR", str(_default_smtp_inbox_dir())))
APP_BASE_URL = _default_app_base_url()
