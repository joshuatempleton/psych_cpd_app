from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import streamlit as st

from cloud_storage import CloudConflictError, CloudStorageError, SupabasePortfolioStore


SESSION_AUTH = "cloud_auth"
SESSION_REVISION = "cloud_revision"
SESSION_HASH = "cloud_last_saved_hash"
SESSION_READY = "cloud_portfolio_loaded"
SESSION_STATUS = "cloud_save_status"
SESSION_LAST_SAVED = "cloud_last_saved_at"
SESSION_AUTOSAVE = "cloud_autosave_enabled"
SESSION_AUTH_MODE = "cloud_auth_mode"


def get_store() -> SupabasePortfolioStore | None:
    try:
        config = st.secrets["supabase"]
        return SupabasePortfolioStore(config["url"], config["anon_key"])
    except (KeyError, FileNotFoundError):
        return None


def cloud_signed_in() -> bool:
    return bool(st.session_state.get(SESSION_AUTH, {}).get("access_token"))


def cloud_ready() -> bool:
    return cloud_signed_in() and bool(st.session_state.get(SESSION_READY))


def render_cloud_account(
    portfolio_key: str,
    normalise_portfolio: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    require_sign_in: bool = True,
) -> None:
    """Require authentication, load the user's portfolio and enable cloud saving.

    Call this once near the beginning of ``app.py``, after the default portfolio
    has been placed in ``st.session_state[portfolio_key]`` and before any page or
    portfolio module is rendered.
    """
    store = get_store()

    if store is None:
        st.error("Cloud storage is not configured. Add the Supabase URL and anonymous key to Streamlit secrets.")
        if require_sign_in:
            st.stop()
        return

    if cloud_signed_in() and not _ensure_fresh_session(store):
        _clear_cloud_session(portfolio_key)

    if not cloud_signed_in():
        _render_authentication_page(store)
        if require_sign_in:
            st.stop()
        return

    auth = st.session_state[SESSION_AUTH]

    if not st.session_state.get(SESSION_READY):
        _initialise_cloud_portfolio(store, portfolio_key, normalise_portfolio)

    _render_account_sidebar(store, portfolio_key, normalise_portfolio, auth)


def _render_authentication_page(store: SupabasePortfolioStore) -> None:
    """Render a blocking, full-page password screen."""
    st.title("Psychology CPD Portfolio")
    st.caption("Secure cloud access")
    st.info(
        "Sign in to open your portfolio. Your portfolio is linked to this account "
        "and is not loaded until authentication succeeds."
    )

    left, centre, right = st.columns([1, 1.35, 1])
    with centre:
        mode = st.segmented_control(
            "Account action",
            options=["Sign in", "Create account"],
            default=st.session_state.get(SESSION_AUTH_MODE, "Sign in"),
            key=SESSION_AUTH_MODE,
            label_visibility="collapsed",
        )

        with st.form("cloud_auth_form", clear_on_submit=False):
            email = st.text_input("Email address", autocomplete="email")
            password = st.text_input(
                "Password",
                type="password",
                autocomplete="current-password" if mode == "Sign in" else "new-password",
            )
            submitted = st.form_submit_button(mode or "Sign in", type="primary", width="stretch")

        if mode == "Create account":
            st.caption("Use at least eight characters. Supabase may require email confirmation before first sign-in.")
        else:
            st.caption("Use the same account on each device to access the same portfolio.")

    if not submitted:
        return

    email = email.strip().lower()
    if not email or "@" not in email:
        st.error("Enter a valid email address.")
        return
    if len(password) < 8:
        st.error("Password must contain at least eight characters.")
        return

    try:
        if mode == "Create account":
            session = store.sign_up(email, password)
            if session is None:
                st.success("Account created. Confirm your email address, then return here and sign in.")
                return
        else:
            session = store.sign_in(email, password)

        _store_auth_session(session)
        st.session_state[SESSION_READY] = False
        st.session_state[SESSION_STATUS] = "loading"
        st.rerun()
    except CloudStorageError as exc:
        st.error(f"Authentication failed: {exc}")


