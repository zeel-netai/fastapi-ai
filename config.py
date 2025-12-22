from dotenv import load_dotenv
import os

load_dotenv()

EMBEDDINGS_MODEL_NAME = "gemini-embedding-001"
FAISS_INDEX_DIR = "faiss_routes_index"
METADATA_PATH = "faiss_routes_metadata.pkl"

DB_CONFIG = {
    "host": "localhost",
    "port": 8123,
    "username": "admin",
    "password": os.getenv("DB_PASSWORD"),
}

EMBEDDING_DIMENSION = 384

IS_DEV_MODE = False
