from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.auth.dependencies import get_current_user
from app.firebase import db
from app.services.common import document_data, owns_or_admin


def safe_consultant_data(data: dict) -> dict:
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "consultancy_name": data.get("consultancy_name"),
        "consultancy_area": data.get("consultancy_area"),
        "place": data.get("place"),
        "bio": data.get("bio"),
        "expertise": data.get("expertise", []),
        "standards_handled": data.get("standards_handled", []),
        "categories": data.get("categories", []),
        "availability": data.get("availability", True),
        "profile_complete": data.get("profile_complete", False),
        "active": data.get("active", True),
    }


router = APIRouter(prefix="/api/consultants", tags=["consultants"])


class ConsultantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    consultancy_name: str = Field(min_length=2, max_length=160)
    consultancy_area: str = Field(min_length=2, max_length=160)
    place: str = Field(min_length=2, max_length=160)
    bio: str = Field(default="", max_length=2000)
    expertise: list[str] = Field(default_factory=list, max_length=30)
    standards_handled: list[str] = Field(default_factory=list, max_length=100)
    categories: list[str] = Field(default_factory=list, max_length=30)
    availability: bool = True


class ConsultantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    consultancy_name: str | None = Field(default=None, min_length=2, max_length=160)
    consultancy_area: str | None = Field(default=None, min_length=2, max_length=160)
    place: str | None = Field(default=None, min_length=2, max_length=160)
    bio: str | None = Field(default=None, max_length=2000)
    expertise: list[str] | None = Field(default=None, max_length=30)
    standards_handled: list[str] | None = Field(default=None, max_length=100)
    categories: list[str] | None = Field(default=None, max_length=30)
    availability: bool | None = None
    active: bool | None = None


def can_manage(uid: str, consultant_id: str):
    return owns_or_admin(uid, consultant_id)


def profile_is_complete(data: dict) -> bool:
    required_fields = ("name", "email", "consultancy_name", "consultancy_area", "place")
    return all(str(data.get(field, "")).strip() for field in required_fields)


@router.get("")
def list_consultants(
    expertise: str | None = None,
    category: str | None = None,
    standard: str | None = None,
    available: bool | None = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
):
    consultants = []
    for document in db.collection("users").where("role", "==", "consultant").stream():
        data = document_data(document)
        if data.get("active", True) is False:
            continue
        if available is not None and data.get("availability", False) != available:
            continue
        if expertise and expertise.lower() not in [item.lower() for item in data.get("expertise", [])]:
            continue
        if category and category.lower() not in [item.lower() for item in data.get("categories", [])]:
            continue
        if standard and standard.lower() not in [item.lower() for item in data.get("standards_handled", [])]:
            continue
        if search:
            haystack = " ".join([
                data.get("name", ""),
                data.get("bio", ""),
                *data.get("expertise", []),
                *data.get("categories", []),
                *data.get("standards_handled", []),
            ]).lower()
            if search.lower() not in haystack:
                continue
        data["profile_complete"] = profile_is_complete(data)
        safe_data = safe_consultant_data(data)
        safe_data.pop("phone", None)
        consultants.append(safe_data)
    return {"consultants": consultants}


@router.get("/me/profile")
def get_my_consultant_profile(current_user=Depends(get_current_user)):
    document = db.collection("users").document(current_user["uid"]).get()
    if not document.exists or document.to_dict().get("role") != "consultant":
        return {"profile": None, "profile_complete": False}
    data = document_data(document)
    data["profile_complete"] = profile_is_complete(data)
    safe_data = safe_consultant_data(data)
    return {"profile": safe_data, "profile_complete": data["profile_complete"]}


@router.get("/{consultant_id}")
def get_consultant(consultant_id: str):
    document = db.collection("users").document(consultant_id).get()
    if not document.exists or document.to_dict().get("role") != "consultant" or document.to_dict().get("active", True) is False:
        raise HTTPException(status_code=404, detail="Consultant not found")
    data = document_data(document)
    data["profile_complete"] = profile_is_complete(data)
    safe_data = safe_consultant_data(data)
    safe_data.pop("phone", None)
    return safe_data


@router.post("", status_code=status.HTTP_201_CREATED)
def create_consultant(
    payload: ConsultantCreate,
    current_user=Depends(get_current_user),
):
    uid = current_user["uid"]
    reference = db.collection("users").document(uid)
    document = reference.get()

    if not document.exists:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = document.to_dict() or {}
    if user_data.get("role") not in {"consultant", "admin"}:
        raise HTTPException(status_code=403, detail="Consultant profile access required")

    data = payload.model_dump()
    data["email"] = data.get("email") or current_user.get("email")
    data["profile_complete"] = profile_is_complete(data)
    data["role"] = "consultant"
    data.update({
        "active": True,
        "updated_at": SERVER_TIMESTAMP,
    })

    reference.set(data, merge=True)
    updated_doc = reference.get()
    updated_data = document_data(updated_doc)
    updated_data["profile_complete"] = profile_is_complete(updated_data)
    return safe_consultant_data(updated_data)


@router.put("/{consultant_id}")
def update_consultant(
    consultant_id: str,
    payload: ConsultantUpdate,
    current_user=Depends(get_current_user),
):
    document = db.collection("users").document(consultant_id).get()
    if not document.exists or document.to_dict().get("role") != "consultant":
        raise HTTPException(status_code=404, detail="Consultant not found")
    if not can_manage(current_user["uid"], consultant_id):
        raise HTTPException(status_code=403, detail="You cannot modify this consultant")

    updates = {key: value for key, value in payload.model_dump().items() if value is not None}
    if not updates:
        data = document_data(document)
        data["profile_complete"] = profile_is_complete(data)
        return safe_consultant_data(data)

    updates.pop("role", None)
    updates["updated_at"] = SERVER_TIMESTAMP

    existing_data = document.to_dict() or {}
    for k, v in updates.items():
        if k != "updated_at":
            existing_data[k] = v
    updates["profile_complete"] = profile_is_complete(existing_data)

    db.collection("users").document(consultant_id).update(updates)

    updated_doc = db.collection("users").document(consultant_id).get()
    updated_data = document_data(updated_doc)
    updated_data["profile_complete"] = updates["profile_complete"]
    return safe_consultant_data(updated_data)


@router.delete("/{consultant_id}")
def deactivate_consultant(
    consultant_id: str,
    current_user=Depends(get_current_user),
):
    document = db.collection("users").document(consultant_id).get()
    if not document.exists or document.to_dict().get("role") != "consultant":
        raise HTTPException(status_code=404, detail="Consultant not found")
    if not can_manage(current_user["uid"], consultant_id):
        raise HTTPException(status_code=403, detail="You cannot deactivate this consultant")
    db.collection("users").document(consultant_id).update({
        "active": False,
        "updated_at": SERVER_TIMESTAMP,
    })
    return {"message": "Consultant deactivated"}
