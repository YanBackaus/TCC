import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from gerenciador_app.repositories.user_repository import get_user_auth_by_email, update_password


HASH_PREFIXES = ("scrypt:", "pbkdf2:")


def criptografar_senha(senha):
    return generate_password_hash(senha)


def senha_criptografada(senha):
    return isinstance(senha, str) and senha.startswith(HASH_PREFIXES)


def gerar_senha_temporaria():
    return f"ROHR-{secrets.token_hex(3).upper()}"


def autenticar_usuario(email, senha):
    usuario = get_user_auth_by_email(email)
    if usuario is None or usuario["status"] != 1:
        return None

    senha_salva = usuario["senha"]
    if senha_criptografada(senha_salva):
        if not check_password_hash(senha_salva, senha):
            return None
    else:
        if senha_salva != senha:
            return None
        update_password(usuario["id"], criptografar_senha(senha))

    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "tipo": usuario["tipo"],
        "status": usuario["status"],
        "precisa_trocar_senha": bool(usuario.get("precisa_trocar_senha")),
    }
