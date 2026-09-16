from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.firebase import db
from app.hybrid_retrieval import HybridRetriever
hybrid_retriever = HybridRetriever()
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


app = FastAPI(
    title="StandIQ API",
    description="BIS Intelligent Assistant Backend",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://sih-2026-nu-liard.vercel.app",
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
    language: str | None = None


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
            "designation": None,
            "clause": None,
            "testing_charge": None,
            "testing_charge_raw": None,
            "effective_date": None,
            "remark": None,
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
            "designation": None,
            "clause": None,
            "testing_charge": None,
            "testing_charge_raw": None,
            "effective_date": None,
            "remark": None,
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "document_url": None,
            "source_url": None,
            "distance": item.get("score"),
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("document_id")
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
            "designation": None,
            "clause": None,
            "testing_charge": None,
            "testing_charge_raw": None,
            "effective_date": None,
            "remark": None,
            "qco_document_id": item.get("qco_document_id"),
            "relationship": item.get("relationship"),
            "order_number": item.get("order_number"),
            "order_date": item.get("order_date"),
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "document_url": None,
            "source_url": item.get("source"),
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
            "designation": item.get("designation"),
            "clause": item.get("clause"),
            "testing_charge": item.get("testing_charge"),
            "testing_charge_raw": item.get("testing_charge_raw"),
            "effective_date": item.get("effective_date"),
            "remark": item.get("remark"),
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "document_url": None,
            "source_url": item.get("scope_url"),
            "distance": None
        })

    for item in hybrid_results.get("tests", []):
        normalized.append({
            "standard_number": item.get("standard_number"),
            "part": None,
            "year": None,
            "title": item.get("title"),
            "source": item.get("source", "BIS LIMS"),
            "department": None,
            "sectional_committee": None,
            "lab_name": item.get("lab_name"),
            "lab_code": item.get("lab_code"),
            "product": item.get("product"),
            "designation": item.get("designation"),
            "clause": item.get("clause"),
            "testing_charge": item.get("testing_charge"),
            "testing_charge_raw": item.get("testing_charge_raw"),
            "effective_date": item.get("effective_date"),
            "remark": item.get("remark"),
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "document_url": None,
            "source_url": item.get("source"),
            "distance": None
        })

    return normalized


@app.post("/api/search")
def search(
    request: SearchRequest,
    current_user=Depends(get_optional_current_user)
):

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

    detected_language = detect_language(request.query)

    language = (
        request.language
        or detected_language["language"]
    )

    response_language = {
        "language": language,
        "language_name": {
            "en": "English",
            "hi": "Hindi",
            "te": "Telugu",
        }[language],
    }

    if not is_bis_related(request.query):

        scope_response = get_scope_response(language)

        return {
            "query": request.query,
            "answer": scope_response["answer"],
            "sources": [],
            "in_scope": False,
            **response_language
        }

    retrieval_query = prepare_retrieval_query(
        request.query,
        language
    )

    hybrid_results = hybrid_retriever.search(
        retrieval_query,
        semantic_limit=request.limit,
        lab_limit=20
    )

    results = normalize_hybrid_results(hybrid_results)

    generated = generate_answer(
        query=request.query,
        retrieved_results=hybrid_results,
        language=language
    )

    response = {
        "query": request.query,
        "answer": generated["answer"],
        "sources": generated["sources"],
        "in_scope": True,
        **response_language
    }

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


@app.get("/api/auth/me")
def get_me(
    current_user=Depends(get_current_user)
):

    return {
        "uid": current_user["uid"],
        "email": current_user.get("email")
    }
