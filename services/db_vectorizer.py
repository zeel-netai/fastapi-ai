from sentence_transformers import SentenceTransformer
from config import EMBEDDING_DIMENSION


def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding from text.
    Returns a list[float].
    """
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = embedding_model.encode(text).tolist()

    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(embedding)}"
        )
    return embedding


def build_device_embedding_text(device: dict) -> str:
    """
    Convert a device record into a human-readable text
    that can be embedded for semantic search.
    """

    port_ips = ", ".join(device.get("port_ip", []))

    return (
        f"Device hostname {device.get('device_hostname')} "
        f"with device ID {device.get('device_id')} "
        f"is a {device.get('device_type')} device. "
        f"Scanned IP address is {device.get('scanned_ip')}. "
        f"Associated port IPs are {port_ips}. "
        f"Alert count is {device.get('alerts_count')}."
    )


def build_navigation_routes_embedding_text(nav: dict) -> str:
    """
    Convert a device record into a human-readable text
    that can be embedded for semantic search.
    """
    return f"{nav['pagePurpose']} {nav['routePath']}"


def get_device_embedding(device: dict) -> list[float]:
    """Generate embedding for a device record."""
    text = build_device_embedding_text(device)
    return generate_embedding(text)


def get_navigation_routes_embedding(device: dict) -> list[float]:
    """Generate embedding for a device record."""
    text = build_navigation_routes_embedding_text(device)
    return generate_embedding(text)
