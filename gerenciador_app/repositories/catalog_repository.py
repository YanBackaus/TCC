from gerenciador_app.db import execute, fetch_all, fetch_one


LATEST_STOCK_JOIN = """
    LEFT JOIN estoque s ON s.id = (
        SELECT s2.id
        FROM estoque s2
        WHERE s2.epi_id = e.id
        ORDER BY s2.id DESC
        LIMIT 1
    )
"""


def list_epis():
    return fetch_all(
        f"""
        SELECT
            e.id,
            e.nome,
            e.tipo,
            e.descricao,
            e.quantidadeMin,
            e.ca,
            e.status,
            COALESCE(s.quantidade, 0) AS estoque_atual
        FROM epi e
        {LATEST_STOCK_JOIN}
        ORDER BY e.nome;
        """,
        dictionary=True,
    )


def get_epi_by_id(epi_id):
    return fetch_one(
        f"""
        SELECT
            e.id,
            e.nome,
            e.tipo,
            e.descricao,
            e.quantidadeMin,
            e.ca,
            e.status,
            COALESCE(s.quantidade, 0) AS estoque_atual
        FROM epi e
        {LATEST_STOCK_JOIN}
        WHERE e.id = %s;
        """,
        (epi_id,),
        dictionary=True,
    )


def create_epi(nome, tipo, descricao, quantidade_min, ca, status):
    return execute(
        """
        INSERT INTO epi (nome, tipo, descricao, quantidadeMin, ca, status)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (nome, tipo, descricao, quantidade_min, ca, status),
    )


def update_epi(epi_id, nome, tipo, descricao, quantidade_min, ca, status):
    execute(
        """
        UPDATE epi
        SET nome = %s, tipo = %s, descricao = %s, quantidadeMin = %s, ca = %s, status = %s
        WHERE id = %s;
        """,
        (nome, tipo, descricao, quantidade_min, ca, status, epi_id),
    )


def update_epi_status(epi_id, status):
    execute(
        """
        UPDATE epi
        SET status = %s
        WHERE id = %s;
        """,
        (status, epi_id),
    )


def list_inventory():
    return fetch_all(
        f"""
        SELECT
            e.id AS epi_id,
            e.nome AS epi_nome,
            e.tipo AS epi_tipo,
            e.descricao,
            e.quantidadeMin,
            e.ca,
            e.status AS epi_status,
            s.id AS estoque_id,
            COALESCE(s.quantidade, 0) AS quantidade,
            COALESCE(s.status, 1) AS estoque_status
        FROM epi e
        {LATEST_STOCK_JOIN}
        ORDER BY e.nome;
        """,
        dictionary=True,
    )


def get_stock_by_id(stock_id):
    return fetch_one(
        """
        SELECT
            s.id,
            s.epi_id,
            s.quantidade,
            s.status,
            e.nome AS epi_nome,
            e.tipo AS epi_tipo,
            e.quantidadeMin,
            e.status AS epi_status
        FROM estoque s
        INNER JOIN epi e ON e.id = s.epi_id
        WHERE s.id = %s;
        """,
        (stock_id,),
        dictionary=True,
    )


def get_stock_by_epi_id(epi_id):
    return fetch_one(
        """
        SELECT
            s.id,
            s.epi_id,
            s.quantidade,
            s.status
        FROM estoque s
        WHERE s.epi_id = %s
        ORDER BY s.id DESC
        LIMIT 1;
        """,
        (epi_id,),
        dictionary=True,
    )


def create_stock(epi_id, quantidade, status):
    return execute(
        """
        INSERT INTO estoque (epi_id, quantidade, status)
        VALUES (%s, %s, %s);
        """,
        (epi_id, quantidade, status),
    )


def update_stock(stock_id, quantidade, status):
    execute(
        """
        UPDATE estoque
        SET quantidade = %s, status = %s
        WHERE id = %s;
        """,
        (quantidade, status, stock_id),
    )


def create_stock_log(stock_id, epi_id, user_id, tipo, quantidade, data=None):
    if data is not None:
        return execute(
            """
            INSERT INTO registroestoque (estoque_id, estoque_epi_id, Usuarios_id, tipo, quantidade, data)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (stock_id, epi_id, user_id, tipo, quantidade, data),
        )

    return execute(
        """
        INSERT INTO registroestoque (estoque_id, estoque_epi_id, Usuarios_id, tipo, quantidade)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (stock_id, epi_id, user_id, tipo, quantidade),
    )


def list_logs_by_epi(epi_id):
    return fetch_all(
        """
        SELECT
            r.id,
            r.data,
            r.tipo,
            r.quantidade,
            u.nome AS usuario_nome
        FROM registroestoque r
        INNER JOIN usuarios u ON u.id = r.Usuarios_id
        WHERE r.estoque_epi_id = %s
        ORDER BY r.data ASC, r.id ASC;
        """,
        (epi_id,),
        dictionary=True,
    )


def list_recent_logs(limit=10):
    limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""
    return fetch_all(
        f"""
        SELECT
            r.id,
            r.data,
            r.tipo,
            r.quantidade,
            e.nome AS epi_nome,
            u.nome AS usuario_nome
        FROM registroestoque r
        INNER JOIN epi e ON e.id = r.estoque_epi_id
        INNER JOIN usuarios u ON u.id = r.Usuarios_id
        ORDER BY r.data DESC
        {limit_clause};
        """,
        dictionary=True,
    )


def create_order(epi_id, user_id, quantidade, observacao, status):
    return execute(
        """
        INSERT INTO pedidos (epi_id, usuario_id, quantidade, observacao, status)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (epi_id, user_id, quantidade, observacao, status),
    )


def get_order_by_id(order_id):
    return fetch_one(
        """
        SELECT
            p.id,
            p.epi_id,
            p.usuario_id,
            p.quantidade,
            p.observacao,
            p.status,
            p.data_pedido,
            e.nome AS epi_nome,
            u.nome AS usuario_nome
        FROM pedidos p
        INNER JOIN epi e ON e.id = p.epi_id
        INNER JOIN usuarios u ON u.id = p.usuario_id
        WHERE p.id = %s;
        """,
        (order_id,),
        dictionary=True,
    )


def update_order_status(order_id, status):
    execute(
        """
        UPDATE pedidos
        SET status = %s
        WHERE id = %s;
        """,
        (status, order_id),
    )


def count_orders_by_status(status, epi_id=None):
    query = """
        SELECT COUNT(*) AS total
        FROM pedidos
        WHERE status = %s
    """
    params = [status]

    if epi_id is not None:
        query += " AND epi_id = %s"
        params.append(epi_id)

    result = fetch_one(
        f"{query};",
        tuple(params),
        dictionary=True,
    )
    return result["total"] if result is not None else 0


def list_recent_orders(limit=10, status=None, epi_id=None):
    limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""
    filters = []
    params = []

    if status is not None:
        filters.append("p.status = %s")
        params.append(status)

    if epi_id is not None:
        filters.append("p.epi_id = %s")
        params.append(epi_id)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    return fetch_all(
        f"""
        SELECT
            p.id,
            p.epi_id,
            p.usuario_id,
            p.quantidade,
            p.observacao,
            p.status,
            p.data_pedido,
            e.nome AS epi_nome,
            u.nome AS usuario_nome
        FROM pedidos p
        INNER JOIN epi e ON e.id = p.epi_id
        INNER JOIN usuarios u ON u.id = p.usuario_id
        {where_clause}
        ORDER BY p.data_pedido DESC
        {limit_clause};
        """,
        tuple(params),
        dictionary=True,
    )
