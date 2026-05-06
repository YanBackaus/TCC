import os
import secrets
from pathlib import Path


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
APP_ENV = os.environ.get("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV in {"prod", "production"}

SERVER_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
}

DATABASE_NAME = os.environ.get("DB_NAME", "Gerenciador")
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
TEST_SMTP_INBOX_DIR = Path(os.environ.get("TEST_SMTP_INBOX_DIR", str(BASE_DIR / ".smtp-test-inbox")))
APP_BASE_URL = os.environ.get("APP_BASE_URL", "")

