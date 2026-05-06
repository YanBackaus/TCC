import re


MYSQL_RESERVED_WORDS = {
    "alter",
    "create",
    "delete",
    "drop",
    "insert",
    "select",
    "truncate",
    "union",
    "update",
}

SQL_CONTROL_TOKENS = ("--", "/*", "*/", "#", ";")


def validate_against_sql_injection(*values):
    for value in values:
        if value is None:
            continue

        normalized_value = str(value).strip().lower()
        if not normalized_value:
            continue

        if any(token in normalized_value for token in SQL_CONTROL_TOKENS):
            raise ValueError("Os dados informados contem caracteres ou sequencias invalidas.")

        words = set(re.findall(r"[a-z_]+", normalized_value))
        if words & MYSQL_RESERVED_WORDS:
            raise ValueError("Os dados informados contem palavra reservada do MySQL.")
