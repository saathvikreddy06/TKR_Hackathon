from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.firebase import db
from app.retrieval import search_standards
from app.generation import generate_answer
from app.scope import is_bis_related, get_scope_response

app = FastAPI(
    title="StandIQ API",
    description="BIS Intelligent Assistant Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@app.get("/")
def root():
    return {
        "message": "StandIQ backend is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/firebase-test")
def firebase_test():

    test_ref = db.collection("system").document("connection_test")

    test_ref.set({
        "status": "connected"
    })

    return {
        "firebase": "connected",
        "firestore": "connected"
    }


@app.post("/api/search")
def search(request: SearchRequest):

    # ------------------------------------------
    # Scope check
    # ------------------------------------------

    if not is_bis_related(request.query):

        scope_response = get_scope_response()

        return {
            "query": request.query,
            "answer": scope_response["answer"],
            "sources": [],
            "in_scope": False
        }

    # ------------------------------------------
    # RAG retrieval
    # ------------------------------------------

    results = search_standards(
        query=request.query,
        limit=request.limit
    )

    # ------------------------------------------
    # Groq generation
    # ------------------------------------------

    generated = generate_answer(
        query=request.query,
        retrieved_results=results[:3]
    )

    return {
        "query": request.query,
        "answer": generated["answer"],
        "sources": generated["sources"],
        "in_scope": True
    }