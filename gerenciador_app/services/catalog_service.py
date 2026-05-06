from collections import Counter

from urllib.parse import quote

from gerenciador_app.db import run_transaction
from gerenciador_app.repositories.catalog_repository import (
    create_order,
    get_epi_by_id,
    get_order_by_id,
    get_stock_by_epi_id,
    get_stock_by_id,
    list_epis,
    list_inventory,
    list_logs_by_epi,
    list_recent_logs,
    list_recent_orders,
    update_order_status,
    update_epi,
    update_epi_status,
)
from gerenciador_app.services.input_validation_service import validate_against_sql_injection
from gerenciador_app.services.settings_service import get_purchase_department_email


LOG_TIPO_REGISTRO = 1
LOG_TIPO_EDICAO = 2
LOG_TIPO_RETIRADA = 3
PEDIDO_STATUS_SOLICITADO = "solicitado_por_email"
PEDIDO_STATUS_CONCLUIDO_SEM_ENTRADA = "concluido_sem_entrada"
PEDIDO_STATUS_CONCLUIDO_COM_ENTRADA = "concluido_com_entrada"


def _parse_positive_int(value, label, allow_zero=False):
    try:
        parsed_value = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{label} deve ser um numero inteiro.")

    if allow_zero:
        if parsed_value < 0:
            raise ValueError(f"{label} não pode ser negativo.")
    elif parsed_value <= 0:
        raise ValueError(f"{label} deve ser maior que zero.")

    return parsed_value


def _parse_status(value, label="O status"):
    try:
        parsed_value = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{label} informado e inválido.")

    if parsed_value not in (0, 1):
        raise ValueError(f"{label} informado e inválido.")

    return parsed_value


