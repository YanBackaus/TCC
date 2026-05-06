from flask import session


def set_current_page(page_name):
    session["pagina"] = page_name


def ensure_public_session_defaults():
    session.setdefault("tipo", 0)


def log_in_user(usuario):
    if isinstance(usuario, dict):
        session["usuario_id"] = usuario["id"]
        session["tipo"] = usuario["tipo"]
        session["precisa_trocar_senha"] = bool(usuario.get("precisa_trocar_senha"))
        return

    session["usuario_id"] = usuario[0]
    session["tipo"] = usuario[4]
    session["precisa_trocar_senha"] = False
