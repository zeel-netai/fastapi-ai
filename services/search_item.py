from services.db_vectorizer import generate_embedding
from db.clickhouse import get_db_client


def search_device(query: str):
    try:
        query_vector = generate_embedding(query)
        client = get_db_client()

        result_limit = 5

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

        print("Search results:", formatted)
        return formatted

    except Exception as e:
        print("Error in ask_navigation_query:", str(e))
        return f"An error occurred: {str(e)}"


def search_navigation_route(query: str):
    try:
        query_vector = generate_embedding(query)
        client = get_db_client()

        result_limit = 5

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

        print("Search results:", formatted)
        return formatted

    except Exception as e:
        print("Error in ask_navigation_query:", str(e))
        return f"An error occurred: {str(e)}"
