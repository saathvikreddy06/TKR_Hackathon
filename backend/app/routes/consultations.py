from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.auth.dependencies import get_current_user
from app.firebase import db
from app.services.common import document_data, get_document, user_role


router = APIRouter(prefix="/api/consultations", tags=["consultations"])

VALID_STATUSES = {"pending", "accepted", "rejected", "cancelled", "active", "completed"}
TRANSITIONS = {
    "pending": {"accepted", "rejected", "cancelled"},
    "accepted": {"active"},
    "active": {"completed"},
    "rejected": set(),
    "cancelled": set(),
    "completed": set(),
}


class ConsultationCreate(BaseModel):
    consultant_id: str = Field(min_length=1, max_length=160)
    subject: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=2, max_length=4000)


def consultation_data(consultation_id: str):
    return document_data(get_document("consultation_requests", consultation_id))


def ensure_participant(data: dict, uid: str):
    if uid not in {data.get("user_id"), data.get("consultant_id")}:
        raise HTTPException(status_code=403, detail="You cannot access this consultation")


def ensure_transition(data: dict, target: str):
    current = data.get("status")
    if target not in VALID_STATUSES or target not in TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition consultation from {current} to {target}",
        )


def update_status(consultation_id: str, target: str, current_user: dict):
    reference = db.collection("consultation_requests").document(consultation_id)
    document = get_document("consultation_requests", consultation_id)
    data = document.to_dict() or {}
    uid = current_user["uid"]
    role = user_role(uid)
    ensure_participant(data, uid)
    if target == "cancelled" and (uid != data.get("user_id") or data.get("status") != "pending"):
        raise HTTPException(status_code=403, detail="Only the requesting user can cancel a pending request")
    if target in {"accepted", "rejected", "active", "completed"} and uid != data.get("consultant_id"):
        raise HTTPException(status_code=403, detail="Only the assigned consultant can perform this action")
    if role != "consultant" and target != "cancelled":
        raise HTTPException(status_code=403, detail="Consultant access required")
    ensure_transition(data, target)
    updates = {"status": target, "updated_at": SERVER_TIMESTAMP}
    if target == "accepted":
        updates["accepted_at"] = SERVER_TIMESTAMP
    if target == "completed":
        updates["completed_at"] = SERVER_TIMESTAMP
    reference.update(updates)
    return consultation_data(consultation_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_consultation(
    payload: ConsultationCreate,
    current_user=Depends(get_current_user),
):
    uid = current_user["uid"]
    consultant = get_document("consultancies", payload.consultant_id)
    consultant_data = consultant.to_dict() or {}
    if consultant_data.get("active", True) is False:
        raise HTTPException(status_code=409, detail="Consultant is inactive")
    existing_requests = db.collection("consultation_requests").where("user_id", "==", uid).stream()
    for existing in existing_requests:
        existing_data = existing.to_dict() or {}
        if (
            existing_data.get("consultant_id") == payload.consultant_id
            and existing_data.get("status") == "pending"
        ):
            raise HTTPException(
                status_code=409,
                detail="A pending consultation already exists with this consultant",
            )
    reference = db.collection("consultation_requests").document()
    reference.set({
        "user_id": uid,
        "consultant_id": payload.consultant_id,
        "subject": payload.subject,
        "description": payload.description,
        "status": "pending",
        "created_at": SERVER_TIMESTAMP,
        "updated_at": SERVER_TIMESTAMP,
        "accepted_at": None,
        "completed_at": None,
    })
    return consultation_data(reference.id)


@router.get("/my")
def list_my_consultations(current_user=Depends(get_current_user)):
    uid = current_user["uid"]
    role = user_role(uid)
    results = []
    for document in db.collection("consultation_requests").stream():
        data = document_data(document)
        if data.get("user_id") == uid or (role == "consultant" and data.get("consultant_id") == uid):
            results.append(data)
    return {"consultations": results}


@router.get("/{consultation_id}")
def get_consultation(consultation_id: str, current_user=Depends(get_current_user)):
    data = consultation_data(consultation_id)
    ensure_participant(data, current_user["uid"])
    return data


@router.put("/{consultation_id}/accept")
def accept_consultation(consultation_id: str, current_user=Depends(get_current_user)):
    return update_status(consultation_id, "accepted", current_user)


@router.put("/{consultation_id}/reject")
def reject_consultation(consultation_id: str, current_user=Depends(get_current_user)):
    return update_status(consultation_id, "rejected", current_user)


@router.put("/{consultation_id}/start")
def start_consultation(consultation_id: str, current_user=Depends(get_current_user)):
    return update_status(consultation_id, "active", current_user)


@router.put("/{consultation_id}/complete")
def complete_consultation(consultation_id: str, current_user=Depends(get_current_user)):
    return update_status(consultation_id, "completed", current_user)


@router.put("/{consultation_id}/cancel")
def cancel_consultation(consultation_id: str, current_user=Depends(get_current_user)):
    return update_status(consultation_id, "cancelled", current_user)