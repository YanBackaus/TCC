import secrets

from flask import abort, flash, request, session
from markupsafe import Markup, escape


CSRF_SESSION_KEY = "_csrf_token"


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token

    return token


def csrf_token_field():
    return Markup(
        '<input type="hidden" name="csrf_token" value="{}">'.format(
            escape(get_csrf_token())
        )
    )


def validate_csrf_token():
    if request.method != "POST":
        return

    expected_token = session.get(CSRF_SESSION_KEY)
    submitted_token = request.form.get("csrf_token", "")
    if not expected_token or not secrets.compare_digest(expected_token, submitted_token):
        abort(400)


def validate_required_fields(required_fields):
    form_data = {}

    for field_name, label in required_fields:
        value = request.form.get(field_name, "").strip()
        if not value:
            flash(f"{label} é obrigatório.")
            return None
        form_data[field_name] = value

    return form_data
