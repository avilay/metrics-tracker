import os

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.models import User
from app.repositories import get_connection
from app.repositories.user_repo import upsert_user

_firebase_app = None


def init_firebase() -> None:
    global _firebase_app
    if _firebase_app is not None:
        return

    cred_path = os.environ.get("FIREBASE_CREDENTIALS")
    if cred_path:
        cred = credentials.Certificate(cred_path)
    else:
        cred = credentials.ApplicationDefault()

    _firebase_app = firebase_admin.initialize_app(cred)


def verify_firebase_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded claims."""
    return firebase_auth.verify_id_token(id_token)


def verify_and_upsert_user(id_token: str, client_photo_url: str | None = None) -> User:
    """Verify token, create or update user in DB, return User."""
    claims = verify_firebase_token(id_token)
    firebase_uid = claims["uid"]
    is_anonymous = claims.get("firebase", {}).get("sign_in_provider") == "anonymous"
    display_name = claims.get("name")
    email = claims.get("email")
    photo_url = claims.get("picture") or client_photo_url

    conn = get_connection()
    try:
        return upsert_user(
            conn, firebase_uid, is_anonymous, display_name, email, photo_url
        )
    finally:
        conn.close()
        conn.close()
        conn.close()
