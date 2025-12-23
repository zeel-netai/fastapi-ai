import json
from mcp_use import MCPClient, MCPAgent
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.hepler import highlight_text

# ============================================================================
# AGENT CONFIGURATION & SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """
You are an intelligent AI navigation assistant that helps users find the correct 
dashboard URLs and navigate to various pages in the system.

## Your Core Task:
Analyze the user's query and intelligently determine:
1. Whether they need a DEVICE-SPECIFIC page (requires device ID)
2. Whether they need an INTERFACE-SPECIFIC page (requires device ID + interface ID)  
3. Whether they need a STATIC page (no IDs needed)

## Decision Logic:

### Case 1: STATIC PAGES (No search needed)
Examples: fault management, alerts, admin pages, users, reports, etc.
- User says: "Show me the fault management page"
- User says: "I want to see system alarms"
- Action: ONLY call search_route tool
- Return URL directly from route_template

### Case 2: DEVICE-SPECIFIC PAGES (Device search needed)
Examples: device dashboard, device alerts, device inventory, etc.
- User says: "Show me the dashboard for server XYZ"
- User says: "I want the dashboard for device-01"
- Action: CALL search_device → CALL search_route → Build URL
- Return format: device-summary/{device_id}/{endpoint}

### Case 3: INTERFACE-SPECIFIC PAGES (Device + Interface search needed)
Examples: interface dashboard, interface inventory, etc.
- User says: "Show me interface eth0 dashboard on device-01"
- User says: "I want to see interface metrics for server XYZ"
- Action: CALL search_device → May need additional context or search_route
- Return format: interface-summary/{device_id}/{interface_id}/{endpoint}

## Tool Usage Instructions:

### Tool: search_device(device_name: str)
- Input: Device name/description from the user query
- Returns: {device_id, device_name, status}
- Use ONLY when user mentions a specific device

### Tool: search_route(intent: str)
- Input: What the user wants to do (dashboard, alerts, fault management, etc.)
- Returns: {route_path, is_dynamic_route, param_keys, status}
- Use for EVERY query to determine the target page

## URL Construction Rules:

### Static Routes:
- No parameters needed
- Example: "/fault-management/alarms" → "fault-management/alarms"

### Device-Dynamic Routes:
- Starts with device-summary/[deviceId]
- Format: device-summary/{device_id}/{endpoint}
- Examples: device dashboard, alerts, inventory, audit-log, configurations, debug

### Interface-Dynamic Routes:
- Starts with interface-summary/[deviceId]/[interfaceId]
- Format: interface-summary/{device_id}/{interface_id}/{endpoint}
- Examples: interface dashboard, interface inventory

## Response Format:
ALWAYS respond with a JSON object in this exact format:
{
    "status": "success" or "error",
    "device_name": "found device name or null",
    "device_id": "found device id or null",
    "interface_id": "found interface id or null",
    "route_endpoint": "the extracted endpoint or null",
    "final_url": "the complete URL or null",
    "route_type": "static" | "device-dynamic" | "interface-dynamic",
    "message": "descriptive message for the user"
}

## Important Guidelines:
- Analyze user intent BEFORE calling tools
- Only call search_device if user mentions a device
- Always call search_route to determine the target page
- For static pages (like fault management, alerts), skip device search entirely
- Extract endpoint from route_path correctly
- Handle missing devices/routes with clear error messages
- Be concise and user-friendly in messages
- Return valid JSON only
"""

# ============================================================================
# SETUP AGENT FUNCTION
# ============================================================================


async def setup_agent(query: str):
    """
    Initialize and run the AI navigation assistant agent.

    Args:
        query: User's natural language query (e.g., "Show me the dashboard for device XYZ")

    Returns:
        dict: Structured response with device info, route, and final URL
    """
    try:
        # Configure MCP Client to connect to the MCP server
        config = {
            "mcpServers": {
                "navigation_tools": {
                    "transport": "stdio",
                    "command": "python",
                    "args": ["mcp_server.py"],
                }
            }
        }

        # Create MCPClient from configuration
        client = MCPClient.from_dict(config)

        # Build the LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,  # Lower temperature for more deterministic responses
        )

        # Create agent with improved configuration
        agent = MCPAgent(
            llm=llm,
            client=client,
            max_steps=30,
            system_prompt=SYSTEM_PROMPT,
        )

        # Run the query through the agent
        highlight_text(f"[AGENT] Processing query: '{query}'")
        result = await agent.run(query)

        # Parse and validate the result
        parsed_result = _parse_agent_response(result)

        print("\n[SUCCESS] Agent result:")
        highlight_text(json.dumps(parsed_result, indent=2))

        return parsed_result

    except Exception as e:
        error_response = {
            "status": "error",
            "device_name": None,
            "device_id": None,
            "interface_id": None,
            "route_endpoint": None,
            "final_url": None,
            "route_type": None,
            "message": f"Error during agent execution: {str(e)}",
        }
        print(f"\n[ERROR] {str(e)}")
        return error_response


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _parse_agent_response(response) -> dict:
    """
    Parse and validate the agent's response.

    Args:
        response: Raw response from the agent

    Returns:
        dict: Structured and validated response
    """
    # Try to extract JSON from response
    if isinstance(response, dict):
        return _ensure_response_fields(response)

    response_str = str(response)

    # Try to find JSON in the response
    try:
        # Look for JSON pattern in response
        json_start = response_str.find("{")
        json_end = response_str.rfind("}") + 1

        if json_start != -1 and json_end > json_start:
            json_str = response_str[json_start:json_end]
            parsed = json.loads(json_str)
            return _ensure_response_fields(parsed)
    except (json.JSONDecodeError, ValueError):
        pass

    # If we can't parse, return a default error structure
    return {
        "status": "error",
        "device_name": None,
        "device_id": None,
        "interface_id": None,
        "route_endpoint": None,
        "final_url": None,
        "route_type": None,
        "message": f"Could not parse agent response: {response_str[:200]}",
    }


def _ensure_response_fields(response: dict) -> dict:
    """Ensure all required fields are present in response."""
    required_fields = {
        "status": None,
        "device_name": None,
        "device_id": None,
        "interface_id": None,
        "route_endpoint": None,
        "final_url": None,
        "route_type": None,
        "message": "Navigation result",
    }
    return {**required_fields, **response}
