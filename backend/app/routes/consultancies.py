from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.auth.dependencies import get_current_user
from app.firebase import db
from app.services.common import document_data, owns_or_admin, user_role


router = APIRouter(prefix="/api/consultants", tags=["consultants"])


class ConsultantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str | None = None
    bio: str = Field(default="", max_length=2000)
    expertise: list[str] = Field(default_factory=list, max_length=30)
    standards_handled: list[str] = Field(default_factory=list, max_length=100)
    categories: list[str] = Field(default_factory=list, max_length=30)
    availability: bool = True


class ConsultantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = None
    bio: str | None = Field(default=None, max_length=2000)
    expertise: list[str] | None = Field(default=None, max_length=30)
    standards_handled: list[str] | None = Field(default=None, max_length=100)
    categories: list[str] | None = Field(default=None, max_length=30)
    availability: bool | None = None
    active: bool | None = None


def can_manage(uid: str, consultant_id: str):
    return owns_or_admin(uid, consultant_id)


@router.get("")
def list_consultants(
    expertise: str | None = None,
    category: str | None = None,
    standard: str | None = None,
    available: bool | None = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
):
    consultants = []
    for document in db.collection("consultancies").stream():
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
        consultants.append(data)
    return {"consultants": consultants}


@router.get("/{consultant_id}")
def get_consultant(consultant_id: str):
    document = db.collection("consultancies").document(consultant_id).get()
    if not document.exists or document.to_dict().get("active", True) is False:
        raise HTTPException(status_code=404, detail="Consultant not found")
    return document_data(document)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_consultant(
    payload: ConsultantCreate,
    current_user=Depends(get_current_user),
):
    uid = current_user["uid"]
    if user_role(uid) not in {"consultant", "admin"}:
        raise HTTPException(status_code=403, detail="Consultant profile access required")
    reference = db.collection("consultancies").document(uid)
    if reference.get().exists:
        raise HTTPException(status_code=409, detail="Consultant profile already exists")
    data = payload.model_dump()
    data.update({
        "user_id": uid,
        "active": True,
        "created_at": SERVER_TIMESTAMP,
        "updated_at": SERVER_TIMESTAMP,
    })
    reference.set(data)
    return document_data(reference.get())


@router.put("/{consultant_id}")
def update_consultant(
    consultant_id: str,
    payload: ConsultantUpdate,
    current_user=Depends(get_current_user),
):
    document = db.collection("consultancies").document(consultant_id).get()
    if not document.exists:
        raise HTTPException(status_code=404, detail="Consultant not found")
    if not can_manage(current_user["uid"], consultant_id):
        raise HTTPException(status_code=403, detail="You cannot modify this consultant")
    updates = {key: value for key, value in payload.model_dump().items() if value is not None}
    if not updates:
        return document_data(document)
    updates["updated_at"] = SERVER_TIMESTAMP
    db.collection("consultancies").document(consultant_id).update(updates)
    return document_data(db.collection("consultancies").document(consultant_id).get())


@router.delete("/{consultant_id}")
def deactivate_consultant(
    consultant_id: str,
    current_user=Depends(get_current_user),
):
    document = db.collection("consultancies").document(consultant_id).get()
    if not document.exists:
        raise HTTPException(status_code=404, detail="Consultant not found")
    if not can_manage(current_user["uid"], consultant_id):
        raise HTTPException(status_code=403, detail="You cannot deactivate this consultant")
    db.collection("consultancies").document(consultant_id).update({
        "active": False,
        "updated_at": SERVER_TIMESTAMP,
    })
    return {"message": "Consultant deactivated"}