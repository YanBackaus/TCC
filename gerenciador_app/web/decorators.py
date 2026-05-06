from functools import wraps

from flask import flash, redirect, request, session, url_for

from gerenciador_app.config import ADMIN_TYPE
from gerenciador_app.services.user_service import buscar_usuario_por_id


def _get_authenticated_user():
    if not session.get("usuario_id"):
        return None

    usuario = buscar_usuario_por_id(session["usuario_id"])
    if usuario is None or usuario["status"] != 1:
        session.clear()
        return None

    session["tipo"] = usuario["tipo"]
    session["precisa_trocar_senha"] = bool(usuario.get("precisa_trocar_senha"))
    return usuario


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if _get_authenticated_user() is None:
            return redirect(url_for("pagina_login"))
        if session.get("precisa_trocar_senha") and request.endpoint not in {"primeiro_acesso", "logout"}:
            flash("Você precisa definir uma nova senha antes de continuar.")
            return redirect(url_for("primeiro_acesso"))

        return view_function(*args, **kwargs)

    return wrapped_view


def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        usuario = _get_authenticated_user()
        if usuario is None:
            return redirect(url_for("pagina_login"))
        if session.get("precisa_trocar_senha"):
            flash("Você precisa definir uma nova senha antes de continuar.")
            return redirect(url_for("primeiro_acesso"))
        if usuario["tipo"] != ADMIN_TYPE:
            flash("Apenas administradores podem acessar essa área.")
            return redirect(url_for("pagina_inicial"))

        return view_function(*args, **kwargs)

    return wrapped_view
