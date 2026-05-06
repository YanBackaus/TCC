from io import BytesIO

from flask import flash, redirect, render_template, request, send_file, send_from_directory, session, url_for

from gerenciador_app.config import (
    ADMIN_TYPE,
    PAGE_CONFIGURACOES,
    PAGE_EPI,
    PAGE_ESTOQUE,
    PAGE_INICIAL,
    PAGE_MOVIMENTACOES,
    PAGE_PERFIL,
    PAGE_SOLICITACOES,
    PAGE_USUARIOS,
)
from gerenciador_app.services.auth_service import autenticar_usuario
from gerenciador_app.services.catalog_service import (
    ativar_epi,
    cadastrar_epi,
    concluir_pedido_com_entrada,
    desativar_epi,
    editar_epi,
    editar_estoque,
    encerrar_pedido_sem_entrada,
    fazer_pedido,
    listar_epis,
    listar_logs_detalhados,
    listar_estoque,
    listar_pedidos_detalhados,
    listar_pedidos_abertos_por_epi,
    listar_logs_recentes,
    listar_pedidos_recentes,
    montar_dashboard_estoque,
    obter_epi,
    obter_estoque,
    obter_pedido_aberto_para_entrada,
    preparar_solicitacao_compra,
    registrar_estoque,
    retirar_estoque,
)
from gerenciador_app.services.password_reset_service import (
    enviar_email_recuperacao,
    gerar_token_recuperacao,
    validar_token_recuperacao,
)
from gerenciador_app.services.export_service import (
    build_movimentacoes_pdf,
    build_movimentacoes_xlsx,
    build_solicitacoes_pdf,
    build_solicitacoes_xlsx,
    export_filename,
)
from gerenciador_app.services.session_service import (
    ensure_public_session_defaults,
    log_in_user,
    set_current_page,
)
from gerenciador_app.services.settings_service import (
    get_app_base_url,
    get_email_settings_form_data,
    salvar_configuracoes_email,
)
from gerenciador_app.services.smtp_test_inbox_service import (
    listar_emails_teste,
    obter_email_teste,
)
from gerenciador_app.services.user_service import (
    ativar_usuario,
    atualizar_senha,
    atualizar_usuario,
    buscar_usuario_por_email,
    buscar_usuario_por_id,
    criar_usuario,
    desativar_usuario,
    email_ja_cadastrado,
    gerar_nova_senha_provisoria,
    listar_usuarios_filtrados,
    listar_tipos_usuario,
)
from gerenciador_app.web.decorators import admin_required, login_required
from gerenciador_app.web.forms import validate_required_fields


def render_login_page():
    return render_template("login.html")


def ensure_admin_for_managed_user_flow():
    if not session.get("usuario_id"):
        return None

    usuario = buscar_usuario_por_id(session["usuario_id"])
    if usuario is None or usuario["status"] != 1:
        session.clear()
        return redirect(url_for("pagina_login"))

    session["tipo"] = usuario["tipo"]
    session["precisa_trocar_senha"] = bool(usuario.get("precisa_trocar_senha"))
    if session.get("precisa_trocar_senha"):
        flash("Você precisa definir uma nova senha antes de continuar.")
        return redirect(url_for("primeiro_acesso"))
    if usuario["tipo"] != ADMIN_TYPE:
        flash("Apenas administradores podem gerenciar usuários.")
        return redirect(url_for("pagina_inicial"))

    return None


def render_cadastro_page(form_data=None):
    ensure_public_session_defaults()
    return render_template(
        "cadastroUsuarios.html",
        form_data=form_data or {},
        pode_escolher_tipo=bool(session.get("usuario_id")),
        tipos_usuario=listar_tipos_usuario(),
    )


def render_cadastro_epi_page(form_data=None):
    set_current_page(PAGE_EPI)
    return render_template("cadastroEpi.html", form_data=form_data or {})


def render_configuracoes_page(form_data=None):
    set_current_page(PAGE_CONFIGURACOES)
    return render_template("configuracoes.html", form_data=form_data or get_email_settings_form_data())


def render_emails_teste_page(selected_email=None):
    set_current_page(PAGE_CONFIGURACOES)
    return render_template(
        "emailsTeste.html",
        emails=listar_emails_teste(),
        selected_email=selected_email,
    )


def render_editar_epi_page(epi, form_data=None):
    set_current_page(PAGE_EPI)
    dados_epi = form_data or epi
    return render_template("editarEpi.html", dados_epi=dados_epi, epi_id=epi["id"])


