from datetime import datetime

from fastapi import HTTPException

from app.firebase import db


def serialize_value(value):
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def document_data(document):
    data = document.to_dict() or {}
    data["id"] = document.id
    return serialize_value(data)


def get_document(collection: str, document_id: str):
    document = db.collection(collection).document(document_id).get()
    if not document.exists:
        raise HTTPException(status_code=404, detail=f"{collection} record not found")
    return document


def user_role(uid: str):
    user = db.collection("users").document(uid).get()
    return user.to_dict().get("role") if user.exists else None


def owns_or_admin(uid: str, owner_id: str):
    if uid == owner_id:
        return True
    admin = db.collection("admins").document(uid).get()
    return admin.exists and admin.to_dict().get("active", True) is not False