def _render_account_sidebar(
    store: SupabasePortfolioStore,
    portfolio_key: str,
    normalise_portfolio: Callable[[dict[str, Any]], dict[str, Any]],
    auth: dict[str, Any],
) -> None:
    st.sidebar.subheader("Cloud portfolio")
    st.sidebar.caption(f"Signed in as {auth.get('email', '')}")

    st.session_state.setdefault(SESSION_AUTOSAVE, True)
    autosave = st.sidebar.toggle(
        "Automatic cloud saving",
        key=SESSION_AUTOSAVE,
        help="Saves validated portfolio changes after they are committed by the app.",
    )

    _render_save_status(store, portfolio_key)

    c1, c2 = st.sidebar.columns(2)
    if c1.button("Save now", width="stretch"):
        save_cloud_portfolio(portfolio_key)

    if c2.button("Reload", width="stretch"):
        reload_cloud_portfolio(portfolio_key, normalise_portfolio)

    if st.sidebar.button("Sign out", width="stretch"):
        _clear_cloud_session(portfolio_key)
        st.rerun()

    if autosave:
        _cloud_autosave_fragment(portfolio_key)


def _initialise_cloud_portfolio(
    store: SupabasePortfolioStore,
    portfolio_key: str,
    normalise_portfolio: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    auth = st.session_state[SESSION_AUTH]
    try:
        cloud_record = store.load_portfolio(auth["access_token"])
        if cloud_record is None:
            initial = normalise_portfolio(st.session_state[portfolio_key])
            created = store.create_portfolio(auth["access_token"], initial)
            st.session_state[portfolio_key] = normalise_portfolio(created.portfolio)
            st.session_state[SESSION_REVISION] = created.revision
        else:
            st.session_state[portfolio_key] = normalise_portfolio(cloud_record.portfolio)
            st.session_state[SESSION_REVISION] = cloud_record.revision

        st.session_state[SESSION_HASH] = store.portfolio_hash(st.session_state[portfolio_key])
        st.session_state[SESSION_READY] = True
        st.session_state[SESSION_STATUS] = "saved"
        st.session_state[SESSION_LAST_SAVED] = datetime.now().isoformat(timespec="seconds")
        st.rerun()
    except CloudStorageError as exc:
        st.error(f"Could not load your cloud portfolio: {exc}")
        st.stop()


@st.fragment(run_every="2s")
def _cloud_autosave_fragment(portfolio_key: str) -> None:
    if not cloud_ready() or not st.session_state.get(SESSION_AUTOSAVE, True):
        return

    store = get_store()
    if store is None or portfolio_key not in st.session_state:
        return
    if not _ensure_fresh_session(store):
        st.session_state[SESSION_STATUS] = "error"
        return

    current_hash = store.portfolio_hash(st.session_state[portfolio_key])
    if current_hash == st.session_state.get(SESSION_HASH):
        return

    st.session_state[SESSION_STATUS] = "saving"
    save_cloud_portfolio(portfolio_key, silent_when_unchanged=True, render_errors=False)


def _render_save_status(store: SupabasePortfolioStore, portfolio_key: str) -> None:
    status = st.session_state.get(SESSION_STATUS, "saved")
    portfolio = st.session_state.get(portfolio_key, {})
    current_hash = store.portfolio_hash(portfolio)
    dirty = current_hash != st.session_state.get(SESSION_HASH)

    if dirty and status != "error":
        status = "saving" if st.session_state.get(SESSION_AUTOSAVE, True) else "unsaved"

    if status == "loading":
        st.sidebar.info("Loading cloud portfolio…")
    elif status == "saving":
        st.sidebar.info("Saving changes to cloud…")
    elif status == "unsaved":
        st.sidebar.warning("Unsaved cloud changes")
    elif status == "conflict":
        st.sidebar.error("Cloud conflict detected. Reload before continuing.")
    elif status == "error":
        st.sidebar.error("Cloud connection or save failed. Use Save now to retry.")
    else:
        last_saved = st.session_state.get(SESSION_LAST_SAVED)
        label = "Saved to cloud"
        if last_saved:
            label += f" at {last_saved[11:16]}"
        st.sidebar.success(label)


def save_cloud_portfolio(
    portfolio_key: str,
    *,
    silent_when_unchanged: bool = False,
    render_errors: bool = True,
) -> bool:
    store = get_store()
    if store is None or not cloud_ready() or portfolio_key not in st.session_state:
        return False
    if not _ensure_fresh_session(store):
        st.session_state[SESSION_STATUS] = "error"
        if render_errors:
            st.sidebar.error("Your session expired. Sign in again.")
        return False

    portfolio = st.session_state[portfolio_key]
    current_hash = store.portfolio_hash(portfolio)
    if current_hash == st.session_state.get(SESSION_HASH):
        st.session_state[SESSION_STATUS] = "saved"
        if not silent_when_unchanged:
            st.sidebar.info("No unsaved portfolio changes.")
        return True

    auth = st.session_state[SESSION_AUTH]
    st.session_state[SESSION_STATUS] = "saving"
    try:
        saved = store.save_portfolio(
            auth["access_token"],
            portfolio,
            int(st.session_state.get(SESSION_REVISION, 0)),
        )
        st.session_state[portfolio_key] = saved.portfolio
        st.session_state[SESSION_REVISION] = saved.revision
        st.session_state[SESSION_HASH] = store.portfolio_hash(saved.portfolio)
        st.session_state[SESSION_STATUS] = "saved"
        st.session_state[SESSION_LAST_SAVED] = datetime.now().isoformat(timespec="seconds")
        if not silent_when_unchanged:
            st.sidebar.success("Portfolio saved to cloud.")
        return True
    except CloudConflictError as exc:
        st.session_state[SESSION_STATUS] = "conflict"
        if render_errors:
            st.sidebar.error(str(exc))
    except CloudStorageError as exc:
        st.session_state[SESSION_STATUS] = "error"
        if render_errors:
            st.sidebar.error(f"Cloud save failed: {exc}")
    return False


def reload_cloud_portfolio(
    portfolio_key: str,
    normalise_portfolio: Callable[[dict[str, Any]], dict[str, Any]],
) -> bool:
    store = get_store()
    if store is None or not cloud_signed_in() or not _ensure_fresh_session(store):
        return False

    auth = st.session_state[SESSION_AUTH]
    try:
        cloud_record = store.load_portfolio(auth["access_token"])
        if cloud_record is None:
            return False
        st.session_state[portfolio_key] = normalise_portfolio(cloud_record.portfolio)
        st.session_state[SESSION_REVISION] = cloud_record.revision
        st.session_state[SESSION_HASH] = store.portfolio_hash(cloud_record.portfolio)
        st.session_state[SESSION_READY] = True
        st.session_state[SESSION_STATUS] = "saved"
        st.session_state[SESSION_LAST_SAVED] = datetime.now().isoformat(timespec="seconds")
        st.sidebar.success("Cloud portfolio reloaded.")
        st.rerun()
    except CloudStorageError as exc:
        st.session_state[SESSION_STATUS] = "error"
        st.sidebar.error(str(exc))
    return False


def mark_cloud_dirty() -> None:
    if cloud_ready():
        st.session_state[SESSION_STATUS] = "unsaved"


def _store_auth_session(session: Any) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(int(session.expires_in), 60))
    st.session_state[SESSION_AUTH] = {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "user_id": session.user_id,
        "email": session.email,
        "expires_at": expires_at.isoformat(),
    }