def _insert_stock_log(cursor, stock_id, epi_id, user_id, tipo, quantidade):
    cursor.execute(
        """
        INSERT INTO registroestoque (estoque_id, estoque_epi_id, Usuarios_id, tipo, quantidade)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (stock_id, epi_id, user_id, tipo, quantidade),
    )


def _decorate_epi(epi):
    epi["status_label"] = "Ativo" if epi["status"] else "Inativo"
    epi["estoque_baixo"] = epi["estoque_atual"] <= epi["quantidadeMin"]
    return epi


def _decorate_stock(item):
    item["possui_estoque"] = item["estoque_id"] is not None
    item["estoque_ativo"] = bool(item["epi_status"] and item["estoque_status"])
    item["status_label"] = "Ativo" if item["epi_status"] and item["estoque_status"] else "Inativo"
    item["estoque_baixo"] = item["estoque_ativo"] and item["quantidade"] <= item["quantidadeMin"]
    item["diferenca_minima"] = item["quantidade"] - item["quantidadeMin"]
    item["reposicao_sugerida"] = max(item["quantidadeMin"] - item["quantidade"], 1)
    return item


def _decorate_log(log_item):
    tipo_map = {
        LOG_TIPO_REGISTRO: "Registro de estoque",
        LOG_TIPO_EDICAO: "Edição de estoque",
        LOG_TIPO_RETIRADA: "Retirada de estoque",
    }
    log_item["tipo_label"] = tipo_map.get(log_item["tipo"], "Ação no estoque")
    return log_item


def _decorate_order(order_item):
    status_map = {
        PEDIDO_STATUS_SOLICITADO: "Solicitação por e-mail",
        PEDIDO_STATUS_CONCLUIDO_SEM_ENTRADA: "Concluida sem entrada",
        PEDIDO_STATUS_CONCLUIDO_COM_ENTRADA: "Concluida com entrada",
    }
    order_item["status_label"] = status_map.get(order_item["status"], order_item["status"])
    order_item["status_badge_class"] = {
        PEDIDO_STATUS_SOLICITADO: "text-bg-warning",
        PEDIDO_STATUS_CONCLUIDO_SEM_ENTRADA: "text-bg-secondary",
        PEDIDO_STATUS_CONCLUIDO_COM_ENTRADA: "text-bg-success",
    }.get(order_item["status"], "text-bg-light")
    order_item["encerrado"] = order_item["status"] != PEDIDO_STATUS_SOLICITADO
    return order_item


def _build_restock_notification(item):
    deficit = item["quantidadeMin"] - item["quantidade"]
    quantidade_sugerida = deficit if deficit > 0 else 1
    return {
        "epi_id": item["epi_id"],
        "epi_nome": item["epi_nome"],
        "quantidade_atual": item["quantidade"],
        "quantidade_minima": item["quantidadeMin"],
        "quantidade_sugerida": quantidade_sugerida,
        "mensagem": (
            f"O produto {item['epi_nome']} está acabando. "
            f"E recomendado comprar mais {quantidade_sugerida} unidade(s)."
        ),
    }


def _build_purchase_email(epi, quantidade_pedida, observacao, solicitante_nome):
    purchase_department_email = get_purchase_department_email()
    assunto = f"Solicitação de compra de produto - {epi['nome']}"
    mensagem = "\n".join(
        [
            "Prezados,",
            "",
            f"Solicito a compra do produto {epi['nome']}.",
            f"Quantidade solicitada: {quantidade_pedida} unidade(s).",
            f"Estoque atual: {epi['estoque_atual']} unidade(s).",
            f"Quantidade mínima definida: {epi['quantidadeMin']} unidade(s).",
            f"Observação do almoxarife: {observacao.strip()}",
            "",
            f"Solicitante: {solicitante_nome}",
        ]
    )
    mailto_url = (
        f"mailto:{purchase_department_email}"
        f"?subject={quote(assunto)}"
        f"&body={quote(mensagem)}"
    )

    return {
        "destinatario": purchase_department_email,
        "assunto": assunto,
        "mensagem": mensagem,
        "mailto_url": mailto_url,
    }


def _signed_log_quantity(log_item):
    if log_item["tipo"] == LOG_TIPO_RETIRADA:
        return -abs(log_item["quantidade"])
    return log_item["quantidade"]


def _format_log_date(log_date):
    if hasattr(log_date, "strftime"):
        return log_date.strftime("%d/%m %H:%M")
    return str(log_date)


def _build_stock_history(epi, logs):
    if not logs:
        return {
            "labels": ["Agora"],
            "quantidades": [epi["estoque_atual"]],
            "minimos": [epi["quantidadeMin"]],
            "ultima_movimentacao": "Sem movimentações registradas",
            "movimentacoes": 0,
        }

    signed_deltas = [_signed_log_quantity(log_item) for log_item in logs]
    quantity_before_history = epi["estoque_atual"] - sum(signed_deltas)
    current_quantity = quantity_before_history

    labels = []
    quantities = []

    if quantity_before_history != 0:
        labels.append("Base")
        quantities.append(quantity_before_history)

    for log_item, signed_delta in zip(logs, signed_deltas):
        current_quantity += signed_delta
        labels.append(_format_log_date(log_item["data"]))
        quantities.append(current_quantity)

    if not quantities:
        labels.append("Agora")
        quantities.append(epi["estoque_atual"])

    return {
        "labels": labels,
        "quantidades": quantities,
        "minimos": [epi["quantidadeMin"]] * len(quantities),
        "ultima_movimentacao": _format_log_date(logs[-1]["data"]),
        "movimentacoes": len(logs),
    }


def _build_dashboard_item(item, open_order_count):
    epi = obter_epi(item["epi_id"])
    logs = list_logs_by_epi(item["epi_id"])
    history = _build_stock_history(epi, logs) if epi is not None else _build_stock_history(item, [])
    return {
        "id": item["epi_id"],
        "nome": item["epi_nome"],
        "descricao": item["descricao"],
        "ca": item["ca"],
        "quantidade": item["quantidade"],
        "quantidade_minima": item["quantidadeMin"],
        "diferenca_minima": item["diferenca_minima"],
        "reposicao_sugerida": item["reposicao_sugerida"],
        "estoque_baixo": item["estoque_baixo"],
        "pedidos_abertos": open_order_count,
        "ultima_movimentacao": history["ultima_movimentacao"],
        "movimentacoes": history["movimentacoes"],
        "chart_labels": history["labels"],
        "chart_quantidades": history["quantidades"],
        "chart_minimos": history["minimos"],
    }


def _validar_pedido_aberto(pedido_id, epi_id=None):
    pedido = get_order_by_id(pedido_id)
    if pedido is None:
        raise ValueError("Solicitação não encontrada.")
    if pedido["status"] != PEDIDO_STATUS_SOLICITADO:
        raise ValueError("Essa solicitação já foi encerrada.")
    if epi_id is not None and pedido["epi_id"] != epi_id:
        raise ValueError("A solicitação informada não pertence a esse produto.")
    return _decorate_order(pedido)


def _matches_search(values, search):
    if not search:
        return True

    termo = search.strip().lower()
    if not termo:
        return True

    for value in values:
        if termo in str(value).lower():
            return True

    return False


def listar_epis(search=""):
    epis = [_decorate_epi(epi) for epi in list_epis()]
    if not search:
        return epis

    return [
        epi
        for epi in epis
        if _matches_search(
            [epi["nome"], epi["tipo"], epi["descricao"], epi["ca"], epi["status_label"]],
            search,
        )
    ]


def obter_epi(epi_id):
    epi = get_epi_by_id(epi_id)
    if epi is None:
        return None
    return _decorate_epi(epi)


def cadastrar_epi(nome, tipo, descricao, quantidade_min, ca, quantidade_estoque, user_id=None):
    validate_against_sql_injection(nome, tipo, descricao)
    quantidade_minima = _parse_positive_int(quantidade_min or 0, "A quantidade mínima", allow_zero=True)
    ca_numero = _parse_positive_int(ca or 0, "O CA", allow_zero=True)
    quantidade_inicial = _parse_positive_int(
        quantidade_estoque or 0,
        "A quantidade inicial em estoque",
        allow_zero=True,
    )

    def transaction(cursor):
        cursor.execute(
            """
            INSERT INTO epi (nome, tipo, descricao, quantidadeMin, ca, status)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (nome.strip(), tipo.strip(), descricao.strip(), quantidade_minima, ca_numero, 1),
        )
        epi_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO estoque (epi_id, quantidade, status)
            VALUES (%s, %s, %s);
            """,
            (epi_id, quantidade_inicial, 1),
        )
        stock_id = cursor.lastrowid

        if user_id is not None:
            _insert_stock_log(cursor, stock_id, epi_id, user_id, LOG_TIPO_REGISTRO, quantidade_inicial)

        return epi_id

    return run_transaction(transaction)


def editar_epi(epi_id, nome, tipo, descricao, quantidade_min, ca, status):
    epi = get_epi_by_id(epi_id)
    if epi is None:
        raise ValueError("Produto não encontrado.")

    validate_against_sql_injection(nome, tipo, descricao)
    quantidade_minima = (
        epi["quantidadeMin"]
        if str(quantidade_min or "").strip() == ""
        else _parse_positive_int(quantidade_min, "A quantidade mínima", allow_zero=True)
    )
    ca_numero = (
        epi["ca"]
        if str(ca or "").strip() == ""
        else _parse_positive_int(ca, "O CA", allow_zero=True)
    )
    status_epi = _parse_status(status)
    update_epi(epi_id, nome.strip(), tipo.strip(), descricao.strip(), quantidade_minima, ca_numero, status_epi)


def ativar_epi(epi_id):
    epi = get_epi_by_id(epi_id)
    if epi is None:
        raise ValueError("Produto não encontrado.")
    update_epi_status(epi_id, 1)


def desativar_epi(epi_id):
    epi = get_epi_by_id(epi_id)
    if epi is None:
        raise ValueError("Produto não encontrado.")

    update_epi_status(epi_id, 0)


def listar_estoque(search="", include_inactive=False):
    itens = [_decorate_stock(item) for item in list_inventory()]
    if not include_inactive:
        itens = [item for item in itens if item["epi_status"]]

    if not search:
        return itens

    return [
        item
        for item in itens
        if _matches_search(
            [
                item["epi_nome"],
                item["epi_tipo"],
                item["descricao"],
                item["ca"],
                item["status_label"],
                "acabando" if item["estoque_baixo"] else "normal",
            ],
            search,
        )
    ]


def obter_estoque(stock_id):
    estoque = get_stock_by_id(stock_id)
    if estoque is None:
        return None
    estoque["estoque_ativo"] = bool(estoque["epi_status"] and estoque["status"])
    estoque["estoque_baixo"] = estoque["quantidade"] <= estoque["quantidadeMin"]
    return estoque


def registrar_estoque(epi_id, quantidade, user_id):
    quantidade_registrada = _parse_positive_int(quantidade, "A quantidade")

    def transaction(cursor):
        cursor.execute(
            """
            SELECT id, status
            FROM epi
            WHERE id = %s
            FOR UPDATE;
            """,
            (epi_id,),
        )
        epi = cursor.fetchone()
        if epi is None:
            raise ValueError("Produto não encontrado.")
        if not epi["status"]:
            raise ValueError("Não é possível movimentar estoque de um produto inativo.")

        cursor.execute(
            """
            SELECT id, epi_id, quantidade, status
            FROM estoque
            WHERE epi_id = %s
            ORDER BY id DESC
            LIMIT 1
            FOR UPDATE;
            """,
            (epi_id,),
        )
        estoque = cursor.fetchone()

        if estoque is None:
            cursor.execute(
                """
                INSERT INTO estoque (epi_id, quantidade, status)
                VALUES (%s, %s, %s);
                """,
                (epi_id, quantidade_registrada, 1),
            )
            stock_id = cursor.lastrowid
        else:
            if not estoque["status"]:
                raise ValueError("Não é possível movimentar um estoque inativo.")

            stock_id = estoque["id"]
            cursor.execute(
                """
                UPDATE estoque
                SET quantidade = %s, status = %s
                WHERE id = %s;
                """,
                (estoque["quantidade"] + quantidade_registrada, 1, stock_id),
            )

        _insert_stock_log(cursor, stock_id, epi_id, user_id, LOG_TIPO_REGISTRO, quantidade_registrada)

    run_transaction(transaction)


def editar_estoque(stock_id, quantidade, user_id, status=1):
    quantidade_editada = _parse_positive_int(quantidade, "A quantidade", allow_zero=True)
    status_estoque = _parse_status(status)

    def transaction(cursor):
        cursor.execute(
            """
            SELECT
                s.id,
                s.epi_id,
                s.quantidade,
                s.status,
                e.status AS epi_status
            FROM estoque s
            INNER JOIN epi e ON e.id = s.epi_id
            WHERE s.id = %s
            FOR UPDATE;
            """,
            (stock_id,),
        )
        estoque = cursor.fetchone()
        if estoque is None:
            raise ValueError("Estoque não encontrado.")
        if not estoque["epi_status"]:
            raise ValueError("Não é possível editar estoque de um produto inativo.")

        quantidade_anterior = estoque["quantidade"]
        cursor.execute(
            """
            UPDATE estoque
            SET quantidade = %s, status = %s
            WHERE id = %s;
            """,
            (quantidade_editada, status_estoque, stock_id),
        )
        _insert_stock_log(
            cursor,
            stock_id,
            estoque["epi_id"],
            user_id,
            LOG_TIPO_EDICAO,
            quantidade_editada - quantidade_anterior,
        )

    run_transaction(transaction)


def retirar_estoque(stock_id, quantidade, user_id):
    quantidade_retirada = _parse_positive_int(quantidade, "A quantidade")

    def transaction(cursor):
        cursor.execute(
            """
            SELECT
                s.id,
                s.epi_id,
                s.quantidade,
                s.status,
                e.nome AS epi_nome,
                e.quantidadeMin,
                e.status AS epi_status
            FROM estoque s
            INNER JOIN epi e ON e.id = s.epi_id
            WHERE s.id = %s
            FOR UPDATE;
            """,
            (stock_id,),
        )
        estoque = cursor.fetchone()
        if estoque is None:
            raise ValueError("Estoque não encontrado.")
        if not estoque["epi_status"]:
            raise ValueError("Não é possível retirar estoque de um produto inativo.")
        if not estoque["status"]:
            raise ValueError("Não é possível retirar de um estoque inativo.")
        if quantidade_retirada > estoque["quantidade"]:
            raise ValueError("Não há estoque suficiente para essa retirada.")

        quantidade_final = estoque["quantidade"] - quantidade_retirada
        cursor.execute(
            """
            UPDATE estoque
            SET quantidade = %s, status = %s
            WHERE id = %s;
            """,
            (quantidade_final, 1, stock_id),
        )
        _insert_stock_log(cursor, stock_id, estoque["epi_id"], user_id, LOG_TIPO_RETIRADA, quantidade_retirada)

        return quantidade_final, estoque

    quantidade_final, estoque = run_transaction(transaction)

    if quantidade_final <= estoque["quantidadeMin"]:
        quantidade_sugerida = max(estoque["quantidadeMin"] - quantidade_final, 1)
        return (
            f"Notificação de reposição: o produto {estoque['epi_nome']} está acabando. "
            f"Compre mais {quantidade_sugerida} unidade(s)."
        )

    return None


def preparar_solicitacao_compra(epi_id, quantidade, observacao, solicitante_nome):
    epi = get_epi_by_id(epi_id)
    if epi is None:
        raise ValueError("Produto não encontrado.")
    if not epi["status"]:
        raise ValueError("Não é possível solicitar compra de um produto inativo.")
    estoque = get_stock_by_epi_id(epi_id)
    if estoque is not None and not estoque["status"]:
        raise ValueError("Não é possível solicitar compra de um estoque inativo.")

    quantidade_pedida = _parse_positive_int(quantidade, "A quantidade")
    observacao_texto = observacao.strip()
    validate_against_sql_injection(observacao_texto)

    return {
        "epi": epi,
        "quantidade": quantidade_pedida,
        "observacao": observacao_texto,
        "pedido_email": _build_purchase_email(
            epi,
            quantidade_pedida,
            observacao_texto,
            solicitante_nome,
        ),
    }


def fazer_pedido(epi_id, quantidade, observacao, user_id, solicitante_nome):
    solicitacao = preparar_solicitacao_compra(
        epi_id=epi_id,
        quantidade=quantidade,
        observacao=observacao,
        solicitante_nome=solicitante_nome,
    )
    create_order(
        epi_id=epi_id,
        user_id=user_id,
        quantidade=solicitacao["quantidade"],
        observacao=solicitacao["observacao"],
        status=PEDIDO_STATUS_SOLICITADO,
    )
    return solicitacao["pedido_email"]


def obter_pedido(pedido_id):
    pedido = get_order_by_id(pedido_id)
    if pedido is None:
        return None
    return _decorate_order(pedido)


def obter_pedido_aberto_para_entrada(pedido_id, epi_id):
    return _validar_pedido_aberto(pedido_id, epi_id=epi_id)


def encerrar_pedido_sem_entrada(pedido_id):
    _validar_pedido_aberto(pedido_id)
    update_order_status(pedido_id, PEDIDO_STATUS_CONCLUIDO_SEM_ENTRADA)


def concluir_pedido_com_entrada(pedido_id, epi_id):
    _validar_pedido_aberto(pedido_id, epi_id=epi_id)
    update_order_status(pedido_id, PEDIDO_STATUS_CONCLUIDO_COM_ENTRADA)


def listar_logs_recentes(limit=10):
    return [_decorate_log(item) for item in list_recent_logs(limit=limit)]


def listar_pedidos_recentes(limit=10):
    return [_decorate_order(item) for item in list_recent_orders(limit=limit)]


def listar_pedidos_abertos_por_epi(epi_id):
    return [
        _decorate_order(item)
        for item in list_recent_orders(
            limit=None,
            status=PEDIDO_STATUS_SOLICITADO,
            epi_id=epi_id,
        )
    ]


def listar_logs_detalhados(search="", limit=None):
    logs = listar_logs_recentes(limit=limit)
    if not search:
        return logs

    return [
        log
        for log in logs
        if _matches_search(
            [log["tipo_label"], log["epi_nome"], log["usuario_nome"], log["data"], log["quantidade"]],
            search,
        )
    ]


def listar_pedidos_detalhados(search="", limit=None):
    pedidos = listar_pedidos_recentes(limit=limit)
    if not search:
        return pedidos

    return [
        pedido
        for pedido in pedidos
        if _matches_search(
            [
                pedido["epi_nome"],
                pedido["usuario_nome"],
                pedido["status_label"],
                pedido["observacao"],
                pedido["data_pedido"],
                pedido["quantidade"],
            ],
            search,
        )
    ]


def montar_dashboard_estoque():
    itens_estoque = [
        item
        for item in listar_estoque(include_inactive=False)
        if item["estoque_ativo"]
    ]
    pedidos_abertos = listar_pedidos_recentes(limit=None)
    pedidos_abertos = [pedido for pedido in pedidos_abertos if pedido["status"] == PEDIDO_STATUS_SOLICITADO]
    pedidos_por_epi = Counter(pedido["epi_id"] for pedido in pedidos_abertos)

    total_itens = len(itens_estoque)
    itens_baixos = [item for item in itens_estoque if item["estoque_baixo"]]
    itens_com_folga = [item for item in itens_estoque if not item["estoque_baixo"]]
    notificacoes_reposicao = [_build_restock_notification(item) for item in itens_baixos]
    estoques_criticos = sorted(
        itens_baixos,
        key=lambda item: (item["diferenca_minima"], item["quantidade"], item["epi_nome"]),
    )
    itens_com_maior_folga = sorted(
        itens_estoque,
        key=lambda item: (-item["diferenca_minima"], -item["quantidade"], item["epi_nome"]),
    )
    menores_estoques = sorted(
        itens_estoque,
        key=lambda item: (item["quantidade"], item["epi_nome"]),
    )
    prioridade_do_dia = estoques_criticos[0] if estoques_criticos else (menores_estoques[0] if menores_estoques else None)
    menores_quantidades = sorted(
        itens_estoque,
        key=lambda item: (item["quantidade"], item["diferenca_minima"], item["epi_nome"]),
    )
    maiores_estoques = sorted(
        itens_estoque,
        key=lambda item: (-item["quantidade"], -item["diferenca_minima"], item["epi_nome"]),
    )
    dashboard_items = [
        _build_dashboard_item(item, pedidos_por_epi.get(item["epi_id"], 0))
        for item in sorted(itens_estoque, key=lambda estoque_item: estoque_item["epi_nome"])
    ]
    selected_item_id = prioridade_do_dia["epi_id"] if prioridade_do_dia else (dashboard_items[0]["id"] if dashboard_items else None)

    return {
        "resumo": {
            "total_itens": total_itens,
            "itens_baixos": len(itens_baixos),
            "itens_com_folga": len(itens_com_folga),
            "pedidos_abertos": len(pedidos_abertos),
        },
        "prioridade_do_dia": prioridade_do_dia,
        "prioridade_em_alerta": bool(estoques_criticos),
        "epi_menor_estoque": menores_estoques[0] if menores_estoques else None,
        "epi_maior_folga": itens_com_maior_folga[0] if itens_com_maior_folga else None,
        "itens_baixos": itens_baixos[:5],
        "notificacoes_reposicao": notificacoes_reposicao[:5],
        "estoques_criticos": estoques_criticos[:5],
        "menores_quantidades": menores_quantidades[:5],
        "maiores_estoques": maiores_estoques[:5],
        "maiores_folgas": itens_com_maior_folga[:5],
        "itens_dashboard": dashboard_items,
        "selected_item_id": selected_item_id,
    }


