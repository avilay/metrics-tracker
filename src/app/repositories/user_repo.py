import sqlite3
import time

from app.models import User


def upsert_user(
    conn: sqlite3.Connection,
    firebase_uid: str,
    is_anonymous: bool,
    display_name: str | None = None,
    email: str | None = None,
    photo_url: str | None = None,
) -> User:
    row = conn.execute(
        "SELECT * FROM users WHERE firebase_uid = ?", (firebase_uid,)
    ).fetchone()

    if row:
        if not is_anonymous:
            conn.execute(
                "UPDATE users SET is_anonymous = 0, display_name = ?, email = ?, photo_url = ? WHERE id = ?",
                (display_name, email, photo_url, row["id"]),
            )
            conn.commit()
        return User(
            id=row["id"],
            firebase_uid=row["firebase_uid"],
            display_name=display_name or row["display_name"],
            email=email or row["email"],
            photo_url=photo_url or row["photo_url"],
            is_anonymous=is_anonymous,
            created_at=row["created_at"],
        )

    now = int(time.time())
    cursor = conn.execute(
        "INSERT INTO users (firebase_uid, display_name, email, photo_url, is_anonymous, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (firebase_uid, display_name, email, photo_url, is_anonymous, now),
    )
    conn.commit()
    return User(
        id=cursor.lastrowid,
        firebase_uid=firebase_uid,
        display_name=display_name,
        email=email,
        photo_url=photo_url,
        is_anonymous=is_anonymous,
        created_at=now,
    )


def get_user_by_firebase_uid(
    conn: sqlite3.Connection, firebase_uid: str
) -> User | None:
    print(f"Fetching user {firebase_uid}")
    row = conn.execute(
        "SELECT * FROM users WHERE firebase_uid = ?", (firebase_uid,)
    ).fetchone()
    if not row:
        return None
    return User(
        id=row["id"],
        firebase_uid=row["firebase_uid"],
        display_name=row["display_name"],
        email=row["email"],
        photo_url=row["photo_url"],
        is_anonymous=bool(row["is_anonymous"]),
        created_at=row["created_at"],
    )
