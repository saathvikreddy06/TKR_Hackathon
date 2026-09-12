from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.firebase import db
from app.retrieval import search_standards
from app.generation import generate_answer
from app.scope import is_bis_related, get_scope_response
from app.language import detect_language, prepare_retrieval_query

from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_optional_current_user

from app.routes.consultancies import router as consultancies_router
from app.routes.consultations import router as consultations_router
from app.routes.chat import router as chat_router
from app.routes.feedback import router as feedback_router
from app.routes.history import router as history_router
from app.routes.admin import router as admin_router


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="StandIQ API",
    description="BIS Intelligent Assistant Backend",
    version="1.0.0"
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local development
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        # Production frontend
        "https://sih-2026-nu-liard.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(consultancies_router)
app.include_router(consultations_router)
app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(history_router)
app.include_router(admin_router)


# ============================================================
# REQUEST MODELS
# ============================================================

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    language: str | None = None


# ============================================================
# BASIC ENDPOINTS
# ============================================================

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


# ============================================================
# FIREBASE CONNECTION TEST
# ============================================================

@app.get("/firebase-test")
def firebase_test():

    if not db:
        return {
            "firebase": "disconnected",
            "firestore": "disconnected",
            "reason": "No credentials configured"
        }

    test_ref = db.collection("system").document("connection_test")

    test_ref.set({
        "status": "connected"
    })

    return {
        "firebase": "connected",
        "firestore": "connected"
    }


# ============================================================
# STANDIQ SEARCH / RAG ENDPOINT
# ============================================================

@app.post("/api/search")
def search(
    request: SearchRequest,
    current_user=Depends(get_optional_current_user)
):

    # --------------------------------------------------------
    # Supported languages
    # --------------------------------------------------------

    supported_languages = {
        "en",
        "te",
        "hi"
    }

    if (
        request.language is not None
        and request.language not in supported_languages
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported language. "
                "Supported languages are: en, te, hi"
            ),
        )


    # --------------------------------------------------------
    # Detect language
    # --------------------------------------------------------

    detected_language = detect_language(request.query)

    language = (
        request.language
        or detected_language["language"]
    )


    # --------------------------------------------------------
    # Response language information
    # --------------------------------------------------------

    response_language = {
        "language": language,
        "language_name": {
            "en": "English",
            "hi": "Hindi",
            "te": "Telugu",
        }[language],
    }


    # --------------------------------------------------------
    # Scope check
    # --------------------------------------------------------

    if not is_bis_related(request.query):

        scope_response = get_scope_response(language)

        return {
            "query": request.query,
            "answer": scope_response["answer"],
            "sources": [],
            "in_scope": False,
            **response_language
        }


    # --------------------------------------------------------
    # RAG RETRIEVAL
    # --------------------------------------------------------

    results = search_standards(
        query=prepare_retrieval_query(
            request.query,
            language
        ),
        limit=request.limit
    )


    # --------------------------------------------------------
    # GROQ GENERATION
    # --------------------------------------------------------

    generated = generate_answer(
        query=request.query,
        retrieved_results=results[:3],
        language=language
    )


    # --------------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------------

    response = {
        "query": request.query,
        "answer": generated["answer"],
        "sources": generated["sources"],
        "in_scope": True,
        **response_language
    }


    # --------------------------------------------------------
    # SAVE SEARCH HISTORY
    # --------------------------------------------------------

    if current_user:

        db.collection("search_history").document().set({
            "user_id": current_user["uid"],
            "query": request.query,
            "answer": generated["answer"],
            "language": language,
            "sources": [
                source.get("standard_number")
                or source.get("id")
                for source in generated["sources"]
            ],
            "created_at": SERVER_TIMESTAMP,
        })


    return response


# ============================================================
# AUTHENTICATED USER ENDPOINT
# ============================================================

@app.get("/api/auth/me")
def get_me(
    current_user=Depends(get_current_user)
):

    return {
        "uid": current_user["uid"],
        "email": current_user.get("email")
    }