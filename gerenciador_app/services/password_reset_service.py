from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from gerenciador_app.config import PASSWORD_RESET_EXPIRATION_SECONDS, PASSWORD_RESET_SALT, SECRET_KEY
from gerenciador_app.services.email_service import enviar_email
from gerenciador_app.services.user_service import buscar_usuario_por_email, buscar_usuario_por_id


def _get_serializer():
    return URLSafeTimedSerializer(SECRET_KEY)


def gerar_token_recuperacao(usuario):
    serializer = _get_serializer()
    return serializer.dumps(
        {
            "user_id": usuario["id"],
            "email": usuario["email"],
        },
        salt=PASSWORD_RESET_SALT,
    )


def validar_token_recuperacao(token):
    serializer = _get_serializer()

    try:
        payload = serializer.loads(
            token,
            salt=PASSWORD_RESET_SALT,
            max_age=PASSWORD_RESET_EXPIRATION_SECONDS,
        )
    except SignatureExpired as exc:
        raise ValueError("O link de recuperação expirou. Solicite um novo e-mail.") from exc
    except BadSignature as exc:
        raise ValueError("O link de recuperação é inválido.") from exc

    usuario = buscar_usuario_por_id(payload["user_id"])
    if usuario is None or usuario["email"] != payload["email"]:
        raise ValueError("O link de recuperação é inválido.")

    return usuario


def enviar_email_recuperacao(email_destino, reset_link):
    usuario = buscar_usuario_por_email(email_destino)
    if usuario is None:
        return False

    assunto = "Recuperação de senha - Gerenciador de produto"
    mensagem = "\n".join(
        [
            f"Olá, {usuario['nome']}.",
            "",
            "Recebemos uma solicitação para redefinir sua senha no Gerenciador de produto.",
            "Use o link abaixo para cadastrar uma nova senha:",
            reset_link,
            "",
            f"Este link expira em {PASSWORD_RESET_EXPIRATION_SECONDS // 60} minuto(s).",
            "Se você não solicitou a alteração, ignore este e-mail.",
        ]
    )
    mensagem_html = f"""
    <html>
        <body>
            <p>Olá, {usuario['nome']}.</p>
            <p>Recebemos uma solicitação para redefinir sua senha no Gerenciador de produto.</p>
            <p>
                Clique no link abaixo para cadastrar uma nova senha:<br>
                <a href="{reset_link}">{reset_link}</a>
            </p>
            <p>Este link expira em {PASSWORD_RESET_EXPIRATION_SECONDS // 60} minuto(s).</p>
            <p>Se você não solicitou a alteração, ignore este e-mail.</p>
        </body>
    </html>
    """.strip()

    enviar_email(usuario["email"], assunto, mensagem, html_body=mensagem_html)
    return True

