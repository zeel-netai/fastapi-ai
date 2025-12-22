from fastapi import FastAPI
from models.chat_ai import AskQuery
from services.chat_ai import ask_query, ask_navigation_query
from dotenv import load_dotenv
from services.embedding import create_embeddings_model
from db.clickhouse import get_db_client

app = FastAPI()

vectors = None
metadata = None


# This function will run when the server starts
@app.on_event("startup")
def startup_event():
    try:
        print("====== Performing startup tasks...=======")
        load_dotenv()
        result = create_embeddings_model()
        global vectors, metadata
        vectors = result.get("vectors")
        metadata = result.get("metadata")
        print("====== Startup tasks completed. =======")
    except Exception as e:
        print("====== Error during startup: =======", str(e))


@app.get("/")
async def read_root():
    return {
        "message": "Welcome to the FastAPI AI service!",
        "endpoints": {
            "/ping": {
                "method": "GET",
                "description": "for checking if the service is alive.",
                "url": "/ping",
            },
            "/ask": {
                "method": "POST",
                "description": "Ask a question to the AI and get a response.",
                "payload": {"query": "The question you want to ask the AI."},
            },
            "/query": {
                "method": "POST",
                "description": "Ask a navigation related question to the AI and get a response.",
                "payload": {"query": "The question you want to ask the AI."},
            },
        },
    }


@app.get("/health")
def health_check():
    db = get_db_client()
    result = db.query("SELECT 1")
    return {"status": "ok", "db_respons ": result.result_rows}


@app.get("/ping")
def ping():
    return {"message": "pong", "status": "success"}


@app.post("/ask")
def ask_question(payload: AskQuery):
    response = ask_query(payload.query)
    return {"query": payload.query, "response": response}


@app.post("/query")
def ask_navigation_query_fn(payload: AskQuery):
    response = ask_navigation_query(payload.query, vectors, metadata)
    return {"query": payload.query, "response": response}
