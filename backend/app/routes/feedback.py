from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.auth.dependencies import get_current_user
from app.firebase import db
from app.services.common import document_data, get_document


router = APIRouter(prefix="/api", tags=["feedback"])


class FeedbackCreate(BaseModel):
    consultation_id: str = Field(min_length=1, max_length=160)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def create_feedback(payload: FeedbackCreate, current_user=Depends(get_current_user)):
    consultation = get_document("consultation_requests", payload.consultation_id).to_dict() or {}
    uid = current_user["uid"]
    if consultation.get("user_id") != uid:
        raise HTTPException(status_code=403, detail="You can only review your own consultation")
    if consultation.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Feedback requires a completed consultation")
    existing = db.collection("feedback").where("consultation_id", "==", payload.consultation_id).stream()
    if any((document.to_dict() or {}).get("user_id") == uid for document in existing):
        raise HTTPException(status_code=409, detail="Feedback already submitted")
    reference = db.collection("feedback").document()
    reference.set({
        "consultation_id": payload.consultation_id,
        "user_id": uid,
        "consultant_id": consultation["consultant_id"],
        "rating": payload.rating,
        "comment": payload.comment.strip(),
        "created_at": SERVER_TIMESTAMP,
    })
    return document_data(reference.get())


@router.get("/feedback/my")
def list_my_feedback(current_user=Depends(get_current_user)):
    feedback = [
        document_data(document)
        for document in db.collection("feedback").where("user_id", "==", current_user["uid"]).stream()
    ]
    return {"feedback": feedback}


@router.get("/consultants/{consultant_id}/feedback")
def list_consultant_feedback(consultant_id: str, current_user=Depends(get_current_user)):
    if current_user["uid"] != consultant_id:
        raise HTTPException(status_code=403, detail="You can only view your own consultant feedback")
    feedback = [
        document_data(document)
        for document in db.collection("feedback").where("consultant_id", "==", consultant_id).stream()
    ]
    return {"feedback": feedback}