from __future__ import annotations
import streamlit as st
from constants import ENDORSEMENT_OPTIONS

def render_sidebar(profile: dict) -> None:
    st.sidebar.header("Setup and privacy")
    st.sidebar.info("This app is local/session-only. Nothing is stored after the app closes. To keep your data, download your JSON portfolio file and keep it safe.")
    with st.sidebar.expander("Registration / pathway questions", expanded=True):
        profile["psychologist_name"] = st.text_input("Psychologist name", value=profile.get("psychologist_name", ""), key="profile_name")
        profile["signature_name"] = st.text_input("Signature name for exports", value=profile.get("signature_name", ""), key="profile_sig")
        profile["registration_cycle_year_end"] = st.number_input("Registration cycle year end", min_value=2020, max_value=2100, step=1, value=int(profile.get("registration_cycle_year_end")), key="profile_cycle")
        profile["full_year_general_registration"] = st.checkbox("Held general registration for the full cycle", value=profile.get("full_year_general_registration", True))
        profile["months_general_registration"] = 12 if profile["full_year_general_registration"] else st.number_input("Full months of general registration in the cycle", min_value=0, max_value=12, value=int(profile.get("months_general_registration", 12)))
        profile["has_board_exemption"] = st.checkbox("There is a Board exemption or variation affecting this cycle", value=profile.get("has_board_exemption", False))
        if profile["has_board_exemption"]:
            profile["exemption_notes"] = st.text_area("Exemption / variation notes", value=profile.get("exemption_notes", ""))
        profile["has_endorsement"] = st.checkbox("Has area of practice endorsement(s)", value=profile.get("has_endorsement", False))
        profile["endorsements"] = st.multiselect("Select endorsement area(s)", ENDORSEMENT_OPTIONS, default=profile.get("endorsements", [])) if profile["has_endorsement"] else []
        profile["is_registrar"] = st.checkbox("Currently in registrar program", value=profile.get("is_registrar", False))
        if profile["is_registrar"]:
            current = profile.get("registrar_area") or (profile["endorsements"][0] if profile.get("endorsements") else ENDORSEMENT_OPTIONS[0])
            profile["registrar_area"] = st.selectbox("Registrar area", ENDORSEMENT_OPTIONS, index=ENDORSEMENT_OPTIONS.index(current) if current in ENDORSEMENT_OPTIONS else 0)
        profile["is_board_approved_supervisor"] = st.checkbox("Board-approved supervisor", value=profile.get("is_board_approved_supervisor", False))
        if profile["is_board_approved_supervisor"]:
            profile["supervisor_last_training_date"] = st.text_input("Last supervisor training/refresher date", value=profile.get("supervisor_last_training_date", ""))
        profile["practice_context"] = st.text_area("Practice context", value=profile.get("practice_context", ""))
        profile["position_description_note"] = st.text_area("Position / practice relevance note", value=profile.get("position_description_note", ""))
