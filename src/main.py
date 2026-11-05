import os
from fastapi import FastAPI

app = FastAPI(
    title="Orquestrador de Roles - RAG API",
    description="API do Orquestrador de Roles (Grupo 7 - Challenge 2)",
    version="0.1.0"
)

@app.get("/")
def home():
    return {
        "projeto": "Orquestrador de Roles",
        "status": "online",
        "ambiente": os.environ.get("ENVIRONMENT", "producao"),
        "responsavel_devops": "Maria Eduarda",
        "doc": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