def _ensure_fresh_session(store: SupabasePortfolioStore) -> bool:
    auth = st.session_state.get(SESSION_AUTH)
    if not auth:
        return False

    expires_at_raw = auth.get("expires_at")
    if not expires_at_raw:
        # Sessions created by Version 3.1 did not store expiry. Refresh once.
        return _refresh_auth_session(store)

    try:
        expires_at = datetime.fromisoformat(expires_at_raw)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return _refresh_auth_session(store)

    if datetime.now(timezone.utc) < expires_at - timedelta(minutes=2):
        return True
    return _refresh_auth_session(store)


def _refresh_auth_session(store: SupabasePortfolioStore) -> bool:
    auth = st.session_state.get(SESSION_AUTH, {})
    refresh_token = auth.get("refresh_token")
    if not refresh_token:
        return False
    try:
        session = store.refresh_session(refresh_token)
        _store_auth_session(session)
        return True
    except CloudStorageError:
        return False


def _clear_cloud_session(portfolio_key: str | None = None) -> None:
    for key in (
        SESSION_AUTH,
        SESSION_REVISION,
        SESSION_HASH,
        SESSION_READY,
        SESSION_STATUS,
        SESSION_LAST_SAVED,
        SESSION_AUTOSAVE,
    ):
        st.session_state.pop(key, None)

    # Prevent another person using the same browser session from seeing the
    # previously authenticated user's in-memory portfolio.
    if portfolio_key:
        st.session_state.pop(portfolio_key, None)
