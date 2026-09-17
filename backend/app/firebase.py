import json
import os

import firebase_admin
from firebase_admin import credentials, firestore


def initialize_firebase():
    if firebase_admin._apps:
        return firestore.client()

    # ---------------------------------------------------------
    # Render / production:
    # Store the complete Firebase service-account JSON in
    # FIREBASE_SERVICE_ACCOUNT_JSON.
    # ---------------------------------------------------------
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    if service_account_json:
        try:
            service_account_info = json.loads(service_account_json)
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized using environment credentials.")
            return firestore.client()
        except Exception as exc:
            print(f"Warning: Firebase environment credentials failed: {exc}")
            return None

    # ---------------------------------------------------------
    # Local development:
    # Use FIREBASE_CREDENTIALS_PATH if provided, otherwise use
    # the existing default location.
    # ---------------------------------------------------------
    cred_path = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        "credentials/firebase-service-account.json",
    )

    if os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print(f"Firebase initialized using credentials file: {cred_path}")
            return firestore.client()
        except Exception as exc:
            print(f"Warning: Firebase credentials file failed: {exc}")
            return None

    print(
        f"Warning: Firebase credentials not found at '{cred_path}'. "
        "Database connection disabled."
    )
    return None


db = initialize_firebase()