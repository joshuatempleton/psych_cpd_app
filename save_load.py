from __future__ import annotations
import streamlit as st
from models import default_portfolio
from persistence import load_portfolio_from_bytes, portfolio_json_bytes

def render_save_load(portfolio: dict) -> None:
    st.subheader("Save / load portfolio")
    st.warning("Confidentiality note: this app does not keep your data after the app closes. Your JSON portfolio file is your record. Keep it safe.")
    base_name = portfolio["profile"].get("psychologist_name", "").strip().replace(" ", "_") or "psychology_cpd_portfolio"
    st.download_button("Download portfolio JSON", data=portfolio_json_bytes(portfolio), file_name=f"{base_name}.json", mime="application/json")
    uploaded = st.file_uploader("Upload existing portfolio JSON", type=["json"])
    if uploaded is not None:
        try:
            loaded = load_portfolio_from_bytes(uploaded.read())
            if st.button("Load uploaded portfolio into this session"):
                st.session_state.portfolio = loaded; st.session_state.editing_cpd_id = None; st.session_state.editing_peer_id = None
                st.success("Portfolio loaded into the current session."); st.rerun()
        except Exception as e:
            st.error(f"Unable to load file: {e}")
    if st.button("Start a new blank portfolio"):
        st.session_state.portfolio = default_portfolio(); st.session_state.editing_cpd_id = None; st.session_state.editing_peer_id = None; st.rerun()