def render_registrar_estoque_page(epi, form_data=None, pedido_relacionado=None, pedidos_disponiveis=None):
    set_current_page(PAGE_ESTOQUE)
    pedidos_disponiveis = pedidos_disponiveis if pedidos_disponiveis is not None else listar_pedidos_abertos_por_epi(epi["id"])
    normalized_form_data = dict(form_data or {})

    if pedido_relacionado is not None and not normalized_form_data.get("quantidade"):
        normalized_form_data["quantidade"] = str(pedido_relacionado["quantidade"])
    if pedido_relacionado is not None and not normalized_form_data.get("pedido_id"):
        normalized_form_data["pedido_id"] = str(pedido_relacionado["id"])

    return render_template(
        "registrarEstoque.html",
        epi=epi,
        form_data=normalized_form_data,
        pedido_relacionado=pedido_relacionado,
        pedidos_disponiveis=pedidos_disponiveis,
    )


def render_editar_estoque_page(estoque, form_data=None):
    set_current_page(PAGE_ESTOQUE)
    return render_template("editarEstoque.html", estoque=estoque, form_data=form_data or {})


def render_retirar_estoque_page(estoque, form_data=None):
    set_current_page(PAGE_ESTOQUE)
    return render_template("retirarEstoque.html", estoque=estoque, form_data=form_data or {})


def render_fazer_pedido_page(epi, form_data=None, pedido_email=None, pedido_pendente=False):
    set_current_page(PAGE_ESTOQUE)
    return render_template(
        "fazerPedido.html",
        epi=epi,
        form_data=form_data or {},
        pedido_email=pedido_email,
        pedido_pendente=pedido_pendente,
    )


def render_esqueci_senha_page():
    ensure_public_session_defaults()
    return render_template("esquecisenha.html")


def render_mudar_senha_page(reset_token):
    ensure_public_session_defaults()
    return render_template(
        "mudarsenha.html",
        reset_token=reset_token,
        is_first_access=False,
    )


def render_primeiro_acesso_page():
    return render_template("mudarsenha.html", reset_token=None, is_first_access=True)


def render_senha_provisoria_page(cadastro, back_endpoint, back_label):
    return render_template(
        "senhaProvisoria.html",
        cadastro=cadastro,
        back_endpoint=back_endpoint,
        back_label=back_label,
    )


def render_editar_usuario_page(user_id, usuario, can_edit_type, is_own_profile, form_data=None):
    set_current_page(PAGE_PERFIL if is_own_profile else PAGE_USUARIOS)
    return render_template(
        "editarusuario.html",
        id=user_id,
        dados_usuario=form_data or usuario,
        tipos_usuario=listar_tipos_usuario() if can_edit_type else [],
        can_edit_type=can_edit_type,
        is_own_profile=is_own_profile,
    )


def render_estoque_dashboard():
    search = request.args.get("busca", "").strip()
    produtos = listar_estoque(search=search)
    dashboard = montar_dashboard_estoque()
    logs_recentes = listar_logs_recentes()
    pedidos_recentes = listar_pedidos_recentes()
    return render_template(
        "estoque.html",
        produtos=produtos,
        logs=logs_recentes,
        pedidos=pedidos_recentes,
        notificacoes=dashboard["notificacoes_reposicao"],
        search=search,
    )


def render_registro_movimentacoes_page():
    set_current_page(PAGE_MOVIMENTACOES)
    search = request.args.get("busca", "").strip()
    logs = listar_logs_detalhados(search=search)
    return render_template(
        "registroMovimentacoes.html",
        logs=logs,
        search=search,
    )


def render_registro_solicitacoes_page():
    set_current_page(PAGE_SOLICITACOES)
    search = request.args.get("busca", "").strip()
    pedidos = listar_pedidos_detalhados(search=search)
    return render_template(
        "registroSolicitacoes.html",
        pedidos=pedidos,
        search=search,
    )


