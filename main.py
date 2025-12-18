from fastapi import FastAPI
from models.chat_ai import AskQuery
from services.chat_ai import ask_query
from dotenv import load_dotenv

app = FastAPI()


# This function will run when the server starts
@app.on_event("startup")
def startup_event():
    print("====== Performing startup tasks...=======")
    load_dotenv()


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
        },
    }


@app.get("/ping")
def ping():
    return {"message": "pong", "status": "success"}


@app.post("/ask")
def ask_question(payload: AskQuery):
    response = ask_query(payload.query)
    return {"query": payload.query, "response": response}
