from __future__ import annotations
from datetime import date

import pandas as pd
import streamlit as st

from constants import CPD_ACTIVITY_TYPES, EVIDENCE_OPTIONS
from models import new_id
from utils import (
    delete_entry,
    format_goal_links,
    get_entry_by_id,
    goal_title_map,
    parse_iso_date,
    safe_float,
    upsert_entry,
)


def render_cpd_log(portfolio: dict) -> None:
    """General annual CPD log.

    Registrar/endorsement CPD is entered in the Endorsement / Registrar tab.
    Eligible registrar CPD is automatically included in annual CPD calculations.
    """
    st.subheader("General CPD log")
    st.info(
        "Use this tab for ordinary annual CPD. If you are completing a registrar program, "
        "enter registrar-specific active CPD in the Endorsement / Registrar tab so it can "
        "be documented for both registrar and annual CPD requirements."
    )

    goal_options = goal_title_map(portfolio["learning_goals"])
    entries = portfolio["cpd_entries"]

    if entries:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Date": e.get("date"),
                        "Type": e.get("activity_type"),
                        "Activity details": e.get("activity_details"),
                        "Area": e.get("area_of_practice"),
                        "Hours": e.get("hours"),
                        "Goals": format_goal_links(e.get("goal_ids", []), goal_options),
                        "Evidence": e.get("evidence_type"),
                        "Reflection": e.get("reflection"),
                    }
                    for e in entries
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("**Add or edit general CPD entry**")

    entry_options = {"New entry": None}
    for e in entries:
        entry_options[
            f"{e.get('date', '')} | {e.get('activity_type', '')} | "
            f"{safe_float(e.get('hours'))}h | {e.get('activity_details', '')[:40]}"
        ] = e.get("id")

    selected_label = st.selectbox(
        "Choose an existing CPD entry to edit, or leave on New entry",
        list(entry_options.keys()),
        key="cpd_select_entry",
    )
    selected_id = entry_options[selected_label]
    selected_entry = get_entry_by_id(entries, selected_id)

    default_activity_type = selected_entry.get("activity_type", CPD_ACTIVITY_TYPES[0]) if selected_entry else CPD_ACTIVITY_TYPES[0]
    if default_activity_type not in CPD_ACTIVITY_TYPES:
        default_activity_type = "Other"

    default_evidence = selected_entry.get("evidence_type", EVIDENCE_OPTIONS[0]) if selected_entry else EVIDENCE_OPTIONS[0]
    if default_evidence not in EVIDENCE_OPTIONS:
        default_evidence = "Other"

    with st.form("cpd_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        entry_date = c1.date_input(
            "Date of activity",
            value=parse_iso_date(selected_entry.get("date")) if selected_entry else date.today(),
        )
        activity_type = c2.selectbox(
            "Type of activity",
            CPD_ACTIVITY_TYPES,
            index=CPD_ACTIVITY_TYPES.index(default_activity_type),
        )
        hours = c3.number_input(
            "Duration in decimal hours",
            min_value=0.0,
            step=0.25,
            format="%.2f",
            value=safe_float(selected_entry.get("hours")) if selected_entry else 0.0,
        )

        activity_details = st.text_area(
            "Activity details",
            value=selected_entry.get("activity_details", "") if selected_entry else "",
        )
        area = st.text_input(
            "Area of practice (if applicable)",
            value=selected_entry.get("area_of_practice", "") if selected_entry else "",
        )
        related_goals = st.multiselect(
            "Related learning goals",
            options=list(goal_options.keys()),
            default=selected_entry.get("goal_ids", []) if selected_entry else [],
            format_func=lambda gid: goal_options[gid],
        )
        reflection = st.text_area(
            "Reflection",
            value=selected_entry.get("reflection", "") if selected_entry else "",
        )

        e1, e2 = st.columns([2, 3])
        evidence_type = e1.selectbox("Evidence type", EVIDENCE_OPTIONS, index=EVIDENCE_OPTIONS.index(default_evidence))
        evidence_details = e2.text_input(
            "Evidence detail / where stored",
            value=selected_entry.get("evidence_details", "") if selected_entry else "",
        )

        col1, col2 = st.columns(2)
        save_clicked = col1.form_submit_button("Save CPD entry")
        delete_clicked = col2.form_submit_button("Delete selected CPD entry")

    if save_clicked:
        upsert_entry(
            entries,
            {
                "id": selected_entry.get("id") if selected_entry else new_id(),
                "date": entry_date.isoformat(),
                "activity_type": activity_type,
                "activity_details": activity_details,
                "area_of_practice": area,
                "hours": round(float(hours), 2),
                "goal_ids": related_goals,
                "reflection": reflection,
                "evidence_type": evidence_type,
                "evidence_details": evidence_details,
                "source": "general_cpd",
            },
        )
        st.success("CPD entry saved.")
        st.rerun()

    if delete_clicked:
        if selected_id:
            delete_entry(entries, selected_id)
            st.success("CPD entry deleted.")
            st.rerun()
        else:
            st.warning("Select an existing CPD entry first.")
