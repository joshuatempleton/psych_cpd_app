from __future__ import annotations
import streamlit as st
from constants import APP_TITLE
from cpd import render_cpd_log
from dashboard import render_dashboard
from export_ui import render_export
from learning_plan import render_learning_plan
from models import default_portfolio, normalise_portfolio
from peer import render_peer_log
from registrar import render_endorsement_registrar
from save_load import render_save_load
from sidebar import render_sidebar

def ensure_state() -> None:
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = default_portfolio()
    else:
        st.session_state.portfolio = normalise_portfolio(st.session_state.portfolio)
    st.session_state.setdefault("editing_cpd_id", None)
    st.session_state.setdefault("editing_peer_id", None)

def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    ensure_state()
    portfolio = st.session_state.portfolio
    st.title(APP_TITLE)
    st.caption("Local/session-only CPD tracker. No automatic storage outside the JSON file you choose to save.")
    st.info("This tool supports CPD, peer consultation, learning goals, registrar supervision, endorsement competencies, deadlines, Word export and CSV export. Keep your JSON portfolio file safe.")
    render_sidebar(portfolio["profile"])
    tabs = st.tabs(["Dashboard", "Learning plan", "CPD log", "Peer consultation", "Endorsement / Registrar", "Export", "Save / load"])
    with tabs[0]: render_dashboard(portfolio)
    with tabs[1]: render_learning_plan(portfolio)
    with tabs[2]: render_cpd_log(portfolio)
    with tabs[3]: render_peer_log(portfolio)
    with tabs[4]: render_endorsement_registrar(portfolio)
    with tabs[5]: render_export(portfolio)
    with tabs[6]: render_save_load(portfolio)
    st.divider()
    st.caption("Privacy design: data is only kept in memory during the current session unless you explicitly download your JSON portfolio file.")

if __name__ == "__main__":
    main()
