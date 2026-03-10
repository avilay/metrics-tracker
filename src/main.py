import hashlib
import os
from pathlib import Path

import httpx
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from nicegui import app, ui

import metrics_tracker.pages.welcome  # noqa: F401 — registers /welcome route
from metrics_tracker.components.layout import page_layout
from metrics_tracker.pages import (
    account_page,
    dashboard_page,
    dummy_page,
    new_metric_page,
)

PHOTO_CACHE_DIR = Path(__file__).parent / ".photo_cache"


def setup_auth_endpoints() -> None:
    """Register auth-related endpoints on the FastAPI app."""

    PHOTO_CACHE_DIR.mkdir(exist_ok=True)

    @app.get("/auth/photo/{filename}")
    async def get_photo(filename: str):
        path = PHOTO_CACHE_DIR / filename
        if path.exists():
            return FileResponse(path, media_type="image/jpeg")
        return JSONResponse({"error": "not found"}, status_code=404)

    @app.post("/auth/sign-out")
    async def sign_out(request: Request) -> JSONResponse:
        storage = app.storage.user
        storage.clear()
        return JSONResponse({"status": "ok"})

    @app.post("/auth/firebase-token")
    async def firebase_token(request: Request) -> JSONResponse:
        try:
            body = await request.json()
            id_token = body.get("token")
            if not id_token:
                return JSONResponse({"error": "missing token"}, status_code=400)

            from metrics_tracker.auth import verify_and_upsert_user

            # photo_url comes from client JS (user.photoURL) since it's
            # not always present in the ID token claims
            client_photo_url = body.get("photo_url")
            user = verify_and_upsert_user(id_token, client_photo_url)

            # Download and cache profile photo locally
            local_photo_url = None
            if user.photo_url:
                try:
                    url_hash = hashlib.md5(user.photo_url.encode()).hexdigest()
                    filename = f"{url_hash}.jpg"
                    cache_path = PHOTO_CACHE_DIR / filename
                    if not cache_path.exists():
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(user.photo_url)
                            if resp.status_code == 200:
                                cache_path.write_bytes(resp.content)
                    if cache_path.exists():
                        local_photo_url = f"/auth/photo/{filename}"
                except Exception:
                    pass

            # Store user info in NiceGUI's per-browser storage
            storage = app.storage.user
            storage["user_id"] = user.id
            storage["firebase_uid"] = user.firebase_uid
            storage["is_anonymous"] = user.is_anonymous
            storage["display_name"] = user.display_name
            storage["photo_url"] = local_photo_url
            storage["is_demo"] = False
            storage["email"] = user.email

            return JSONResponse({"status": "ok", "user_id": user.id})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=401)


def root():
    if not app.storage.user.get("user_id"):
        ui.navigate.to("/welcome")
        return

    app.add_static_files("/static", Path("./static"))
    ui.add_css(
        """
        .body--light {
            color: rgb(33, 33, 33);

            .color-4 { color: rgb(66, 66, 66); }

            .color-5 { color: rgb(97, 97, 97); }

            .color-6 { color: rgb(117, 117, 117); }

            .color-8 { color: rgb(158, 158, 158); }

        }

        .body--dark {
            color: rgb(255, 255, 255);

            .color-4 { color: rgb(224, 224, 224); }

            .color 5 { color: rgb(189, 189, 189); }

            .color-6 { color: rgb(158, 158, 158); }

            .color-8 {color: rgb(97, 97, 97); }
        }

        @font-face {
            src: url("/static/NotoSans-VariableFont_wdth,wght.ttf");
            font-family: "Noto Sans";
        }

        @font-face {
            src: url("/static/NotoSans-Italic-VariableFont_wdth,wght.ttf");
            font-family: "Noto Sans Italic"
        }

        body {
            font-family: "Noto Sans", sans-serif;
            font-optical-sizing: auto;
            font-weight: 400;
            font-style: normal;
            font-size: 1rem;
        }

        blockquote {
            font-family: "Noto Sans Italic", sans-serif;
            font-weight: 500;
            color: gray;
        }

        .q-field {
            font-size: 1rem;
        }
    """,
        shared=True,
    )

    with page_layout():
        title = ui.label().classes("text-h6 text-white")

    ui.sub_pages(
        {
            "/": dashboard_page,
            "/account": account_page,
            "/metric/new": new_metric_page,
            "/dummy": dummy_page,
        },
        data={"title": title},
    )


firebase_api_key = os.environ.get("FIREBASE_API_KEY")
if firebase_api_key:
    from metrics_tracker.auth import init_firebase

    init_firebase()
    setup_auth_endpoints()

storage_secret = os.environ.get("STORAGE_SECRET", "dev-secret-change-in-production")
ui.run(
    root,
    title="Metrics Tracker",
    storage_secret=storage_secret,
    dark=None,
    show=False,
)
