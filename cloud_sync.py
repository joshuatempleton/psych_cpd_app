from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from cloud_storage import CloudConflictError, CloudStorageError, SupabasePortfolioStore


SESSION_AUTH = "cloud_auth"
SESSION_REVISION = "cloud_revision"
SESSION_HASH = "cloud_last_saved_hash"
SESSION_READY = "cloud_portfolio_loaded"


def get_store() -> SupabasePortfolioStore | None:
    try:
        config = st.secrets["supabase"]
        return SupabasePortfolioStore(config["url"], config["anon_key"])
    except (KeyError, FileNotFoundError):
        return None


def cloud_signed_in() -> bool:
    return bool(st.session_state.get(SESSION_AUTH, {}).get("access_token"))


def render_cloud_account(
    portfolio_key: str,
    normalise_portfolio: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    """Render account controls and initialise the portfolio from Supabase.

    Call this once near the beginning of app.py, after the default portfolio
    has been placed in st.session_state[portfolio_key].
    """
    store = get_store()
    st.sidebar.subheader("Cloud portfolio")

    if store is None:
        st.sidebar.warning("Cloud storage is not configured. The app remains in local JSON mode.")
        return

    if not cloud_signed_in():
        _render_sign_in(store)
        return

    auth = st.session_state[SESSION_AUTH]
    st.sidebar.caption(f"Signed in as {auth.get('email', '')}")

    if not st.session_state.get(SESSION_READY):
        try:
            cloud_record = store.load_portfolio(auth["access_token"])
            if cloud_record is None:
                local_portfolio = normalise_portfolio(st.session_state[portfolio_key])
                created = store.create_portfolio(auth["access_token"], local_portfolio)
                st.session_state[portfolio_key] = normalise_portfolio(created.portfolio)
                st.session_state[SESSION_REVISION] = created.revision
            else:
                st.session_state[portfolio_key] = normalise_portfolio(cloud_record.portfolio)
                st.session_state[SESSION_REVISION] = cloud_record.revision
            st.session_state[SESSION_HASH] = store.portfolio_hash(st.session_state[portfolio_key])
            st.session_state[SESSION_READY] = True
            st.rerun()
        except CloudStorageError as exc:
            st.sidebar.error(f"Could not load cloud portfolio: {exc}")
            return

    if st.sidebar.button("Save portfolio to cloud", use_container_width=True):
        save_cloud_portfolio(portfolio_key)

    if st.sidebar.button("Reload cloud portfolio", use_container_width=True):
        try:
            cloud_record = store.load_portfolio(auth["access_token"])
            if cloud_record is not None:
                st.session_state[portfolio_key] = normalise_portfolio(cloud_record.portfolio)
                st.session_state[SESSION_REVISION] = cloud_record.revision
                st.session_state[SESSION_HASH] = store.portfolio_hash(cloud_record.portfolio)
                st.sidebar.success("Cloud portfolio reloaded.")
                st.rerun()
        except CloudStorageError as exc:
            st.sidebar.error(str(exc))

    if st.sidebar.button("Sign out", use_container_width=True):
        for key in (SESSION_AUTH, SESSION_REVISION, SESSION_HASH, SESSION_READY):
            st.session_state.pop(key, None)
        st.rerun()


def save_cloud_portfolio(portfolio_key: str, *, silent_when_unchanged: bool = False) -> bool:
    store = get_store()
    if store is None or not cloud_signed_in() or not st.session_state.get(SESSION_READY):
        return False

    portfolio = st.session_state[portfolio_key]
    current_hash = store.portfolio_hash(portfolio)
    if current_hash == st.session_state.get(SESSION_HASH):
        if not silent_when_unchanged:
            st.sidebar.info("No unsaved portfolio changes.")
        return True

    auth = st.session_state[SESSION_AUTH]
    try:
        saved = store.save_portfolio(
            auth["access_token"],
            portfolio,
            int(st.session_state.get(SESSION_REVISION, 0)),
        )
        st.session_state[portfolio_key] = saved.portfolio
        st.session_state[SESSION_REVISION] = saved.revision
        st.session_state[SESSION_HASH] = store.portfolio_hash(saved.portfolio)
        if not silent_when_unchanged:
            st.sidebar.success("Portfolio saved to cloud.")
        return True
    except CloudConflictError as exc:
        st.sidebar.error(str(exc))
    except CloudStorageError as exc:
        st.sidebar.error(f"Cloud save failed: {exc}")
    return False


def _render_sign_in(store: SupabasePortfolioStore) -> None:
    mode = st.sidebar.radio("Account action", ["Sign in", "Create account"], horizontal=True)
    with st.sidebar.form("cloud_auth_form"):
        email = st.text_input("Email address")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(mode, use_container_width=True)

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
        st.rerun()
    except CloudStorageError as exc:
        st.sidebar.error(str(exc))
