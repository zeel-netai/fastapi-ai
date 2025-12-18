from fastapi import FastAPI

app = FastAPI()


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
async def ping():
    return {"message": "pong", "status": "success"}


@app.get("/ask")
async def ask_question(question: str):
    return {"question": question, "answer": "This is a placeholder answer from the AI."}
