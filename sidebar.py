from __future__ import annotations
import streamlit as st
from constants import ENDORSEMENT_OPTIONS
from utils import available_cpd_cycle_years, cpd_cycle_label


def render_sidebar(portfolio: dict) -> None:
    profile = portfolio["profile"]

    st.sidebar.header("Setup and privacy")
    st.sidebar.info(
        "This app is local/session-only. Nothing is stored after the app closes. "
        "To keep your data, download your JSON portfolio file and keep it safe."
    )

    with st.sidebar.expander("Annual CPD cycle view", expanded=True):
        st.caption(
            "Your JSON portfolio keeps entries across multiple years. "
            "This selector only changes which annual CPD cycle is calculated on the dashboard."
        )
        cycle_years = available_cpd_cycle_years(portfolio)
        selected_year = int(
            portfolio.get("cpd_cycle_settings", {}).get(
                "selected_year_end",
                profile.get("registration_cycle_year_end", cycle_years[0]),
            )
        )
        if selected_year not in cycle_years:
            cycle_years.insert(0, selected_year)

        selected_label = st.selectbox(
            "Viewing CPD cycle",
            options=cycle_years,
            format_func=cpd_cycle_label,
            index=cycle_years.index(selected_year),
            key="selected_cpd_cycle_year_end",
        )
        portfolio.setdefault("cpd_cycle_settings", {})["selected_year_end"] = int(selected_label)
        profile["registration_cycle_year_end"] = int(selected_label)

    with st.sidebar.expander("Registration / pathway questions", expanded=True):
        profile["psychologist_name"] = st.text_input(
            "Psychologist name",
            value=profile.get("psychologist_name", ""),
            key="profile_name",
        )
        profile["signature_name"] = st.text_input(
            "Signature name for exports",
            value=profile.get("signature_name", ""),
            key="profile_sig",
        )

        st.caption(f"Annual CPD calculations currently use: {cpd_cycle_label(int(profile['registration_cycle_year_end']))}")

        profile["full_year_general_registration"] = st.checkbox(
            "Held general registration for the full selected CPD cycle",
            value=profile.get("full_year_general_registration", True),
        )
        profile["months_general_registration"] = (
            12
            if profile["full_year_general_registration"]
            else st.number_input(
                "Full months of general registration in the selected CPD cycle",
                min_value=0,
                max_value=12,
                value=int(profile.get("months_general_registration", 12)),
            )
        )

        profile["has_board_exemption"] = st.checkbox(
            "There is a Board exemption or variation affecting this selected cycle",
            value=profile.get("has_board_exemption", False),
        )
        if profile["has_board_exemption"]:
            profile["exemption_notes"] = st.text_area(
                "Exemption / variation notes",
                value=profile.get("exemption_notes", ""),
            )

        profile["has_endorsement"] = st.checkbox(
            "Has area of practice endorsement(s)",
            value=profile.get("has_endorsement", False),
        )
        profile["endorsements"] = (
            st.multiselect(
                "Select endorsement area(s)",
                ENDORSEMENT_OPTIONS,
                default=[e for e in profile.get("endorsements", []) if e in ENDORSEMENT_OPTIONS],
            )
            if profile["has_endorsement"]
            else []
        )

        profile["is_registrar"] = st.checkbox(
            "Currently in registrar program",
            value=profile.get("is_registrar", False),
        )
        if profile["is_registrar"]:
            current = profile.get("registrar_area") or (
                profile["endorsements"][0] if profile.get("endorsements") else ENDORSEMENT_OPTIONS[0]
            )
            profile["registrar_area"] = st.selectbox(
                "Registrar area",
                ENDORSEMENT_OPTIONS,
                index=ENDORSEMENT_OPTIONS.index(current) if current in ENDORSEMENT_OPTIONS else 0,
            )
            portfolio.setdefault("registrar", {})["area"] = profile["registrar_area"]

        profile["is_board_approved_supervisor"] = st.checkbox(
            "Board-approved supervisor",
            value=profile.get("is_board_approved_supervisor", False),
        )
        if profile["is_board_approved_supervisor"]:
            profile["supervisor_last_training_date"] = st.text_input(
                "Last supervisor training/refresher date",
                value=profile.get("supervisor_last_training_date", ""),
            )

        profile["practice_context"] = st.text_area(
            "Practice context",
            value=profile.get("practice_context", ""),
        )
        profile["position_description_note"] = st.text_area(
            "Position / practice relevance note",
            value=profile.get("position_description_note", ""),
        )
