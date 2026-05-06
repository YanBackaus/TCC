from gerenciador_app.config import (
    APP_BASE_URL,
    MAIL_DEFAULT_SENDER,
    MAIL_PASSWORD,
    MAIL_PORT,
    MAIL_SERVER,
    MAIL_SUPPRESS_SEND,
    MAIL_USERNAME,
    MAIL_USE_SSL,
    MAIL_USE_TLS,
    PURCHASE_DEPARTMENT_EMAIL,
)
from gerenciador_app.repositories.settings_repository import list_settings, upsert_setting


EMAIL_SETTING_KEYS = {
    "app_base_url": APP_BASE_URL,
    "purchase_department_email": PURCHASE_DEPARTMENT_EMAIL,
    "mail_server": MAIL_SERVER,
    "mail_port": str(MAIL_PORT),
    "mail_use_tls": "1" if MAIL_USE_TLS else "0",
    "mail_use_ssl": "1" if MAIL_USE_SSL else "0",
    "mail_username": MAIL_USERNAME,
    "mail_password": MAIL_PASSWORD,
    "mail_default_sender": MAIL_DEFAULT_SENDER,
    "mail_suppress_send": "1" if MAIL_SUPPRESS_SEND else "0",
}


def _settings_map():
    persisted = {
        row["setting_key"]: row["setting_value"]
        for row in list_settings()
    }
    return {**EMAIL_SETTING_KEYS, **persisted}


def get_email_settings():
    settings_map = _settings_map()
    return {
        "app_base_url": settings_map["app_base_url"],
        "purchase_department_email": settings_map["purchase_department_email"],
        "mail_server": settings_map["mail_server"],
        "mail_port": int(settings_map["mail_port"] or 0),
        "mail_use_tls": settings_map["mail_use_tls"] == "1",
        "mail_use_ssl": settings_map["mail_use_ssl"] == "1",
        "mail_username": settings_map["mail_username"],
        "mail_password": settings_map["mail_password"],
        "mail_default_sender": settings_map["mail_default_sender"],
        "mail_suppress_send": settings_map["mail_suppress_send"] == "1",
    }


def get_email_settings_form_data():
    settings_map = get_email_settings()
    return {
        "app_base_url": settings_map["app_base_url"],
        "purchase_department_email": settings_map["purchase_department_email"],
        "mail_server": settings_map["mail_server"],
        "mail_port": str(settings_map["mail_port"]),
        "mail_use_tls": settings_map["mail_use_tls"],
        "mail_use_ssl": settings_map["mail_use_ssl"],
        "mail_username": settings_map["mail_username"],
        "mail_password": "",
        "mail_password_configured": bool(settings_map["mail_password"]),
        "mail_default_sender": settings_map["mail_default_sender"],
        "mail_suppress_send": settings_map["mail_suppress_send"],
    }


def get_purchase_department_email():
    return get_email_settings()["purchase_department_email"]


def get_app_base_url():
    return get_email_settings()["app_base_url"].rstrip("/")


def salvar_configuracoes_email(form_data):
    app_base_url = form_data.get("app_base_url", "").strip()
    mail_server = form_data.get("mail_server", "").strip()
    purchase_department_email = form_data.get("purchase_department_email", "").strip()
    mail_username = form_data.get("mail_username", "").strip()
    mail_default_sender = form_data.get("mail_default_sender", "").strip()
    mail_password = form_data.get("mail_password", "")

    if purchase_department_email and "@" not in purchase_department_email:
        raise ValueError("Informe um e-mail válido para o setor de compras.")
    if app_base_url and not (app_base_url.startswith("http://") or app_base_url.startswith("https://")):
        raise ValueError("A URL base do sistema deve começar com http:// ou https://.")
    if mail_default_sender and "@" not in mail_default_sender:
        raise ValueError("Informe um remetente padrão válido.")
    if mail_username and "@" not in mail_username:
        raise ValueError("Informe um usuário de e-mail válido.")

    try:
        mail_port = int(str(form_data.get("mail_port", "")).strip())
    except (TypeError, ValueError):
        raise ValueError("A porta do servidor deve ser um numero inteiro.")

    if mail_port <= 0:
        raise ValueError("A porta do servidor deve ser maior que zero.")

    current = get_email_settings()
    if mail_password == "":
        mail_password = current["mail_password"]

    normalized = {
        "app_base_url": app_base_url,
        "purchase_department_email": purchase_department_email,
        "mail_server": mail_server,
        "mail_port": str(mail_port),
        "mail_use_tls": "1" if form_data.get("mail_use_tls") else "0",
        "mail_use_ssl": "1" if form_data.get("mail_use_ssl") else "0",
        "mail_username": mail_username,
        "mail_password": mail_password,
        "mail_default_sender": mail_default_sender,
        "mail_suppress_send": "1" if form_data.get("mail_suppress_send") else "0",
    }

    if normalized["mail_use_tls"] == "1" and normalized["mail_use_ssl"] == "1":
        raise ValueError("Selecione TLS ou SSL, não os dois ao mesmo tempo.")

    for setting_key, setting_value in normalized.items():
        upsert_setting(setting_key, setting_value)

    return get_email_settings_form_data()
