from mcp_use.server import FastMCP
from services.search_item import (
    search_device as search_device_fn,
    search_navigation_route,
)
from services.db_vectorizer import generate_embedding


mcp = FastMCP("navigation_tools")


@mcp.tool()
def search_device(device_name: str, query_embedding=None) -> dict:
    """
    Search vector store for a device by name using semantic similarity.

    This tool searches through all devices in the ClickHouse database and finds
    the device that best matches the user's query using vector embeddings.

    Args:
        device_name (str): Device name, hostname, or description (e.g., "network device", "server xyz")
        query_embedding (list): Optional pre-computed embedding to avoid recomputation

    Returns:
        dict: Contains device_id (unique identifier) and device_name (hostname).
              Example: {"device_id": "123", "device_name": "prod-server-01"}

    Raises:
        Exception: If the search fails or no devices are found
    """
    try:
        # Use provided embedding or generate it (cached)
        q_embedding = (
            query_embedding if query_embedding else generate_embedding(device_name)
        )
        
        print('q_embedding search_device for intent:', query_embedding)


        results = search_device_fn(device_name, q_embedding)

        if not results or len(results) == 0:
            return {
                "status": "error",
                "device_id": None,  
                "device_name": None,
                "message": f"No device found matching '{device_name}'",
                "confidence": 0.0,
            }

        # Get the best match (first result has highest similarity)
        best_match = results[0]

        return {
            "status": "success",
            "device_id": str(best_match.get("device_id", "")),
            "device_name": str(best_match.get("device_hostname", "")),
            "device_type": best_match.get("device_type", ""),
            "scanned_ip": best_match.get("scanned_ip", ""),
            "similarity_score": float(best_match.get("score", 0.0)),
            "message": f"Successfully found device: {best_match.get('device_hostname')}",
        }

    except Exception as e:
        print(f"Error in search_device tool: {str(e)}")
        return {
            "status": "error",
            "device_id": None,
            "device_name": None,
            "message": f"Error searching for device: {str(e)}",
            "error_details": str(e),
        }


@mcp.tool()
def search_route(intent: str, query_embedding=None) -> dict:
    """
    Search vector store for a navigation route by user intent.

    This tool searches through all available navigation routes and finds the route
    that best matches the user's intended action using semantic similarity.

    The tool also analyzes route parameters and determines if the route:
    - Is STATIC (no parameters needed)
    - Is DEVICE-DYNAMIC (requires deviceId parameter)
    - Is INTERFACE-DYNAMIC (requires deviceId and interfaceId parameters)

    Args:
        intent (str): User's intent or action (e.g., "dashboard", "view alerts", "device overview")
        query_embedding (list): Optional pre-computed embedding to avoid recomputation

    Returns:
        dict: Contains route_path (the URL path template), route_type classification,
              and metadata about required parameters.

              Example static route:
              {
                "route_path": "/fault-management/alarms",
                "route_type": "static",
                "is_dynamic_route": false
              }

              Example device-dynamic route:
              {
                "route_path": "/device-summary/[deviceId]/dashboard",
                "route_type": "device-dynamic",
                "is_dynamic_route": true,
                "param_keys": ["deviceId"]
              }

    Raises:
        Exception: If the search fails or no routes are found
    """
    try:
        # Use provided embedding or generate it (cached)
        q_embedding = query_embedding if query_embedding else generate_embedding(intent)

        print('q_embedding Searching route for intent:', query_embedding)

        results = search_navigation_route(intent, q_embedding)

        if not results or len(results) == 0:
            return {
                "status": "error",
                "route_path": None,
                "message": f"No route found matching intent '{intent}'",
                "confidence": 0.0,
            }

        # Get the best match (first result has highest similarity)
        best_match = results[0]
        route_path = str(best_match.get("route_path", ""))
        is_dynamic = best_match.get("is_dynamic_route", False)
        param_keys = best_match.get("param_keys", [])

        # Determine route type based on parameters
        route_type = _classify_route_type(route_path, is_dynamic, param_keys)

        return {
            "status": "success",
            "route_path": route_path,
            "route_type": route_type,
            "page_purpose": best_match.get("page_purpose", ""),
            "is_dynamic_route": is_dynamic,
            "param_keys": param_keys,
            "param_purposes": best_match.get("param_purposes", []),
            "param_required": best_match.get("param_required", []),
            "layouts": best_match.get("layouts", []),
            "access_level": best_match.get("access_level", ""),
            "similarity_score": float(best_match.get("score", 0.0)),
            "message": f"Successfully found route: {route_path}",
        }

    except Exception as e:
        print(f"Error in search_route tool: {str(e)}")
        return {
            "status": "error",
            "route_path": None,
            "message": f"Error searching for route: {str(e)}",
            "error_details": str(e),
        }


def _classify_route_type(route_path: str, is_dynamic: bool, param_keys: list) -> str:
    """
    Classify a route as static, device-dynamic, or interface-dynamic.

    Args:
        route_path: The route path (e.g., "/device-summary/[deviceId]/dashboard")
        is_dynamic: Whether it's marked as a dynamic route
        param_keys: List of parameter keys

    Returns:
        str: "static", "device-dynamic", or "interface-dynamic"
    """
    if not is_dynamic or not param_keys:
        return "static"

    # Check if it's interface-dynamic
    if (
        "interfaceId" in param_keys
        or "interface_id" in param_keys
        or "/interface-summary/" in route_path
    ):
        return "interface-dynamic"

    # Check if it's device-dynamic
    if (
        "deviceId" in param_keys
        or "device_id" in param_keys
        or "/device-summary/" in route_path
    ):
        return "device-dynamic"

    return "static"


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
