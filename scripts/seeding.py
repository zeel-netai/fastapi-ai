import uuid
from db.clickhouse import get_db_client
# from db.devices_list import devices_list
from services.db_vectorizer import get_device_embedding
from config import EMBEDDING_DIMENSION, IS_DEV_MODE


devices_list = __import__(
    "db.all_devices_list" if IS_DEV_MODE else "db.devices_list",
    fromlist=["devices_list"],
).devices_list


def seed_devices_table():
    # Create a ClickHouse client (HTTP connection)
    client = get_db_client()

    # --------------------------------------------------
    # 1) CREATE DATABASE IF NOT EXISTS
    # This ensures the 'temp' database exists before we use it.
    # Running this multiple times is safe (idempotent).
    # --------------------------------------------------
    client.command(""" CREATE DATABASE IF NOT EXISTS temp """)

    # --------------------------------------------------
    # 2) USE `temp` DATABASE
    # All subsequent SQL will run inside this database.
    # --------------------------------------------------
    client.command(""" USE temp """)

    # --------------------------------------------------
    # 3) CREATE `devices` TABLE
    #
    # The table schema includes:
    # - id: Unique UUID for device row
    # - device_id/hostname/type: Info about the device
    # - scanned_ip, port_ip: IP addresses
    # - alerts_count: Count of alerts seen
    # - embedding: Array(Float32) storing vector embeddings
    #
    # NOTE: The embedding column must match the vector index
    #       dimension specified below (384 in this example).
    # --------------------------------------------------
    client.command("""
        CREATE TABLE IF NOT EXISTS devices (
            id UUID,
            device_id String,
            device_hostname String,
            device_type String,
            scanned_ip String,
            port_ip Array(String),          -- List of related IPs
            alerts_count UInt32,
            embedding Array(Float32)        -- Vector used for similarity search
        )
        ENGINE = MergeTree
        ORDER BY id
    """)

    # --------------------------------------------------
    # 4) CREATE VECTOR SIMILARITY INDEX
    #
    # Vector similarity indexes allow approximate nearest neighbor (ANN)
    # search for high-dimensional vectors stored in an Array column.
    #
    # How it works:
    #   • ClickHouse supports vector similarity indexes on MergeTree tables.
    #   • These indexes help prune data and reduce search cost for
    #     ORDER BY <distanceFunction(...)> queries (cosineDistance, L2Distance).
    #   • The index is a *skipping index* built over vector blocks.
    #
    # Syntax Breakdown (ClickHouse 25.x+):
    #
    #   vector_similarity(
    #     'hnsw',            → method name (HNSW graph for ANN search)
    #     'cosineDistance',  → distance function for similarity ranking
    #     384               → dimension of the embedding vector
    #   )
    #
    #   • 'hnsw'    → algorithm type (supports approximate search via graph)
    #   • 'cosineDistance' → distance metric (for cosine similarity search)
    #   • 384      → expected number of floats in each embedding array
    #
    # NOTE:
    #  • All arrays in the column must have exactly this many elements.
    #  • Index creation happens on future inserts; to build it for
    #    existing rows you may need to MATERIALIZE it later.
    #  • The `IF NOT EXISTS` clause avoids errors if the index already exists.
    # --------------------------------------------------
    client.command(f"""
        ALTER TABLE devices
        ADD INDEX IF NOT EXISTS embedding_idx
        embedding
        TYPE vector_similarity('hnsw', 'cosineDistance', {EMBEDDING_DIMENSION})
        GRANULARITY 1
    """)

    print("✅ 'devices' table and vector similarity index are ready!")


def insert_devices(all_devices: list[dict]):
    devices = all_devices[0:10]
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


if __name__ == "__main__":
    seed_devices_table()
    insert_devices(devices_list)
