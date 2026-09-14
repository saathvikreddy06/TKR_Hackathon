from fastapi import APIRouter, Depends

from app.auth.dependencies import require_admin
from app.firebase import db
from app.services.common import document_data
from app.routes.consultancies import safe_consultant_data


router = APIRouter(prefix="/api/admin", tags=["admin"])


def all_documents(collection: str):
    return [document_data(document) for document in db.collection(collection).stream()]


@router.get("/consultants")
def admin_consultants(current_user=Depends(require_admin)):
    consultants = []
    for document in db.collection("users").where("role", "==", "consultant").stream():
        data = document_data(document)
        safe_data = safe_consultant_data(data)
        safe_data["created_at"] = data.get("created_at")
        safe_data["updated_at"] = data.get("updated_at")
        consultants.append(safe_data)
    return {"consultants": consultants}


@router.get("/consultations")
def admin_consultations(current_user=Depends(require_admin)):
    return {"consultations": all_documents("consultation_requests")}


@router.get("/feedback")
def admin_feedback(current_user=Depends(require_admin)):
    return {"feedback": all_documents("feedback")}


@router.get("/stats")
def admin_stats(current_user=Depends(require_admin)):
    collections = {
        "consultations": "consultation_requests",
        "chat_sessions": "chat_sessions",
        "feedback": "feedback",
        "search_history": "search_history",
    }
    stats = {name: len(list(db.collection(collection).stream())) for name, collection in collections.items()}
    stats["consultants"] = len(list(db.collection("users").where("role", "==", "consultant").stream()))
    return stats