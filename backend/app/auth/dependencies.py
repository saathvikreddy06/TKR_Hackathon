from fastapi import Depends, Header, HTTPException
from firebase_admin import auth
from app.firebase import db


def get_current_user(
    authorization: str | None = Header(default=None)
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header"
        )

    token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header"
        )

    try:
        decoded_token = auth.verify_id_token(token)

        return decoded_token

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Firebase ID token"
        )


def get_optional_current_user(
    authorization: str | None = Header(default=None)
):
    if not authorization:
        return None
    return get_current_user(authorization)


def get_user_role(uid: str) -> str | None:
    profile = db.collection("users").document(uid).get()
    if not profile.exists:
        return None
    return profile.to_dict().get("role")


def require_consultant(current_user=Depends(get_current_user)):
    role = get_user_role(current_user["uid"])
    if role != "consultant":
        raise HTTPException(status_code=403, detail="Consultant access required")
    return current_user


def require_admin(current_user=Depends(get_current_user)):
    admin = db.collection("admins").document(current_user["uid"]).get()
    if not admin.exists or admin.to_dict().get("active", True) is False:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user