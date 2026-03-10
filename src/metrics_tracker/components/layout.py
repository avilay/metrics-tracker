import os
from contextlib import contextmanager

from nicegui import app, ui

FIREBASE_JS = """
var firebaseAuth = null;
var signingOut = false;

try {{
    firebase.initializeApp({{
        apiKey: "{api_key}",
        authDomain: "{auth_domain}",
        projectId: "{project_id}",
    }});
    firebaseAuth = firebase.auth();
}} catch (e) {{
    console.warn("Firebase init failed (missing config?):", e.message);
}}

async function exchangeToken(user, forceRefresh, photoUrlOverride) {{
    const token = await user.getIdToken(!!forceRefresh);
    const photoUrl = photoUrlOverride
        || user.photoURL
        || (user.providerData && user.providerData.length > 0 && user.providerData[0].photoURL)
        || null;
    const resp = await fetch("/auth/firebase-token", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
            token: token,
            photo_url: photoUrl,
        }}),
    }});
    if (!resp.ok) console.error("Token exchange failed:", resp.status);
    return resp;
}}

async function anonymousSignIn() {{
    if (!firebaseAuth) {{
        console.error("Firebase not initialized. Set FIREBASE_API_KEY env var.");
        return;
    }}
    try {{
        resp = await firebaseAuth.signInAnonymously();
        if (resp && resp.ok && window.location.pathname === '/welcome') {{
            window.location.href = '/';
        }}
    }} catch (e) {{
        console.error("Anonymous sign-in failed:", e);
    }}
}}

if (firebaseAuth) {{
    firebaseAuth.onAuthStateChanged(async (user) => {{
        if (signingOut) return;
        if (user) {{
            resp = await exchangeToken(user);
            if (resp && resp.ok && window.location.pathname === '/welcome') {{
                window.location.href = '/';
            }}
        }}
    }});
}}

async function firebaseSignOut() {{
    signingOut = true;
    try {{
        if (firebaseAuth && firebaseAuth.currentUser) {{
            await firebaseAuth.signOut();
        }}
        await fetch("/auth/sign-out", {{ method: "POST" }});
    }} catch (e) {{
        console.error("Sign-out failed:", e);
    }} finally {{
        signingOut = false;
        window.location.href = '/welcome';
    }}
}}

async function upgradeToGoogle() {{
    if (!firebaseAuth) {{
        console.error("Firebase not initialized. Set FIREBASE_API_KEY env var.");
        return;
    }}
    const provider = new firebase.auth.GoogleAuthProvider();
    try {{
        var result;
        if (firebaseAuth.currentUser && firebaseAuth.currentUser.isAnonymous) {{
            result = await firebaseAuth.currentUser.linkWithPopup(provider);
        }} else {{
            result = await firebaseAuth.signInWithPopup(provider);
        }}
        var googlePhoto = (result.additionalUserInfo
            && result.additionalUserInfo.profile
            && result.additionalUserInfo.profile.picture) || null;
        await exchangeToken(result.user, true, googlePhoto);
        if (window.location.pathname === '/welcome') {{
            window.location.href = '/';
        }}
    }} catch (e) {{
        if (e.code === "auth/credential-already-in-use") {{
            await firebaseAuth.signInWithCredential(e.credential);
            await exchangeToken(firebaseAuth.currentUser, true);
            if (window.location.pathname === '/welcome') {{
                window.location.href = '/';
            }}
        }} else {{
            console.error("Google sign-in failed:", e);
        }}
    }}
}}
"""


def add_firebase_head_html() -> None:
    ui.add_head_html(
        '<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>'
    )
    ui.add_head_html(
        '<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>'
    )

    api_key = os.environ.get("FIREBASE_API_KEY", "")
    auth_domain = os.environ.get("FIREBASE_AUTH_DOMAIN", "")
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "")

    js = FIREBASE_JS.format(
        api_key=api_key, auth_domain=auth_domain, project_id=project_id
    )
    ui.add_head_html(f"<script>{js}</script>")


def _get_auth_snapshot() -> tuple:
    """Return a hashable snapshot of auth-relevant storage fields."""
    user_data = app.storage.user
    return (
        user_data.get("user_id"),
        user_data.get("is_anonymous", True),
        user_data.get("display_name"),
        user_data.get("photo_url"),
    )


@contextmanager
def page_layout():
    """Shared page layout with header and navigation drawer."""
    add_firebase_head_html()

    with ui.header().classes("p-1 bg-dark"):
        with ui.row().classes("w-full items-center"):
            with ui.button(icon="menu").props("flat round color=white"):
                with ui.menu().classes("shadow-sm"):
                    with ui.menu_item(on_click=lambda: ui.navigate.to("/")):
                        with ui.item_section().props("side"):
                            ui.icon("dashboard")
                        with ui.item_section():
                            ui.label("Dashboard")
                    with ui.menu_item(on_click=lambda: ui.navigate.to("/metric/new")):
                        with ui.item_section().props("side"):
                            ui.icon("add_circle")
                        with ui.item_section():
                            ui.label("New Metric")
                    with ui.menu_item(on_click=lambda: ui.navigate.to("/dummy")):
                        with ui.item_section().props("side"):
                            ui.icon("psychology")
                        with ui.item_section():
                            ui.label("Dummy")
            yield
            ui.space()
            auth_container = ui.row().classes("items-center")
            with auth_container:
                _render_auth_controls()

    # Poll storage for auth changes and re-render just the auth controls
    last_snapshot = [_get_auth_snapshot()]

    def check_auth_change():
        current = _get_auth_snapshot()
        if current != last_snapshot[0]:
            last_snapshot[0] = current
            auth_container.clear()
            with auth_container:
                _render_auth_controls()

    ui.timer(1.0, check_auth_change)


def _render_auth_controls():
    user_id = app.storage.user.get("user_id")
    if user_id is None:
        return

    if app.storage.user["is_demo"]:
        avatar_btn = ui.button(icon="face").props("flat round color=white")
    elif app.storage.user["is_anonymous"]:
        avatar_btn = ui.button(icon="no_accounts").props("flat round color=white")
    else:
        photo_url = app.storage.user.get("photo_url")
        if photo_url:
            avatar_btn = (
                ui.button()
                .props("flat round padding=0")
                .style("width:40px;height:40px;min-width:40px")
            )
            with avatar_btn:
                ui.html(
                    f'<img src="{photo_url}"'
                    f' style="width:32px;height:32px;border-radius:50%;object-fit:cover"'
                    f" onerror=\"this.outerHTML='<q-icon name=account_circle style=font-size:32px></q-icon>'\">"
                )
        else:
            avatar_btn = ui.button(icon="account_circle").props(
                "flat round color=white"
            )

    with avatar_btn:
        with ui.menu().classes("shadow-sm !max-w-none"):
            with ui.menu_item(on_click=lambda: ui.navigate.to("/account")):
                with ui.item_section().props("side"):
                    ui.icon("person")
                with ui.item_section():
                    ui.label("Account")
            ui.separator()
            with ui.menu_item(on_click=lambda: ui.run_javascript("firebaseSignOut()")):
                with ui.item_section().props("side"):
                    ui.icon("logout")
                with ui.item_section():
                    ui.label("Sign out")
