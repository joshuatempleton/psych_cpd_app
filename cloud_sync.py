from __future__ import annotations

from datetime import datetime
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
    """Authenticate, load the cloud portfolio and enable automatic saving.

    Call once near the beginning of app.py, after a default portfolio has been
    created in ``st.session_state[portfolio_key]``. When cloud storage is
    configured, Supabase is the primary source of truth. JSON remains a backup
    and legacy import format only.
    """
    store = get_store()
    st.sidebar.subheader("Cloud portfolio")

    if store is None:
        st.sidebar.error("Cloud storage is not configured. Add Supabase secrets before using the app.")
        if require_sign_in:
            st.stop()
        return

    if not cloud_signed_in():
        _render_sign_in(store)
        if require_sign_in:
            st.info("Sign in from the sidebar to open your cloud portfolio.")
            st.stop()
        return

    auth = st.session_state[SESSION_AUTH]
    st.sidebar.caption(f"Signed in as {auth.get('email', '')}")

    if not st.session_state.get(SESSION_READY):
        _initialise_cloud_portfolio(store, portfolio_key, normalise_portfolio)

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
        _clear_cloud_session()
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
        st.sidebar.error(f"Could not load cloud portfolio: {exc}")
        st.stop()


@st.fragment(run_every="2s")
def _cloud_autosave_fragment(portfolio_key: str) -> None:
    """Save committed session-state changes without modifying each UI module."""
    if not cloud_ready() or not st.session_state.get(SESSION_AUTOSAVE, True):
        return

    store = get_store()
    if store is None or portfolio_key not in st.session_state:
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

    if status == "saving":
        st.sidebar.info("Saving changes to cloud…")
    elif status == "unsaved":
        st.sidebar.warning("Unsaved cloud changes")
    elif status == "conflict":
        st.sidebar.error("Cloud conflict detected. Reload before continuing.")
    elif status == "error":
        st.sidebar.error("Cloud save failed. Use Save now to retry.")
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
    if store is None or not cloud_signed_in():
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
    """Optional helper for modules that want to display save feedback immediately."""
    if cloud_ready():
        st.session_state[SESSION_STATUS] = "unsaved"


def _clear_cloud_session() -> None:
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


def _render_sign_in(store: SupabasePortfolioStore) -> None:
    mode = st.sidebar.radio("Account action", ["Sign in", "Create account"], horizontal=True)
    with st.sidebar.form("cloud_auth_form"):
        email = st.text_input("Email address")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(mode, width="stretch")

    if not submitted:
        return
    if not email.strip() or len(password) < 8:
        st.sidebar.error("Enter an email address and a password of at least eight characters.")
        return

    try:
        if mode == "Create account":
            session = store.sign_up(email, password)
            if session is None:
                st.sidebar.success("Account created. Confirm the email address, then sign in.")
                return
        else:
            session = store.sign_in(email, password)
        st.session_state[SESSION_AUTH] = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": session.user_id,
            "email": session.email,
        }
        st.session_state[SESSION_READY] = False
        st.session_state[SESSION_STATUS] = "loading"
        st.rerun()
    except CloudStorageError as exc:
        st.sidebar.error(str(exc))
