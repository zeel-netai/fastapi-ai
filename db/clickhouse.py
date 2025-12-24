import clickhouse_connect
from config import DB_CONFIG

client = None


def get_db_client():
    try:
        global client
        if client is None:
            client = clickhouse_connect.get_client(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                username=DB_CONFIG["username"],
                password=DB_CONFIG["password"],
            )
        return client
    except Exception as e:
        print(f"Error connecting to ClickHouse: {e}")
        return None
