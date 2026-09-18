from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.firebase import db
from app.hybrid_retrieval import hybrid_retriever
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
        "https://sih-2026-one-kappa.vercel.app",
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

def normalize_hybrid_results(hybrid_results):
    normalized = []

    for item in hybrid_results.get("exact_standards", []):
        normalized.append({
            "standard_number": item.get("standard_number"),
            "part": item.get("part"),
            "year": item.get("published_on"),
            "title": item.get("title"),
            "source": item.get("source", "BIS Standards Catalogue"),
            "department": item.get("department"),
            "sectional_committee": item.get("sectional_committee"),
            "lab_name": None,
            "lab_code": None,
            "product": None,
            "clause": None,
            "testing_charge": None,
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "document_url": None,
            "source_url": None,
            "distance": None
        })

    for item in hybrid_results.get("semantic", []):
        metadata = item.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        normalized.append({
            "standard_number": (
                item.get("standard_number")
                or metadata.get("standard_number")
                or metadata.get("is_number")
                or metadata.get("indian_standard_no")
            ),
            "part": item.get("part") or metadata.get("part"),
            "section": item.get("section") or metadata.get("section"),
            "year": (
                item.get("published_on")
                or metadata.get("published_on")
                or metadata.get("year")
            ),
            "title": (
                item.get("title")
                or metadata.get("title")
                or metadata.get("standard_name")
            ),
            "source": item.get("source") or metadata.get("source") or "BIS Firestore Knowledge Base",
            "department": item.get("department") or metadata.get("department"),
            "sectional_committee": (
                item.get("sectional_committee")
                or metadata.get("sectional_committee")
            ),
            "product_category": item.get("product_category") or metadata.get("product_category"),
            "industry": item.get("industry") or metadata.get("industry"),
            "lab_name": None,
            "lab_code": None,
            "product": None,
            "clause": metadata.get("clause"),
            "testing_charge": None,
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": item.get("scheme") or metadata.get("scheme"),
            "mandatory_qco": item.get("mandatory_qco") or metadata.get("mandatory_qco"),
            "status": item.get("status") or metadata.get("status"),
            "document_url": item.get("document_url") or metadata.get("document_url"),
            "source_url": item.get("source_url") or metadata.get("source_url"),
            "distance": item.get("distance"),
            "similarity": item.get("similarity"),
            "match_type": item.get("match_type", "firebase_semantic"),
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("document_id"),
            "text": item.get("text") or ""
        })

    for item in hybrid_results.get("qco", []):
        normalized.append({
            "standard_number": item.get("standard_number"),
            "part": None,
            "year": None,
            "title": None,
            "source": item.get("source", "BIS QCO data"),
            "department": None,
            "sectional_committee": None,
            "lab_name": None,
            "lab_code": None,
            "product": None,
            "clause": None,
            "testing_charge": None,
            "qco_document_id": item.get("qco_document_id"),
            "relationship": item.get("relationship"),
            "order_number": item.get("order_number"),
            "order_date": item.get("order_date"),
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "document_url": None,
            "source_url": None,
            "distance": None,
            "evidence": item.get("evidence"),
            "confidence": item.get("confidence"),
            "matched_is_numbers": item.get("matched_is_numbers")
        })

    for item in hybrid_results.get("labs", []):
        normalized.append({
            "standard_number": item.get("standard_number"),
            "part": None,
            "year": None,
            "title": None,
            "source": item.get("source", "BIS LIMS"),
            "department": None,
            "sectional_committee": None,
            "lab_name": item.get("lab_name"),
            "lab_code": item.get("lab_code"),
            "product": item.get("product"),
            "clause": item.get("clause"),
            "testing_charge": item.get("testing_charge"),
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "document_url": None,
            "source_url": item.get("scope_url"),
            "distance": None,
            "effective_date": item.get("effective_date"),
            "remark": item.get("remark"),
            "designation": item.get("designation")
        })

    return normalized

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

    retrieval_query = prepare_retrieval_query(
        request.query,
        language
    )

    if hybrid_retriever is None:
        raise HTTPException(
            status_code=503,
            detail="BIS retrieval is unavailable because the retriever failed to initialize.",
        )

    try:
        hybrid_results = hybrid_retriever.search(
            retrieval_query,
            semantic_limit=request.limit,
            lab_limit=20
        )
    except Exception as exc:
        print(f"BIS retrieval error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=503,
            detail=(
                "BIS semantic retrieval is temporarily unavailable. "
                "Please try again shortly."
            ),
        ) from exc

    results = normalize_hybrid_results(hybrid_results)


    # --------------------------------------------------------
    # GROQ GENERATION
    # --------------------------------------------------------

    generated = generate_answer(
        query=request.query,
        retrieved_results=hybrid_results,
        language=language
    )


    # --------------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------------

    response = {
        "query": request.query,
        "answer": generated.get("answer", ""),
        "title": generated.get("title"),
        "summary": generated.get("summary"),
        "sections": generated.get("sections", []),
        "sources": generated.get("sources", []),
        "followups": generated.get("followups", []),
        "evidence_status": generated.get("evidence_status", "supported" if generated.get("sources") else "insufficient"),
        "in_scope": True,
        **response_language
    }


    # --------------------------------------------------------
    # SAVE SEARCH HISTORY
    # --------------------------------------------------------

    if current_user and db:

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