def register_routes(app):
    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")

    @app.route("/", methods=["GET"])
    def pagina_login():
        if session.get("usuario_id"):
            if session.get("precisa_trocar_senha"):
                return redirect(url_for("primeiro_acesso"))
            return redirect(url_for("pagina_inicial"))
        return render_login_page()

    @app.route("/logout", methods=["GET"])
    def logout():
        session.clear()
        return redirect(url_for("pagina_login"))

    @app.route("/paginainicial")
    @login_required
    def pagina_inicial():
        set_current_page(PAGE_INICIAL)
        return render_template("paginainicial.html", dashboard=montar_dashboard_estoque())

    @app.route("/epi")
    @login_required
    def pagina_epi():
        set_current_page(PAGE_EPI)
        search = request.args.get("busca", "").strip()
        produtos = listar_epis(search=search)
        return render_template("epi.html", produtos=produtos, search=search)

    @app.route("/estoque")
    @login_required
    def pagina_estoque():
        set_current_page(PAGE_ESTOQUE)
        return render_estoque_dashboard()

    @app.route("/registro-movimentacoes")
    @login_required
    def pagina_registro_movimentacoes():
        return render_registro_movimentacoes_page()

    @app.route("/registro-movimentacoes/exportar/excel")
    @login_required
    def exportar_registro_movimentacoes_excel():
        search = request.args.get("busca", "").strip()
        logs = listar_logs_detalhados(search=search)
        report = build_movimentacoes_xlsx(logs)
        return send_file(
            BytesIO(report),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=export_filename("xlsx"),
        )

    @app.route("/registro-movimentacoes/exportar/pdf")
    @login_required
    def exportar_registro_movimentacoes_pdf():
        search = request.args.get("busca", "").strip()
        logs = listar_logs_detalhados(search=search)
        report = build_movimentacoes_pdf(logs)
        return send_file(
            BytesIO(report),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=export_filename("pdf"),
        )

    @app.route("/registro-solicitacoes")
    @login_required
    def pagina_registro_solicitacoes():
        return render_registro_solicitacoes_page()

    @app.route("/registro-solicitacoes/exportar/excel")
    @login_required
    def exportar_registro_solicitacoes_excel():
        search = request.args.get("busca", "").strip()
        pedidos = listar_pedidos_detalhados(search=search)
        report = build_solicitacoes_xlsx(pedidos)
        return send_file(
            BytesIO(report),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=export_filename("xlsx", prefix="registro-solicitacoes"),
        )

    @app.route("/registro-solicitacoes/exportar/pdf")
    @login_required
    def exportar_registro_solicitacoes_pdf():
        search = request.args.get("busca", "").strip()
        pedidos = listar_pedidos_detalhados(search=search)
        report = build_solicitacoes_pdf(pedidos)
        return send_file(
            BytesIO(report),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=export_filename("pdf", prefix="registro-solicitacoes"),
        )

    @app.route("/usuarios")
    @admin_required
    def pagina_usuarios():
        set_current_page(PAGE_USUARIOS)
        show_inactive = request.args.get("status") == "inativos"
        search = request.args.get("busca", "").strip()

        return render_template(
            "usuarios.html",
            usuarios=listar_usuarios_filtrados(show_inactive=show_inactive, search=search),
            show_inactive=show_inactive,
            search=search,
        )

    @app.route("/configuracoes", methods=["GET", "POST"])
    @admin_required
    def pagina_configuracoes():
        if request.method == "POST":
            form_data = {
                "app_base_url": request.form.get("app_base_url", "").strip(),
                "purchase_department_email": request.form.get("purchase_department_email", "").strip(),
                "mail_server": request.form.get("mail_server", "").strip(),
                "mail_port": request.form.get("mail_port", "").strip(),
                "mail_use_tls": request.form.get("mail_use_tls"),
                "mail_use_ssl": request.form.get("mail_use_ssl"),
                "mail_username": request.form.get("mail_username", "").strip(),
                "mail_password": request.form.get("mail_password", ""),
                "mail_default_sender": request.form.get("mail_default_sender", "").strip(),
                "mail_suppress_send": request.form.get("mail_suppress_send"),
            }

            try:
                saved_form_data = salvar_configuracoes_email(form_data)
            except ValueError as error:
                flash(str(error))
                fallback_data = {
                    **form_data,
                    "mail_password": "",
                    "mail_password_configured": get_email_settings_form_data()["mail_password_configured"],
                    "mail_use_tls": bool(form_data.get("mail_use_tls")),
                    "mail_use_ssl": bool(form_data.get("mail_use_ssl")),
                    "mail_suppress_send": bool(form_data.get("mail_suppress_send")),
                }
                return render_configuracoes_page(form_data=fallback_data)

            flash("Configurações de e-mail atualizadas com sucesso.")
            return render_configuracoes_page(form_data=saved_form_data)

        return render_configuracoes_page()

    @app.route("/configuracoes/emails-teste", methods=["GET"])
    @admin_required
    def pagina_emails_teste():
        return render_emails_teste_page()

    @app.route("/configuracoes/emails-teste/<path:filename>", methods=["GET"])
    @admin_required
    def detalhe_email_teste(filename):
        try:
            selected_email = obter_email_teste(filename)
        except ValueError:
            flash("E-mail de teste inválido.")
            return redirect(url_for("pagina_emails_teste"))

        if selected_email is None:
            flash("E-mail de teste não encontrado.")
            return redirect(url_for("pagina_emails_teste"))

        return render_emails_teste_page(selected_email=selected_email)

    @app.route("/cadastro", methods=["GET", "POST"])
    def abre_cadastro():
        admin_guard = ensure_admin_for_managed_user_flow()
        if admin_guard is not None:
            return admin_guard
        return render_cadastro_page()

    @app.route("/meu-perfil", methods=["GET"])
    @login_required
    def meu_perfil():
        return redirect(url_for("atualizar_usuario", user_id=session["usuario_id"]))

    @app.route("/add_cadastro_usuarios", methods=["POST"])
    def cadastro_usuario():
        admin_guard = ensure_admin_for_managed_user_flow()
        if admin_guard is not None:
            return admin_guard

        form_data = validate_required_fields(
            [
                ("nome", "O nome"),
                ("email", "O e-mail"),
                ("senha", "A senha"),
            ]
        )
        if form_data is None:
            return render_cadastro_page(
                form_data={
                    "nome": request.form.get("nome", "").strip(),
                    "email": request.form.get("email", "").strip(),
                    "tipo": request.form.get("tipo", ""),
                }
            )

        if email_ja_cadastrado(form_data["email"]):
            flash("E-mail já cadastrado.")
            return render_cadastro_page(form_data={**form_data, "tipo": request.form.get("tipo", "")})

        user_type = request.form.get("tipo") if session.get("usuario_id") else None

        try:
            criar_usuario(
                nome=form_data["nome"],
                email=form_data["email"],
                senha=form_data["senha"],
                user_type=user_type,
            )
        except ValueError as error:
            flash(str(error))
            return render_cadastro_page(form_data={**form_data, "tipo": user_type})

        if session.get("usuario_id"):
            flash("Usuário cadastrado com sucesso.")
            return redirect(url_for("pagina_usuarios"))

        flash("Conta criada com sucesso.")
        return redirect(url_for("pagina_login"))

    @app.route("/cadastro_epi", methods=["GET"])
    @admin_required
    def abre_cadastro_epi():
        return render_cadastro_epi_page()

    @app.route("/add_cadastro_epi", methods=["POST"])
    @admin_required
    def cadastro_epi_route():
        form_data = validate_required_fields(
            [
                ("nome", "O nome"),
                ("tipo", "O tipo"),
                ("descricao", "A descrição"),
            ]
        )
        if form_data is None:
            return render_cadastro_epi_page()

        try:
            cadastrar_epi(
                nome=form_data["nome"],
                tipo=form_data["tipo"],
                descricao=form_data["descricao"],
                quantidade_min=request.form.get("quantidadeMin", "").strip(),
                ca=request.form.get("ca", "").strip(),
                quantidade_estoque=request.form.get("quantidadeEstoque", "").strip(),
                user_id=session.get("usuario_id"),
            )
        except ValueError as error:
            flash(str(error))
            return render_cadastro_epi_page(form_data=form_data)

        flash("Produto registrado com sucesso.")
        return redirect(url_for("pagina_epi"))

    @app.route("/editar_epi/<int:epi_id>", methods=["GET", "POST"])
    @admin_required
    def editar_epi_route(epi_id):
        epi = obter_epi(epi_id)
        if epi is None:
            flash("Produto não encontrado.")
            return redirect(url_for("pagina_epi"))

        if request.method == "POST":
            form_data = validate_required_fields(
                [
                    ("nome", "O nome"),
                    ("tipo", "O tipo"),
                    ("descricao", "A descrição"),
                    ("status", "O status"),
                ]
            )
            if form_data is None:
                return render_editar_epi_page(epi)

            try:
                editar_epi(
                    epi_id=epi_id,
                    nome=form_data["nome"],
                    tipo=form_data["tipo"],
                    descricao=form_data["descricao"],
                    quantidade_min=request.form.get("quantidadeMin", "").strip(),
                    ca=request.form.get("ca", "").strip(),
                    status=form_data["status"],
                )
            except ValueError as error:
                flash(str(error))
                return render_editar_epi_page(epi, form_data={**epi, **form_data})

            flash("Produto atualizado com sucesso.")
            return redirect(url_for("pagina_epi"))

        return render_editar_epi_page(epi)

    @app.route("/ativar_epi/<int:epi_id>", methods=["POST"])
    @admin_required
    def ativar_epi_route(epi_id):
        try:
            ativar_epi(epi_id)
            flash("Produto ativado com sucesso.")
        except ValueError as error:
            flash(str(error))
        return redirect(url_for("pagina_epi"))

    @app.route("/desativar_epi/<int:epi_id>", methods=["POST"])
    @admin_required
    def desativar_epi_route(epi_id):
        try:
            desativar_epi(epi_id)
            flash("Produto desativado com sucesso.")
        except ValueError as error:
            flash(str(error))
        return redirect(url_for("pagina_epi"))

    @app.route("/registrar_estoque/<int:epi_id>", methods=["GET", "POST"])
    @login_required
    def registrar_estoque_route(epi_id):
        epi = obter_epi(epi_id)
        if epi is None:
            flash("Produto não encontrado.")
            return redirect(url_for("pagina_estoque"))
        if not epi["status"]:
            flash("Produto inativo não pode receber movimentacao de estoque.")
            return redirect(url_for("pagina_estoque"))

        pedidos_disponiveis = listar_pedidos_abertos_por_epi(epi_id)
        pedido_id = request.args.get("pedido_id", "").strip()
        if request.method == "POST":
            pedido_id = request.form.get("pedido_id", pedido_id).strip()

        pedido_relacionado = None
        pedido_invalido = False
        if pedido_id:
            try:
                pedido_relacionado = obter_pedido_aberto_para_entrada(int(pedido_id), epi_id)
            except ValueError as error:
                flash(str(error))
                pedido_invalido = True
                pedido_id = ""

        if request.method == "POST":
            if pedido_invalido:
                return render_registrar_estoque_page(
                    epi,
                    form_data={
                        "pedido_id": "",
                        "quantidade": request.form.get("quantidade", "").strip(),
                    },
                    pedido_relacionado=None,
                    pedidos_disponiveis=pedidos_disponiveis,
                )

            form_data = validate_required_fields([("quantidade", "A quantidade")])
            if form_data is None:
                return render_registrar_estoque_page(
                    epi,
                    form_data={
                        "pedido_id": pedido_id,
                        "quantidade": request.form.get("quantidade", "").strip(),
                    },
                    pedido_relacionado=pedido_relacionado,
                    pedidos_disponiveis=pedidos_disponiveis,
                )

            if pedido_relacionado is not None:
                try:
                    quantidade_informada = int(str(form_data["quantidade"]).strip())
                except (TypeError, ValueError):
                    quantidade_informada = None

                if quantidade_informada is not None and quantidade_informada < int(pedido_relacionado["quantidade"]):
                    flash(
                        "Para concluir a solicitação vinculada, registre uma quantidade igual ou maior do que a solicitada."
                    )
                    return render_registrar_estoque_page(
                        epi,
                        form_data={**form_data, "pedido_id": pedido_id},
                        pedido_relacionado=pedido_relacionado,
                        pedidos_disponiveis=pedidos_disponiveis,
                    )

            try:
                registrar_estoque(
                    epi_id,
                    form_data["quantidade"],
                    session["usuario_id"],
                )
            except ValueError as error:
                flash(str(error))
                return render_registrar_estoque_page(
                    epi,
                    form_data={
                        **form_data,
                        "pedido_id": pedido_id,
                    },
                    pedido_relacionado=pedido_relacionado,
                    pedidos_disponiveis=pedidos_disponiveis,
                )

            if pedido_relacionado is not None:
                concluir_pedido_com_entrada(pedido_relacionado["id"], epi_id)
                flash("Entrada registrada e solicitação concluída com sucesso.")
                return redirect(url_for("pagina_registro_solicitacoes"))

            flash("Estoque registrado com sucesso.")
            return redirect(url_for("pagina_estoque"))

        return render_registrar_estoque_page(
            epi,
            form_data={"pedido_id": pedido_id},
            pedido_relacionado=pedido_relacionado,
            pedidos_disponiveis=pedidos_disponiveis,
        )

    @app.route("/editar_estoque/<int:stock_id>", methods=["GET", "POST"])
    @admin_required
    def editar_estoque_route(stock_id):
        estoque = obter_estoque(stock_id)
        if estoque is None:
            flash("Estoque não encontrado.")
            return redirect(url_for("pagina_estoque"))
        if not estoque["epi_status"]:
            flash("Produto inativo não pode ter estoque editado.")
            return redirect(url_for("pagina_estoque"))

        if request.method == "POST":
            form_data = validate_required_fields([("quantidade", "A quantidade")])
            if form_data is None:
                return render_editar_estoque_page(estoque)

            try:
                editar_estoque(
                    stock_id,
                    form_data["quantidade"],
                    session["usuario_id"],
                    status=request.form.get("status", estoque["status"]),
                )
            except ValueError as error:
                flash(str(error))
                return render_editar_estoque_page(
                    estoque,
                    form_data={
                        **form_data,
                        "status": request.form.get("status", estoque["status"]),
                    },
                )

            flash("Estoque atualizado com sucesso.")
            return redirect(url_for("pagina_estoque"))

        return render_editar_estoque_page(estoque)

    @app.route("/retirar_estoque/<int:stock_id>", methods=["GET", "POST"])
    @login_required
    def retirar_estoque_route(stock_id):
        estoque = obter_estoque(stock_id)
        if estoque is None:
            flash("Estoque não encontrado.")
            return redirect(url_for("pagina_estoque"))
        if not estoque["epi_status"]:
            flash("Produto inativo não pode ter retirada de estoque.")
            return redirect(url_for("pagina_estoque"))
        if not estoque["status"]:
            flash("Estoque inativo não pode ter retirada registrada.")
            return redirect(url_for("pagina_estoque"))

        if request.method == "POST":
            form_data = validate_required_fields([("quantidade", "A quantidade")])
            if form_data is None:
                return render_retirar_estoque_page(estoque)

            try:
                notificacao = retirar_estoque(
                    stock_id,
                    form_data["quantidade"],
                    session["usuario_id"],
                )
            except ValueError as error:
                flash(str(error))
                return render_retirar_estoque_page(
                    estoque,
                    form_data=form_data,
                )

            flash("Retirada registrada com sucesso.")
            if notificacao:
                flash(notificacao)
            return redirect(url_for("pagina_estoque"))

        return render_retirar_estoque_page(estoque)

    @app.route("/fazer_pedido/<int:epi_id>", methods=["GET", "POST"])
    @login_required
    def fazer_pedido_route(epi_id):
        epi = obter_epi(epi_id)
        if epi is None:
            flash("Produto não encontrado.")
            return redirect(url_for("pagina_estoque"))
        if not epi["status"]:
            flash("Produto inativo não pode gerar solicitação de compra.")
            return redirect(url_for("pagina_estoque"))

        if request.method == "POST":
            form_data = validate_required_fields(
                [
                    ("quantidade", "A quantidade"),
                ]
            )
            if form_data is None:
                return render_fazer_pedido_page(epi)
            observacao = request.form.get("observacao", "").strip()

            try:
                usuario = buscar_usuario_por_id(session["usuario_id"])
                solicitacao = preparar_solicitacao_compra(
                    epi_id=epi_id,
                    quantidade=form_data["quantidade"],
                    observacao=observacao,
                    solicitante_nome=usuario["nome"] if usuario else "Almoxarife",
                )
            except ValueError as error:
                flash(str(error))
                return render_fazer_pedido_page(epi, form_data={**form_data, "observacao": observacao})

            return render_fazer_pedido_page(
                epi,
                form_data={
                    "quantidade": str(solicitacao["quantidade"]),
                    "observacao": solicitacao["observacao"],
                },
                pedido_email=solicitacao["pedido_email"],
                pedido_pendente=True,
            )

        return render_fazer_pedido_page(epi)

    @app.route("/confirmar_pedido/<int:epi_id>", methods=["POST"])
    @login_required
    def confirmar_pedido_route(epi_id):
        epi = obter_epi(epi_id)
        if epi is None:
            flash("Produto não encontrado.")
            return redirect(url_for("pagina_estoque"))
        if not epi["status"]:
            flash("Produto inativo não pode gerar solicitação de compra.")
            return redirect(url_for("pagina_estoque"))

        form_data = validate_required_fields(
            [
                ("quantidade", "A quantidade"),
            ]
        )
        if form_data is None:
            return render_fazer_pedido_page(epi)
        observacao = request.form.get("observacao", "").strip()

        try:
            usuario = buscar_usuario_por_id(session["usuario_id"])
            pedido_email = fazer_pedido(
                epi_id=epi_id,
                quantidade=form_data["quantidade"],
                observacao=observacao,
                user_id=session["usuario_id"],
                solicitante_nome=usuario["nome"] if usuario else "Almoxarife",
            )
        except ValueError as error:
            flash(str(error))
            return render_fazer_pedido_page(epi, form_data={**form_data, "observacao": observacao})

        flash("Solicitação registrada com sucesso. Agora envie o e-mail ao setor de compras.")
        return render_fazer_pedido_page(epi, pedido_email=pedido_email)

    @app.route("/encerrar_solicitacao/<int:pedido_id>", methods=["POST"])
    @login_required
    def encerrar_solicitacao_route(pedido_id):
        try:
            encerrar_pedido_sem_entrada(pedido_id)
        except ValueError as error:
            flash(str(error))
            return redirect(url_for("pagina_registro_solicitacoes"))

        flash("Solicitação encerrada sem necessidade de entrada de estoque.")
        return redirect(url_for("pagina_registro_solicitacoes"))

    @app.route("/esqueci_senha")
    def esqueci_senha():
        return render_esqueci_senha_page()

    @app.route("/redefinir_senha/<token>", methods=["GET"])
    def redefinir_senha(token):
        try:
            validar_token_recuperacao(token)
        except ValueError as error:
            flash(str(error))
            return redirect(url_for("esqueci_senha"))

        return render_mudar_senha_page(token)

    @app.route("/desativar_usuario/<int:user_id>", methods=["POST"])
    @app.route("/excluir_usuario/<int:user_id>", methods=["POST"], endpoint="excluir_usuario_legacy")
    @admin_required
    def desativar_usuario_route(user_id):
        usuario = buscar_usuario_por_id(user_id)
        if usuario is None:
            flash("Usuário não encontrado.")
            return redirect(url_for("pagina_usuarios"))

        if usuario["status"] == 0:
            flash("Usuário já está inativo.")
            return redirect(url_for("pagina_usuarios"))

        desativar_usuario(user_id)
        if session.get("usuario_id") == user_id:
            session.clear()
            flash("Seu usuário foi desativado.")
            return redirect(url_for("pagina_login"))

        flash("Usuário desativado com sucesso.")
        return redirect(url_for("pagina_usuarios"))

    @app.route("/ativar_usuario/<int:user_id>", methods=["POST"])
    @admin_required
    def ativar_usuario_route(user_id):
        usuario = buscar_usuario_por_id(user_id)
        if usuario is None:
            flash("Usuário não encontrado.")
            return redirect(url_for("pagina_usuarios", status="inativos"))

        if usuario["status"] == 1:
            flash("Usuário já está ativo.")
            return redirect(url_for("pagina_usuarios"))

        ativar_usuario(user_id)
        flash("Usuário ativado com sucesso.")
        return redirect(url_for("pagina_usuarios", status="inativos"))

    @app.route("/gerar_senha_provisoria/<int:user_id>", methods=["POST"])
    @admin_required
    def gerar_senha_provisoria_route(user_id):
        try:
            cadastro = gerar_nova_senha_provisoria(user_id)
        except ValueError as error:
            flash(str(error))
            return redirect(url_for("pagina_usuarios"))

        flash("Nova senha provisória gerada com sucesso.")
        return render_senha_provisoria_page(
            cadastro=cadastro,
            back_endpoint="pagina_usuarios",
            back_label="Voltar para usuários",
        )

    @app.route(
        "/editar_usuario/<int:user_id>",
        methods=["GET", "POST"],
        endpoint="atualizar_usuario",
    )
    @app.route("/editarusuario/<int:user_id>", methods=["GET", "POST"])
    @login_required
    def atualizar_usuario_route(user_id):
        current_user_id = session["usuario_id"]
        is_own_profile = current_user_id == user_id
        is_admin = session.get("tipo") == ADMIN_TYPE

        if not is_admin and not is_own_profile:
            flash("Você só pode editar o seu próprio perfil.")
            return redirect(url_for("meu_perfil"))

        usuario = buscar_usuario_por_id(user_id)
        if usuario is None:
            flash("Usuário não encontrado.")
            if is_admin and not is_own_profile:
                return redirect(url_for("pagina_usuarios"))
            return redirect(url_for("pagina_inicial"))

        can_edit_type = is_admin

        if request.method == "POST":
            form_data = validate_required_fields(
                [
                    ("nome", "O nome"),
                    ("email", "O e-mail"),
                ]
            )
            if form_data is None:
                dados_usuario = {
                    **usuario,
                    "nome": request.form.get("nome", "").strip(),
                    "email": request.form.get("email", "").strip(),
                    "tipo": request.form.get("tipo", usuario["tipo"]) if can_edit_type else usuario["tipo"],
                }
                return render_editar_usuario_page(
                    user_id,
                    usuario,
                    can_edit_type=can_edit_type,
                    is_own_profile=is_own_profile,
                    form_data=dados_usuario,
                )

            if email_ja_cadastrado(form_data["email"], ignored_user_id=user_id):
                flash("E-mail já cadastrado para outro usuário.")
                return render_editar_usuario_page(
                    user_id,
                    usuario,
                    can_edit_type=can_edit_type,
                    is_own_profile=is_own_profile,
                    form_data={
                        **usuario,
                        "nome": form_data["nome"],
                        "email": form_data["email"],
                        "tipo": request.form.get("tipo", usuario["tipo"]) if can_edit_type else usuario["tipo"],
                    },
                )

            requested_user_type = request.form.get("tipo", usuario["tipo"]) if can_edit_type else usuario["tipo"]
            nova_senha = request.form.get("senha", "").strip()
            try:
                atualizar_usuario(
                    user_id=user_id,
                    nome=form_data["nome"],
                    email=form_data["email"],
                    senha=nova_senha,
                    user_type=requested_user_type,
                    require_password_reset=bool(nova_senha and not is_own_profile),
                )
            except ValueError as error:
                flash(str(error))
                return render_editar_usuario_page(
                    user_id,
                    usuario,
                    can_edit_type=can_edit_type,
                    is_own_profile=is_own_profile,
                    form_data={
                        **usuario,
                        "nome": form_data["nome"],
                        "email": form_data["email"],
                        "tipo": requested_user_type,
                    },
                )

            if is_own_profile:
                session["tipo"] = int(requested_user_type)
                if nova_senha:
                    session["precisa_trocar_senha"] = False

            flash("Usuário atualizado com sucesso.")
            if is_admin and not is_own_profile:
                return redirect(url_for("pagina_usuarios"))
            return redirect(url_for("meu_perfil"))

        return render_editar_usuario_page(
            user_id,
            usuario,
            can_edit_type=can_edit_type,
            is_own_profile=is_own_profile,
        )

    @app.route("/validalogin", methods=["POST"])
    def login():
        form_data = validate_required_fields(
            [
                ("email", "O e-mail"),
                ("senha", "A senha"),
            ]
        )
        if form_data is None:
            return render_login_page()

        usuario = autenticar_usuario(form_data["email"], form_data["senha"])
        if usuario is None:
            flash("E-mail ou senha inválidos.")
            return render_login_page()

        log_in_user(usuario)
        if session.get("precisa_trocar_senha"):
            flash("No primeiro acesso, você precisa definir uma nova senha.")
            return redirect(url_for("primeiro_acesso"))
        set_current_page(PAGE_INICIAL)

        return redirect(url_for("pagina_inicial"))

    @app.route("/buscasenha", methods=["POST"])
    def buscasenha():
        form_data = validate_required_fields([("email", "O e-mail")])
        if form_data is None:
            return render_esqueci_senha_page()

        usuario = buscar_usuario_por_email(form_data["email"])
        if usuario is not None:
            token = gerar_token_recuperacao(usuario)
            app_base_url = get_app_base_url()
            if app_base_url:
                reset_link = f"{app_base_url}{url_for('redefinir_senha', token=token)}"
            else:
                reset_link = url_for("redefinir_senha", token=token, _external=True)
            try:
                enviar_email_recuperacao(form_data["email"], reset_link)
            except ValueError as error:
                flash(str(error))
                return render_esqueci_senha_page()

        flash("Se o e-mail estiver cadastrado, enviaremos um link para redefinir a senha.")
        return redirect(url_for("pagina_login"))

    @app.route("/primeiro-acesso", methods=["GET", "POST"])
    def primeiro_acesso():
        usuario_id = session.get("usuario_id")
        if not usuario_id:
            flash("Faca login para continuar.")
            return redirect(url_for("pagina_login"))

        usuario = buscar_usuario_por_id(usuario_id)
        if usuario is None or usuario["status"] != 1:
            session.clear()
            flash("Usuário não encontrado.")
            return redirect(url_for("pagina_login"))

        session["tipo"] = usuario["tipo"]
        session["precisa_trocar_senha"] = bool(usuario.get("precisa_trocar_senha"))

        if not session.get("precisa_trocar_senha"):
            return redirect(url_for("pagina_inicial"))

        if request.method == "POST":
            form_data = validate_required_fields([("senha", "A senha")])
            if form_data is None:
                return render_primeiro_acesso_page()

            atualizar_senha(usuario_id, form_data["senha"])
            session["precisa_trocar_senha"] = False
            flash("Senha definida com sucesso. Agora você já pode usar o sistema.")
            return redirect(url_for("pagina_inicial"))

        return render_primeiro_acesso_page()

    @app.route("/mudar_senha/<token>", methods=["POST"])
    def mudar_senha(token):
        try:
            usuario = validar_token_recuperacao(token)
        except ValueError as error:
            flash(str(error))
            return redirect(url_for("esqueci_senha"))

        form_data = validate_required_fields([("senha", "A senha")])
        if form_data is None:
            return render_mudar_senha_page(token)

        atualizar_senha(usuario["id"], form_data["senha"])
        flash("Senha atualizada com sucesso.")

        return redirect(url_for("pagina_login"))


