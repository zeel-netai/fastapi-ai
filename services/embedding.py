import os
import pickle
import numpy as np
import faiss
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from db.routes_data import routes_data
from config import EMBEDDINGS_MODEL_NAME, FAISS_INDEX_DIR, METADATA_PATH


# convert route item to text for embedding
def make_text_for_embedding(route_item: dict) -> str:
    base = f"Route path: {route_item.get('routePath', '')}.\n"
    purpose = f"Page purpose: {route_item.get('pagePurpose', '')}.\n"

    dynamic = (
        "This is a dynamic route.\n"
        if str(route_item.get("isDynamicRoute", "")).lower() == "true"
        else "This is a static route.\n"
    )

    param_texts = []
    params = route_item.get("routeParameters", {})
    if params:
        for key, info in params.items():
            param_texts.append(
                f"Parameter '{key}': "
                f"{info.get('purpose', '')}, "
                f"type {info.get('type', '')}, "
                f"{'required' if info.get('required') == 'true' else 'optional'}, "
                f"from {info.get('source', '')}."
            )

    params_desc = (
        "Route parameters: " + " ".join(param_texts) + "\n"
        if param_texts
        else "No route parameters.\n"
    )

    return base + purpose + dynamic + params_desc


# Check if FAISS index and metadata exist in memory/disk if exists load them
def is_faiss_index_present() -> dict:
    result = {"is_existing": False, "vector_store": None, "metadata": None}

    # FAISS stores index in one file and metadata separately
    if os.path.isfile(FAISS_INDEX_DIR) and os.path.isfile(METADATA_PATH):
        try:
            print("Loading existing FAISS embeddings...")

            with open(METADATA_PATH, "rb") as mfile:
                stored_metadata = pickle.load(mfile)

            # Load FAISS index
            vector_store = faiss.read_index(FAISS_INDEX_DIR)

            result["is_existing"] = True
            result["vector_store"] = vector_store
            result["metadata"] = stored_metadata

            print("FAISS index and metadata loaded successfully.")
        except Exception as err:
            print("Failed to load existing embeddings:", err)

    return result


# Create embeddings model and FAISS index
def create_embeddings_model() -> dict:
    try:
        # First check if we already have an index on disk
        result = is_faiss_index_present()
        if result.get("is_existing"):
            return {
                "vector_store": result.get("vector_store"),
                "metadata": result.get("metadata"),
            }

        print("Creating new FAISS index...")

        # Create the Google embedding model
        embeddings_model = GoogleGenerativeAIEmbeddings(model=EMBEDDINGS_MODEL_NAME)

        vectors_list = []
        metadata = []

        for item in routes_data:
            text = make_text_for_embedding(item)
            # generate vector (single embedding)
            vector = embeddings_model.embed_query(text)
            vectors_list.append(vector)
            metadata.append({"id": item["id"], "routePath": item.get("routePath", "")})

        # Convert list of vectors to numpy as FAISS needs numpy arrays for indexing
        vectors_np = np.array(vectors_list, dtype="float32")

        if len(vectors_np.shape) != 2:
            raise ValueError("Invalid shape for embedding vectors.")

        dim = vectors_np.shape[1]
        index = faiss.IndexFlatL2(dim)

        index.add(vectors_np)

        # Save FAISS index to disk
        faiss.write_index(index, FAISS_INDEX_DIR)
        print("FAISS index saved to disk.")

        # Save metadata to disk
        with open(METADATA_PATH, "wb") as mfile:
            pickle.dump(metadata, mfile)
        print("Metadata saved to disk.")

        return {"vectors": index, "metadata": metadata}

    except Exception as e:
        return {"error": f"An error occurred while creating embeddings model: {str(e)}"}


# Perform semantic search and return top K results
def semantic_search(query_text, index, metadata, top_k=5):
    # Create query embedding
    model = GoogleGenerativeAIEmbeddings(model=EMBEDDINGS_MODEL_NAME)
    q_vec = model.embed_query(query_text)

    # FAISS expects shape (1, dim)
    q_np = np.array([q_vec], dtype="float32")

    # Search top K
    distances, indices = index.search(q_np, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue

        doc_meta = metadata[idx]
        results.append(
            {
                "route": doc_meta["routePath"],
                # "purpose": doc_meta["pagePurpose"],
                "score": float(dist),
            }
        )

    return results
