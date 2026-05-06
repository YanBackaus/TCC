from gerenciador_app.db import execute, fetch_all, fetch_one


def list_settings():
    return fetch_all(
        """
        SELECT setting_key, setting_value
        FROM app_settings;
        """,
        dictionary=True,
    )


def get_setting(setting_key):
    return fetch_one(
        """
        SELECT setting_key, setting_value
        FROM app_settings
        WHERE setting_key = %s;
        """,
        (setting_key,),
        dictionary=True,
    )


def upsert_setting(setting_key, setting_value):
    execute(
        """
        INSERT INTO app_settings (setting_key, setting_value)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);
        """,
        (setting_key, setting_value),
    )
