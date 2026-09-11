from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.firebase import db
from app.services.common import document_data, get_document


router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history(current_user=Depends(get_current_user)):
    history = [
        document_data(document)
        for document in db.collection("search_history").where("user_id", "==", current_user["uid"]).stream()
    ]
    history.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"history": history}


@router.delete("/{history_id}")
def delete_history(history_id: str, current_user=Depends(get_current_user)):
    document = get_document("search_history", history_id)
    if (document.to_dict() or {}).get("user_id") != current_user["uid"]:
        raise HTTPException(status_code=403, detail="You cannot delete this history item")
    document.reference.delete()
    return {"message": "History item deleted"}


@router.delete("")
def clear_history(current_user=Depends(get_current_user)):
    documents = list(db.collection("search_history").where("user_id", "==", current_user["uid"]).stream())
    batch = db.batch()
    for document in documents:
        batch.delete(document.reference)
    if documents:
        batch.commit()
    return {"deleted": len(documents)}