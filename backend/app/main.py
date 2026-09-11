from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.firebase import db
from app.retrieval import search_standards
from app.generation import generate_answer
from app.scope import is_bis_related, get_scope_response
from app.language import detect_language, prepare_retrieval_query
from fastapi import FastAPI, Depends
from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_optional_current_user
from app.routes.consultancies import router as consultancies_router
from app.routes.consultations import router as consultations_router
from app.routes.chat import router as chat_router
from app.routes.feedback import router as feedback_router
from app.routes.history import router as history_router
from app.routes.admin import router as admin_router
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

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

app.include_router(consultancies_router)
app.include_router(consultations_router)
app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(history_router)
app.include_router(admin_router)

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
    if not db:
        return {"firebase": "disconnected", "firestore": "disconnected", "reason": "No credentials configured"}

    test_ref = db.collection("system").document("connection_test")

    test_ref.set({
        "status": "connected"
    })

    return {
        "firebase": "connected",
        "firestore": "connected"
    }


@app.post("/api/search")
def search(request: SearchRequest, current_user=Depends(get_optional_current_user)):

    detected_language = detect_language(request.query)
    language = detected_language["language"]

    # ------------------------------------------
    # Scope check
    # ------------------------------------------

    if not is_bis_related(request.query):

        scope_response = get_scope_response(language)

        return {
            "query": request.query,
            "answer": scope_response["answer"],
            "sources": [],
            "in_scope": False,
            **detected_language
        }

    # ------------------------------------------
    # RAG retrieval
    # ------------------------------------------

    results = search_standards(
        query=prepare_retrieval_query(request.query, language),
        limit=request.limit
    )

    # ------------------------------------------
    # Groq generation
    # ------------------------------------------

    generated = generate_answer(
        query=request.query,
        retrieved_results=results[:3],
        language=language
    )

    response = {
        "query": request.query,
        "answer": generated["answer"],
        "sources": generated["sources"],
        "in_scope": True,
        **detected_language
    }

    if current_user:
        db.collection("search_history").document().set({
            "user_id": current_user["uid"],
            "query": request.query,
            "answer": generated["answer"],
            "sources": [
                source.get("standard_number") or source.get("id")
                for source in generated["sources"]
            ],
            "created_at": SERVER_TIMESTAMP,
        })

    return response

@app.get("/api/auth/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "uid": current_user["uid"],
        "email": current_user.get("email")
    }