from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.auth.dependencies import get_current_user
from app.firebase import db
from app.services.common import document_data, get_document


router = APIRouter(prefix="/api/chat", tags=["chat"])


class SessionCreate(BaseModel):
    consultation_id: str = Field(min_length=1, max_length=160)


class MessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


def session_data(session_id: str):
    return document_data(get_document("chat_sessions", session_id))


def ensure_session_member(data: dict, uid: str):
    if uid not in {data.get("user_id"), data.get("consultant_id")}:
        raise HTTPException(status_code=403, detail="You cannot access this chat")


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, current_user=Depends(get_current_user)):
    consultation = get_document("consultation_requests", payload.consultation_id)
    consultation_data = consultation.to_dict() or {}
    uid = current_user["uid"]
    if uid not in {consultation_data.get("user_id"), consultation_data.get("consultant_id")}:
        raise HTTPException(status_code=403, detail="You cannot create this chat")
    if consultation_data.get("status") not in {"accepted", "active"}:
        raise HTTPException(status_code=409, detail="Chat requires an accepted consultation")
    existing = db.collection("chat_sessions").where("consultation_id", "==", payload.consultation_id).stream()
    for document in existing:
        if (document.to_dict() or {}).get("status") != "closed":
            return document_data(document)
    reference = db.collection("chat_sessions").document()
    reference.set({
        "consultation_id": payload.consultation_id,
        "user_id": consultation_data["user_id"],
        "consultant_id": consultation_data["consultant_id"],
        "status": "active",
        "created_at": SERVER_TIMESTAMP,
        "closed_at": None,
    })
    return session_data(reference.id)


@router.get("/sessions")
def list_sessions(current_user=Depends(get_current_user)):
    uid = current_user["uid"]
    sessions = []
    for document in db.collection("chat_sessions").stream():
        data = document_data(document)
        if uid in {data.get("user_id"), data.get("consultant_id")}:
            sessions.append(data)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, current_user=Depends(get_current_user)):
    data = session_data(session_id)
    ensure_session_member(data, current_user["uid"])
    return data


@router.post("/sessions/{session_id}/messages", status_code=status.HTTP_201_CREATED)
def send_message(
    session_id: str,
    payload: MessageCreate,
    current_user=Depends(get_current_user),
):
    session = session_data(session_id)
    ensure_session_member(session, current_user["uid"])
    if session.get("status") != "active":
        raise HTTPException(status_code=409, detail="Chat session is closed")
    sender_role = "user" if current_user["uid"] == session["user_id"] else "consultant"
    reference = db.collection("chat_messages").document()
    reference.set({
        "session_id": session_id,
        "sender_id": current_user["uid"],
        "sender_role": sender_role,
        "message": payload.message.strip(),
        "created_at": SERVER_TIMESTAMP,
    })
    return document_data(reference.get())


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: str, current_user=Depends(get_current_user)):
    session = session_data(session_id)
    ensure_session_member(session, current_user["uid"])
    messages = [
        document_data(document)
        for document in db.collection("chat_messages").where("session_id", "==", session_id).stream()
    ]
    messages.sort(key=lambda message: message.get("created_at", ""))
    return {"messages": messages}


@router.put("/sessions/{session_id}/close")
def close_session(session_id: str, current_user=Depends(get_current_user)):
    session = session_data(session_id)
    ensure_session_member(session, current_user["uid"])
    if session.get("status") == "closed":
        return session
    reference = db.collection("chat_sessions").document(session_id)
    reference.update({"status": "closed", "closed_at": SERVER_TIMESTAMP})
    return session_data(session_id)