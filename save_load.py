from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

import streamlit as st

from cloud_sync import cloud_ready, save_cloud_portfolio
from models import normalise_portfolio


DEFAULT_PORTFOLIO_KEY = "portfolio"


def render_save_load(portfolio: dict[str, Any] | None = None, portfolio_key: str = DEFAULT_PORTFOLIO_KEY) -> None:
    """Render cloud-first portfolio backup and legacy import controls.

    JSON is intentionally retained for portability, recovery and migration, but
    it is no longer the normal save mechanism.
    """
    _ensure_portfolio_reference(portfolio, portfolio_key)

    st.header("Portfolio backup and recovery")
    if cloud_ready():
        st.success("Your active portfolio is stored in the cloud and saves automatically.")
    else:
        st.warning("Cloud storage is not currently connected. Sign in before making changes.")

    st.markdown(
        "Use JSON only to import an older portfolio, create an offline backup, "
        "or recover from a previous backup. You do not need to upload a file each time you use the app."
    )

    st.subheader("Download offline backup")
    current = st.session_state[portfolio_key]
    payload = json.dumps(current, indent=2, ensure_ascii=False, default=str)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    st.download_button(
        "Download JSON backup",
        data=payload,
        file_name=f"psychology-cpd-portfolio-backup-{timestamp}.json",
        mime="application/json",
        width="stretch",
    )

    st.divider()
    st.subheader("Import legacy or backup portfolio")
    st.warning("Importing replaces the portfolio currently loaded in this browser and then saves it to your cloud account.")
    uploaded = st.file_uploader("Choose a portfolio JSON file", type=["json"], key="legacy_json_import")

    if uploaded is None:
        return

    try:
        parsed = json.loads(uploaded.getvalue().decode("utf-8-sig"))
        if not isinstance(parsed, dict):
            raise ValueError("The portfolio must contain a JSON object.")
        imported = normalise_portfolio(parsed)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        st.error(f"This file could not be imported: {exc}")
        return

    counts = _portfolio_counts(imported)
    st.info(
        "Import summary: "
        f"{counts['cpd']} CPD entries, {counts['peer']} peer entries, "
        f"{counts['practice']} practice entries and {counts['supervision']} supervision entries."
    )

    confirm = st.checkbox("I understand this will replace my current cloud portfolio", key="confirm_json_import")
    if st.button("Import and save to cloud", type="primary", disabled=not confirm, width="stretch"):
        st.session_state[portfolio_key] = imported
        if cloud_ready():
            if save_cloud_portfolio(portfolio_key):
                st.success("Portfolio imported and saved to cloud.")
                st.rerun()
            else:
                st.error("The portfolio was loaded into this session but could not be saved to cloud.")
        else:
            st.error("Sign in to cloud storage before importing a portfolio.")


def render_portfolio_file_controls(portfolio: dict[str, Any] | None = None) -> None:
    render_save_load(portfolio)


def render_save_load_page(portfolio: dict[str, Any] | None = None) -> None:
    render_save_load(portfolio)


def _ensure_portfolio_reference(portfolio: dict[str, Any] | None, portfolio_key: str) -> None:
    if portfolio_key not in st.session_state:
        if portfolio is None:
            raise KeyError(f"st.session_state['{portfolio_key}'] has not been initialised.")
        st.session_state[portfolio_key] = portfolio
    elif portfolio is not None and st.session_state[portfolio_key] is not portfolio:
        st.session_state[portfolio_key] = portfolio


def _portfolio_counts(portfolio: dict[str, Any]) -> dict[str, int]:
    return {
        "cpd": len(portfolio.get("cpd_entries", [])),
        "peer": len(portfolio.get("peer_entries", [])),
        "practice": len(portfolio.get("registrar_practice_entries", [])),
        "supervision": len(portfolio.get("supervision_entries", [])),
    }
