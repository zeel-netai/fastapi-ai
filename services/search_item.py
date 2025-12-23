from services.db_vectorizer import generate_embedding
from db.clickhouse import get_db_client


def search_device(query: str, result_limit=5, q_vector=None):
    try:
        query_vector = q_vector if q_vector else generate_embedding(query)
        client = get_db_client()

        # Convert Python list to ClickHouse array literal string
        # e.g. [0.12, 0.34] -> '[0.12,0.34]'
        vector_literal = "[" + ",".join(map(str, query_vector)) + "]"

        result = client.query(f"""
            SELECT
                device_id,
                device_hostname,
                device_type,
                scanned_ip,
                alerts_count,
                cosineDistance(embedding, {vector_literal}) AS score
            FROM temp.devices
            ORDER BY score ASC
            LIMIT {result_limit}
        """)

        rows = result.result_set  # returns list of tuples
        columns = result.column_names  # tuple of string names

        formatted = [dict(zip(columns, row)) for row in rows]

        # Suppress print to avoid interfering with JSONRPC
        # print("Search results:", formatted)
        return formatted

    except Exception as e:
        # Suppress print to avoid interfering with JSONRPC
        # print("Error in ask_navigation_query:", str(e))
        return f"An error occurred: {str(e)}"


def search_navigation_route(query: str, result_limit=5, q_vector=None):
    try:
        query_vector = q_vector if q_vector else generate_embedding(query)
        client = get_db_client()

        # Convert Python list to ClickHouse array literal string
        # e.g. [0.12, 0.34] -> '[0.12,0.34]'
        vector_literal = "[" + ",".join(map(str, query_vector)) + "]"

        result = client.query(f"""
            SELECT
                route_path,
                page_purpose,
                param_keys,
                param_purposes,
                param_types,
                param_required,
                is_dynamic_route,
                layouts,
                route_groups,
                access_level,
                cosineDistance(embedding, {vector_literal}) AS score
            FROM temp.navigation_routes
            ORDER BY score ASC
            LIMIT {result_limit}
        """)

        rows = result.result_set  # returns list of tuples
        columns = result.column_names  # tuple of string names

        formatted = [dict(zip(columns, row)) for row in rows]

        # Suppress print to avoid interfering with JSONRPC
        # print("Search results:", formatted)
        return formatted

    except Exception as e:
        # Suppress print to avoid interfering with JSONRPC
        # print("Error in ask_navigation_query:", str(e))
        return f"An error occurred: {str(e)}"


def chat_query(query: str):
    try:
        query_vector = generate_embedding(query)

        result_limit = 1

        route = search_navigation_route(query, result_limit, query_vector)
        device = search_device(query, result_limit, query_vector)

        params = {
            "navigation_route": None,
            "device_name": None,
            "device_id": None,
            "interface_name": None,
            "interface_id": None,
            "chat_id": None,
        }

        return {
            "navigation_route": route[0],
            "device": device[0],
        }

    except Exception as e:
        # Suppress print to avoid interfering with JSONRPC
        # print("Error in chat_with_navigation_route:", str(e))
        return f"An error occurred: {str(e)}"
