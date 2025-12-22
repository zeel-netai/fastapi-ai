import clickhouse_connect
from config import DB_CONFIG

client = clickhouse_connect.get_client(
    host=DB_CONFIG["host"],
    port=DB_CONFIG["port"],
    username=DB_CONFIG["username"],
    password=DB_CONFIG["password"],
)


def get_db_client():
    return client
