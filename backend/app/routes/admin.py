from fastapi import APIRouter, Depends

from app.auth.dependencies import require_admin
from app.firebase import db
from app.services.common import document_data


router = APIRouter(prefix="/api/admin", tags=["admin"])


def all_documents(collection: str):
    return [document_data(document) for document in db.collection(collection).stream()]


@router.get("/consultants")
def admin_consultants(current_user=Depends(require_admin)):
    return {"consultants": all_documents("consultancies")}


@router.get("/consultations")
def admin_consultations(current_user=Depends(require_admin)):
    return {"consultations": all_documents("consultation_requests")}


@router.get("/feedback")
def admin_feedback(current_user=Depends(require_admin)):
    return {"feedback": all_documents("feedback")}


@router.get("/stats")
def admin_stats(current_user=Depends(require_admin)):
    collections = {
        "consultants": "consultancies",
        "consultations": "consultation_requests",
        "chat_sessions": "chat_sessions",
        "feedback": "feedback",
        "search_history": "search_history",
    }
    stats = {name: len(list(db.collection(collection).stream())) for name, collection in collections.items()}
    return stats