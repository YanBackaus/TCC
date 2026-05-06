from gerenciador_app.config import ADMIN_TYPE, STANDARD_USER_TYPE
from gerenciador_app.repositories.user_repository import (
    create_user,
    email_exists,
    get_user_by_email,
    get_user_by_id,
    get_user_password_by_id,
    list_users,
    set_temporary_password,
    update_password,
    update_user_status,
    update_user,
)
from gerenciador_app.services.auth_service import criptografar_senha
from gerenciador_app.services.auth_service import gerar_senha_temporaria
from gerenciador_app.services.input_validation_service import validate_against_sql_injection


USER_TYPE_LABELS = {
    STANDARD_USER_TYPE: "Usuário padrão",
    ADMIN_TYPE: "Administrador",
}


def _normalize_user_type(user_type, default_type=STANDARD_USER_TYPE):
    if user_type in (None, ""):
        return default_type

    try:
        parsed_type = int(str(user_type).strip())
    except (TypeError, ValueError):
        raise ValueError("O tipo de usuário informado é inválido.")

    if parsed_type not in USER_TYPE_LABELS:
        raise ValueError("O tipo de usuário informado é inválido.")

    return parsed_type


def listar_tipos_usuario():
    return [
        {"value": user_type, "label": label}
        for user_type, label in USER_TYPE_LABELS.items()
    ]


def listar_usuarios_filtrados(show_inactive=False, search=None):
    status = 0 if show_inactive else 1
    usuarios = list_users(status=status, search=search)

    for usuario in usuarios:
        usuario["status_label"] = "Inativo" if usuario["status"] == 0 else "Ativo"
        usuario["tipo_label"] = USER_TYPE_LABELS.get(usuario["tipo"], "Desconhecido")
        usuario["senha_provisoria_label"] = "Primeiro acesso" if usuario["precisa_trocar_senha"] else "Definida"

    return usuarios


def buscar_usuario_por_id(user_id):
    return get_user_by_id(user_id)


def buscar_usuario_por_email(email):
    return get_user_by_email(email)


def email_ja_cadastrado(email, ignored_user_id=None):
    return email_exists(email, ignored_user_id=ignored_user_id)


def criar_usuario(nome, email, senha=None, user_type=None):
    validate_against_sql_injection(nome, email)
    normalized_user_type = _normalize_user_type(user_type)
    temporary_password = None
    password_to_store = senha
    must_change_password = 0

    if not password_to_store:
        temporary_password = gerar_senha_temporaria()
        password_to_store = temporary_password
        must_change_password = 1

    password_hash = criptografar_senha(password_to_store)
    user_id = create_user(
        nome=nome,
        email=email,
        password_hash=password_hash,
        user_type=normalized_user_type,
        status=1,
        must_change_password=must_change_password,
    )
    cadastro = {"id": user_id}
    if temporary_password is not None:
        cadastro["senha_temporaria"] = temporary_password
    return cadastro


def atualizar_usuario(user_id, nome, email, senha, user_type, require_password_reset=False):
    validate_against_sql_injection(nome, email)
    normalized_user_type = _normalize_user_type(user_type, default_type=ADMIN_TYPE)
    senha_atual = get_user_password_by_id(user_id)
    usuario = get_user_by_id(user_id)
    if senha_atual is None or usuario is None:
        raise ValueError("Usuário não encontrado.")

    password_hash = senha_atual["senha"]
    must_change_password = usuario["precisa_trocar_senha"]
    if senha:
        password_hash = criptografar_senha(senha)
        must_change_password = 1 if require_password_reset else 0

    update_user(user_id, nome, email, password_hash, normalized_user_type, must_change_password)


def desativar_usuario(user_id):
    update_user_status(user_id, 0)


def ativar_usuario(user_id):
    update_user_status(user_id, 1)


def atualizar_senha(user_id, senha):
    update_password(user_id, criptografar_senha(senha))


def gerar_nova_senha_provisoria(user_id):
    usuario = get_user_by_id(user_id)
    if usuario is None:
        raise ValueError("Usuário não encontrado.")

    temporary_password = gerar_senha_temporaria()
    set_temporary_password(user_id, criptografar_senha(temporary_password))

    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "senha_temporaria": temporary_password,
    }
