import firebase_admin
from firebase_admin import credentials, firestore

import os

cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "credentials/firebase-service-account.json")

if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print(f"Warning: Firebase credentials file not found at '{cred_path}'. Database connection disabled.")
    db = None