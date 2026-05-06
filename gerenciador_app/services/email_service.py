import smtplib
from email.message import EmailMessage

from gerenciador_app.services.settings_service import get_email_settings


def _build_email_message(to_email, subject, body, sender, html_body=None):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    return message


def enviar_email(to_email, subject, body, html_body=None):
    settings = get_email_settings()

    if settings["mail_suppress_send"]:
        print(f"EMAIL_SUPPRESSED to={to_email} subject={subject}")
        return

    if not settings["mail_server"]:
        raise ValueError("O envio de e-mail não está configurado no sistema.")

    message = _build_email_message(
        to_email,
        subject,
        body,
        settings["mail_default_sender"],
        html_body=html_body,
    )

    if settings["mail_use_ssl"]:
        with smtplib.SMTP_SSL(settings["mail_server"], settings["mail_port"]) as server:
            if settings["mail_username"]:
                server.login(settings["mail_username"], settings["mail_password"])
            server.send_message(message)
        return

    with smtplib.SMTP(settings["mail_server"], settings["mail_port"]) as server:
        if settings["mail_use_tls"]:
            server.starttls()
        if settings["mail_username"]:
            server.login(settings["mail_username"], settings["mail_password"])
        server.send_message(message)
