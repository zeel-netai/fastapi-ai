from sentence_transformers import SentenceTransformer
from config import EMBEDDING_DIMENSION
import hashlib

# ============================================================================
# SINGLETON EMBEDDING MODEL (loaded once, reused)
# ============================================================================
_embedding_model = None
_embedding_cache = {}  # Cache to store computed embeddings


def get_embedding_model():
    """
    Get or initialize the embedding model as a singleton.
    This ensures the model is loaded only once for all embedding calls.
    """
    global _embedding_model
    if _embedding_model is None:
        print("[INIT] Loading embedding model 'all-MiniLM-L6-v2' (first time only)...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[INIT] Embedding model loaded successfully.")
    return _embedding_model


def _get_cache_key(text: str) -> str:
    """Generate a hash-based cache key for embeddings."""
    return hashlib.md5(text.encode()).hexdigest()


def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding from text with caching.
    Returns a list[float].
    
    Optimizations:
    - Uses singleton model instance (loaded once)
    - Caches computed embeddings to avoid recomputation
    """
    # Check cache first
    cache_key = _get_cache_key(text)
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
    
    # Get or initialize the embedding model
    embedding_model = get_embedding_model()
    embedding = embedding_model.encode(text).tolist()

    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(embedding)}"
        )
    
    # Cache the result
    _embedding_cache[cache_key] = embedding
    
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
