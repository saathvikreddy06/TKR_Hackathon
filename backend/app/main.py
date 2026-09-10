from fastapi import FastAPI
from pydantic import BaseModel

from app.firebase import db
from app.retrieval import search_standards
from app.generation import generate_answer


app = FastAPI(
    title="StandIQ API",
    description="BIS Intelligent Assistant Backend",
    version="1.0.0"
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

    results = search_standards(
        query=request.query,
        limit=request.limit
    )

    generated = generate_answer(
        query=request.query,
        retrieved_results=results
    )

    return {
        "query": request.query,
        "answer": generated["answer"],
        "sources": generated["sources"],
        "retrieved_results": results
    }