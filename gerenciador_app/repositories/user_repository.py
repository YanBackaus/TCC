from gerenciador_app.db import execute, fetch_all, fetch_one


def list_users(status=None, search=None):
    query = """
        SELECT id, nome, email, tipo, status, precisa_trocar_senha
        FROM usuarios
        WHERE 1 = 1
    """
    params = []

    if status is not None:
        query += " AND status = %s"
        params.append(status)

    if search:
        query += " AND (nome LIKE %s OR email LIKE %s)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    query += " ORDER BY nome;"

    return fetch_all(query, tuple(params), dictionary=True)


def get_user_by_id(user_id):
    return fetch_one(
        """
        SELECT id, nome, email, tipo, status, precisa_trocar_senha
        FROM usuarios
        WHERE id = %s;
        """,
        (user_id,),
        dictionary=True,
    )


def get_user_by_email(email):
    return fetch_one(
        """
        SELECT id, nome, email, tipo, status, precisa_trocar_senha
        FROM usuarios
        WHERE email = %s;
        """,
        (email,),
        dictionary=True,
    )


def get_user_auth_by_email(email):
    return fetch_one(
        """
        SELECT id, nome, email, senha, tipo, status, precisa_trocar_senha
        FROM usuarios
        WHERE email = %s;
        """,
        (email,),
        dictionary=True,
    )


def get_user_password_by_id(user_id):
    return fetch_one(
        """
        SELECT senha
        FROM usuarios
        WHERE id = %s;
        """,
        (user_id,),
        dictionary=True,
    )


def email_exists(email, ignored_user_id=None):
    query = "SELECT id FROM usuarios WHERE email = %s"
    params = [email]

    if ignored_user_id is not None:
        query += " AND id <> %s"
        params.append(ignored_user_id)

    query += ";"

    return fetch_one(query, tuple(params)) is not None


def create_user(nome, email, password_hash, user_type, status, must_change_password):
    return execute(
        """
        INSERT INTO usuarios (nome, email, senha, tipo, status, precisa_trocar_senha)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (nome, email, password_hash, user_type, status, must_change_password),
    )


def update_user(user_id, nome, email, password_hash, user_type, must_change_password):
    execute(
        """
        UPDATE usuarios
        SET nome = %s, email = %s, senha = %s, tipo = %s, precisa_trocar_senha = %s
        WHERE id = %s;
        """,
        (nome, email, password_hash, user_type, must_change_password, user_id),
    )


def update_user_status(user_id, status):
    execute(
        """
        UPDATE usuarios
        SET status = %s
        WHERE id = %s;
        """,
        (status, user_id),
    )


def update_password(user_id, password_hash):
    execute(
        """
        UPDATE usuarios
        SET senha = %s, precisa_trocar_senha = 0
        WHERE id = %s;
        """,
        (password_hash, user_id),
    )


def set_temporary_password(user_id, password_hash):
    execute(
        """
        UPDATE usuarios
        SET senha = %s, precisa_trocar_senha = 1
        WHERE id = %s;
        """,
        (password_hash, user_id),
    )
