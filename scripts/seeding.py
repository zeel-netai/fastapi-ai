import uuid
from db.clickhouse import get_db_client

# from db.devices_list import devices_list
from services.db_vectorizer import get_device_embedding, get_navigation_routes_embedding
from config import EMBEDDING_DIMENSION, IS_DEV_MODE


devices_list = __import__(
    "db.all_devices_list" if IS_DEV_MODE else "db.devices_list",
    fromlist=["devices_list"],
).devices_list

routes_data = __import__(
    "db.all_routes_data" if IS_DEV_MODE else "db.routes_data",
    fromlist=["routes_data"],
).routes_data


DATABASE_NAME = "temp"
VECTOR_INDEX_NAME = "embedding_idx"


def ensure_database(client, db_name: str):
    """
    Ensures the database exists and sets it as active.
    """
    client.command(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    client.command(f"USE {db_name}")


def create_vector_index(client, table_name: str, column_name: str = "embedding"):
    """
    Creates a vector similarity index using HNSW + cosine distance.
    Index is idempotent.
    """
    client.command(f"""
        ALTER TABLE {table_name}
        ADD INDEX IF NOT EXISTS {VECTOR_INDEX_NAME}
        {column_name}
        TYPE vector_similarity(
            'hnsw',
            'cosineDistance',
            {EMBEDDING_DIMENSION}
        )
        GRANULARITY 1
    """)


def create_devices_table():
    """
    Creates and initializes the `devices` table with a vector similarity index.
    """
    client = get_db_client()

    ensure_database(client, DATABASE_NAME)

    client.command("""
        CREATE TABLE IF NOT EXISTS devices (
            id UUID,
            device_id String,
            device_hostname String,
            device_type String,
            scanned_ip String,
            port_ip Array(String),
            alerts_count UInt32,
            embedding Array(Float32)
        )
        ENGINE = MergeTree
        ORDER BY id
    """)

    create_vector_index(client, table_name="devices")

    print("✅ 'devices' table and vector similarity index are ready!")


def insert_devices(devices: list[dict]):
    print(f"Inserting {len(devices)} device records into ClickHouse...")
    """
    Insert multiple device records into the `devices` table.

    Each device dict must contain:
    - device_id
    - device_hostname
    - device_type
    - scanned_ip
    - port_ip
    - alerts_count
    - embedding (Array[Float32], length = 384)
    """

    if not devices:
        return

    client = get_db_client()

    rows = []

    for index, device in enumerate(devices, start=1):
        print("Processing device:", index)
        device["embedding"] = get_device_embedding(device)
        rows.append(
            {
                "id": str(uuid.uuid4()),  # Generate unique row ID
                "device_id": device["device_id"],
                "device_hostname": device["device_hostname"],
                "device_type": device["device_type"],
                "scanned_ip": device["scanned_ip"],
                "port_ip": device["port_ip"],
                "alerts_count": device["alerts_count"],
                "embedding": device["embedding"],
            }
        )

    # Define column order
    columns = [
        "id",
        "device_id",
        "device_hostname",
        "device_type",
        "scanned_ip",
        "port_ip",
        "alerts_count",
        "embedding",
    ]

    # Convert list of dicts to list of tuples
    data_tuples = [tuple(row[col] for col in columns) for row in rows]

    # --------------------------------------------------
    # Batch insert into ClickHouse
    #
    # Why batch insert?
    # - Faster than inserting row-by-row
    # - Better performance for MergeTree tables
    # - Recommended approach in ClickHouse
    # --------------------------------------------------
    # Insert into ClickHouse
    client.insert(
        table="devices", data=data_tuples, column_names=columns, database="temp"
    )

    print(f"✅ Inserted {len(rows)} device records")


def create_navigation_routes_table():
    """
    Creates and initializes the `navigation_routes` table with
    a vector similarity index for semantic route discovery.
    """
    client = get_db_client()

    ensure_database(client, DATABASE_NAME)

    client.command("""
        CREATE TABLE IF NOT EXISTS navigation_routes (
            id UUID,
            route_path String,
            page_purpose String,

            param_keys Array(String),
            param_purposes Array(String),
            param_types Array(String),
            param_required Array(UInt8),

            is_dynamic_route UInt8,

            layouts Array(String),
            route_groups Array(String),
            access_level String,

            embedding Array(Float32)
        )
        ENGINE = MergeTree
        ORDER BY id
    """)

    create_vector_index(client, table_name="navigation_routes")

    print("✅ 'navigation_routes' table and vector similarity index are ready!")


def insert_navigation_routes(all_routes: list[dict]):
    routes = all_routes[0:20]
    """
    Insert multiple navigation route records into the `navigation_routes` table.

    Each route dict should contain:
    - route_path
    - page_purpose
    - routeParameters (dict)
    - is_dynamic_route ("True"/"False" or bool)
    - layouts (list[str])
    - routeGroups (list[str])
    - accessLevel
    """

    if not routes:
        return

    print(f"Inserting {len(routes)} navigation routes into ClickHouse...")

    client = get_db_client()
    rows = []

    for index, route in enumerate(routes, start=1):
        print("Processing route:", index)

        # Normalize route parameters
        param_keys = []
        param_purposes = []
        param_types = []
        param_required = []

        route_params = route.get("routeParameters", {}) or {}

        for key, meta in route_params.items():
            param_keys.append(key)
            param_purposes.append(meta.get("purpose", ""))
            param_types.append(meta.get("type", "string"))

            # Convert "True"/"False" or bool → UInt8
            required = meta.get("required", False)
            param_required.append(1 if str(required).lower() == "true" else 0)

        embedding = get_navigation_routes_embedding(route)

        # Build row
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "route_path": route["routePath"],
                "page_purpose": route.get("pagePurpose", ""),
                "param_keys": param_keys,
                "param_purposes": param_purposes,
                "param_types": param_types,
                "param_required": param_required,
                "is_dynamic_route": 1
                if str(route.get("isDynamicRoute")).lower() == "true"
                else 0,
                "layouts": route.get("layouts", []),
                "route_groups": route.get("routeGroups", []),
                "access_level": route.get("accessLevel", "public"),
                "embedding": embedding,
            }
        )

    # Column order must match ClickHouse table
    columns = [
        "id",
        "route_path",
        "page_purpose",
        "param_keys",
        "param_purposes",
        "param_types",
        "param_required",
        "is_dynamic_route",
        "layouts",
        "route_groups",
        "access_level",
        "embedding",
    ]

    data_tuples = [tuple(row[col] for col in columns) for row in rows]

    client.insert(
        table="navigation_routes",
        data=data_tuples,
        column_names=columns,
        database="temp",
    )

    print(f"✅ Inserted {len(rows)} navigation routes")


if __name__ == "__main__":
    # # for devices
    # create_devices_table()
    # insert_devices(devices_list)

    # for navigation routes
    create_navigation_routes_table()
    insert_navigation_routes(routes_data)
