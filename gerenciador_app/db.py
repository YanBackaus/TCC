import mysql.connector

from gerenciador_app.config import DATABASE_CONFIG, DATABASE_NAME, SERVER_CONFIG


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE epi (
        id int(11) NOT NULL,
        nome varchar(45) NOT NULL,
        tipo varchar(45) NOT NULL DEFAULT 'Produto',
        descricao varchar(200) NOT NULL,
        quantidadeMin int(11) NOT NULL,
        ca int(11) NOT NULL,
        status tinyint(1) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """,
    """
    CREATE TABLE estoque (
        id int(11) NOT NULL,
        epi_id int(11) NOT NULL,
        quantidade int(11) NOT NULL,
        status tinyint(1) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """,
    """
    CREATE TABLE registroestoque (
        id int(11) NOT NULL,
        estoque_id int(11) NOT NULL,
        estoque_epi_id int(11) NOT NULL,
        Usuarios_id int(11) NOT NULL,
        data timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
        tipo tinyint(1) NOT NULL,
        quantidade int(11) NOT NULL DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """,
    """
    CREATE TABLE usuarios (
        id int(11) NOT NULL,
        nome varchar(45) NOT NULL,
        email varchar(45) NOT NULL,
        senha varchar(255) NOT NULL,
        tipo tinyint(1) NOT NULL,
        status tinyint(1) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """,
    "ALTER TABLE epi ADD PRIMARY KEY (id);",
    """
    ALTER TABLE estoque
    ADD PRIMARY KEY (id),
    ADD UNIQUE KEY uk_estoque_epi (epi_id);
    """,
    """
    ALTER TABLE registroestoque
    ADD PRIMARY KEY (id),
    ADD KEY fk_registroEstoque_estoque1 (estoque_id),
    ADD KEY fk_registroEstoque_Usuarios1 (Usuarios_id);
    """,
    """
    ALTER TABLE usuarios
    ADD PRIMARY KEY (id),
    ADD UNIQUE KEY uk_usuarios_email (email);
    """,
    "ALTER TABLE epi MODIFY id int(11) NOT NULL AUTO_INCREMENT;",
    "ALTER TABLE estoque MODIFY id int(11) NOT NULL AUTO_INCREMENT;",
    "ALTER TABLE registroestoque MODIFY id int(11) NOT NULL AUTO_INCREMENT;",
    "ALTER TABLE usuarios MODIFY id int(11) NOT NULL AUTO_INCREMENT;",
    """
    ALTER TABLE estoque
    ADD CONSTRAINT fk_estoque_epi
    FOREIGN KEY (epi_id) REFERENCES epi (id)
    ON DELETE NO ACTION ON UPDATE NO ACTION;
    """,
    """
    ALTER TABLE registroestoque
    ADD CONSTRAINT fk_registroEstoque_Usuarios1
    FOREIGN KEY (Usuarios_id) REFERENCES usuarios (id)
    ON DELETE NO ACTION ON UPDATE NO ACTION,
    ADD CONSTRAINT fk_registroEstoque_estoque1
    FOREIGN KEY (estoque_id) REFERENCES estoque (id)
    ON DELETE NO ACTION ON UPDATE NO ACTION;
    """,
]

RUNTIME_SCHEMA_STATEMENTS = [
    """
    ALTER TABLE usuarios
    MODIFY senha varchar(255) NOT NULL;
    """,
    """
    CREATE TABLE IF NOT EXISTS app_settings (
        setting_key varchar(100) NOT NULL,
        setting_value text NOT NULL,
        PRIMARY KEY (setting_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id int(11) NOT NULL AUTO_INCREMENT,
        epi_id int(11) NOT NULL,
        usuario_id int(11) NOT NULL,
        quantidade int(11) NOT NULL,
        observacao varchar(255) NOT NULL,
        status varchar(50) NOT NULL,
        data_pedido timestamp NOT NULL DEFAULT current_timestamp(),
        PRIMARY KEY (id),
        KEY fk_pedidos_epi (epi_id),
        KEY fk_pedidos_usuario (usuario_id),
        CONSTRAINT fk_pedidos_epi
            FOREIGN KEY (epi_id) REFERENCES epi (id)
            ON DELETE NO ACTION ON UPDATE NO ACTION,
        CONSTRAINT fk_pedidos_usuario
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            ON DELETE NO ACTION ON UPDATE NO ACTION
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """,
    """
    ALTER TABLE pedidos
    MODIFY status varchar(50) NOT NULL;
    """,
    """
    UPDATE pedidos
    SET status = CASE
        WHEN status = 'concluido_sem_entrad' THEN 'concluido_sem_entrada'
        WHEN status = 'concluido_com_entrad' THEN 'concluido_com_entrada'
        ELSE status
    END
    WHERE status IN ('concluido_sem_entrad', 'concluido_com_entrad');
    """,
]


def get_server_connection():
    return mysql.connector.connect(**SERVER_CONFIG)


def get_db_connection():
    return mysql.connector.connect(**DATABASE_CONFIG)


def initialize_database():
    if database_exists():
        execute_runtime_statements()
        ensure_runtime_schema()
        print(f"O banco de dados {DATABASE_NAME} existe e esta pronto para uso.")
        return

    create_database()
    execute_statements(SCHEMA_STATEMENTS)
    execute_runtime_statements()
    ensure_runtime_schema()


def database_exists():
    connection = get_server_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.SCHEMATA
            WHERE SCHEMA_NAME = %s;
            """,
            (DATABASE_NAME,),
        )
        return cursor.fetchone()[0] > 0
    finally:
        cursor.close()
        connection.close()


def create_database():
    connection = get_server_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(f"CREATE DATABASE {DATABASE_NAME};")
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def execute_runtime_statements():
    execute_statements(RUNTIME_SCHEMA_STATEMENTS)


def ensure_runtime_schema():
    ensure_column_exists(
        "epi",
        "tipo",
        "varchar(45) NOT NULL DEFAULT 'Produto'",
    )
    execute("ALTER TABLE epi MODIFY tipo varchar(45) NOT NULL DEFAULT 'Produto';")
    execute("UPDATE epi SET tipo = 'Produto' WHERE tipo IN ('EPI', 'produto');")
    ensure_column_exists(
        "usuarios",
        "precisa_trocar_senha",
        "tinyint(1) NOT NULL DEFAULT 0",
    )
    ensure_column_exists(
        "registroestoque",
        "quantidade",
        "int(11) NOT NULL DEFAULT 0",
    )
    ensure_unique_index_exists("usuarios", "uk_usuarios_email", ["email"])


def ensure_column_exists(table_name, column_name, definition):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s;
            """,
            (DATABASE_NAME, table_name, column_name),
        )
        column_found = cursor.fetchone()[0] > 0

        if not column_found:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition};"
            )
            connection.commit()
    finally:
        cursor.close()
        connection.close()


def ensure_unique_index_exists(table_name, index_name, column_names):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
              AND INDEX_NAME = %s
              AND NON_UNIQUE = 0;
            """,
            (DATABASE_NAME, table_name, index_name),
        )
        index_found = cursor.fetchone()[0] > 0

        if not index_found:
            escaped_columns = ", ".join(f"`{column_name}`" for column_name in column_names)
            cursor.execute(
                f"ALTER TABLE `{table_name}` ADD UNIQUE KEY `{index_name}` ({escaped_columns});"
            )
            connection.commit()
    finally:
        cursor.close()
        connection.close()


def execute_statements(statements):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        for statement in statements:
            cursor.execute(statement)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def fetch_all(query, params=None, dictionary=False):
    return run_query(
        query,
        params=params,
        dictionary=dictionary,
        fetch_mode="all",
    )


def fetch_one(query, params=None, dictionary=False):
    return run_query(
        query,
        params=params,
        dictionary=dictionary,
        fetch_mode="one",
    )


def execute(query, params=None):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, params or ())
        connection.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        connection.close()


def run_transaction(callback):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        result = callback(cursor)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def run_query(query, params=None, dictionary=False, fetch_mode=None):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=dictionary)

    try:
        cursor.execute(query, params or ())

        if fetch_mode == "one":
            return cursor.fetchone()
        if fetch_mode == "all":
            return cursor.fetchall()

        return None
    finally:
        cursor.close()
        connection.close()

