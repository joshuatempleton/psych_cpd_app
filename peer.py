from __future__ import annotations
from datetime import date
import pandas as pd
import streamlit as st
from constants import EVIDENCE_OPTIONS, PEER_FORMATS
from models import new_id
from utils import format_goal_links, get_entry_by_id, goal_title_map, parse_iso_date, safe_float, upsert_entry, delete_entry

def render_peer_log(portfolio: dict) -> None:
    st.subheader("Peer consultation log")
    st.caption("Enter total duration and own-practice component separately.")
    goal_options = goal_title_map(portfolio["learning_goals"])
    entries = portfolio["peer_entries"]
    if entries:
        st.dataframe(pd.DataFrame([{"Date": e.get("date"), "Format": e.get("format"), "Focus": e.get("focus"), "Colleagues": e.get("colleagues"), "Total hours": e.get("total_hours"), "Own-practice hours": e.get("own_practice_hours"), "Area": e.get("area_of_practice"), "Goals": format_goal_links(e.get("goal_ids", []), goal_options), "Evidence": e.get("evidence_type"), "Reflection": e.get("reflection")} for e in entries]), use_container_width=True, hide_index=True)
    entry_options = {"New entry": None}
    for e in entries:
        entry_options[f"{e.get('date', '')} | {e.get('format', '')} | {safe_float(e.get('own_practice_hours'))}h | {e.get('focus','')[:40]}"] = e.get("id")
    selected_label = st.selectbox("Choose an existing peer consultation entry to edit, or leave on New entry", list(entry_options.keys()), key="peer_select_entry")
    selected_id = entry_options[selected_label]
    selected_entry = get_entry_by_id(entries, selected_id)
    default_format = selected_entry.get("format", PEER_FORMATS[0]) if selected_entry else PEER_FORMATS[0]
    if default_format not in PEER_FORMATS: default_format = "Other"
    default_evidence = selected_entry.get("evidence_type", EVIDENCE_OPTIONS[0]) if selected_entry else EVIDENCE_OPTIONS[0]
    if default_evidence not in EVIDENCE_OPTIONS: default_evidence = "Other"
    with st.form("peer_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        entry_date = c1.date_input("Date", value=parse_iso_date(selected_entry.get("date")) if selected_entry else date.today())
        peer_format = c2.selectbox("Peer consultation format", PEER_FORMATS, index=PEER_FORMATS.index(default_format))
        focus = st.text_area("Focus of peer consultation", value=selected_entry.get("focus", "") if selected_entry else "")
        colleagues = st.text_input("Colleagues involved", value=selected_entry.get("colleagues", "") if selected_entry else "")
        c3, c4, c5 = st.columns(3)
        total_hours = c3.number_input("Total duration in decimal hours", min_value=0.0, step=0.25, format="%.2f", value=safe_float(selected_entry.get("total_hours")) if selected_entry else 0.0)
        own_practice_hours = c4.number_input("Own-practice hours in decimal hours", min_value=0.0, step=0.25, format="%.2f", value=safe_float(selected_entry.get("own_practice_hours")) if selected_entry else 0.0)
        area = c5.text_input("Area of practice", value=selected_entry.get("area_of_practice", "") if selected_entry else "")
        related_goals = st.multiselect("Related learning goals", options=list(goal_options.keys()), default=selected_entry.get("goal_ids", []) if selected_entry else [], format_func=lambda gid: goal_options[gid])
        reflection = st.text_area("Reflection", value=selected_entry.get("reflection", "") if selected_entry else "")
        e1, e2 = st.columns([2, 3])
        evidence_type = e1.selectbox("Evidence type", EVIDENCE_OPTIONS, index=EVIDENCE_OPTIONS.index(default_evidence))
        evidence_details = e2.text_input("Evidence detail / where stored", value=selected_entry.get("evidence_details", "") if selected_entry else "")
        col1, col2 = st.columns(2)
        save_clicked = col1.form_submit_button("Save peer consultation entry")
        delete_clicked = col2.form_submit_button("Delete selected peer entry")
    if save_clicked:
        if own_practice_hours > total_hours:
            st.error("Own-practice hours cannot exceed total duration.")
        else:
            upsert_entry(entries, {"id": selected_entry.get("id") if selected_entry else new_id(), "date": entry_date.isoformat(), "format": peer_format, "focus": focus, "colleagues": colleagues, "total_hours": round(float(total_hours), 2), "own_practice_hours": round(float(own_practice_hours), 2), "area_of_practice": area, "goal_ids": related_goals, "reflection": reflection, "evidence_type": evidence_type, "evidence_details": evidence_details})
            st.success("Peer consultation entry saved."); st.rerun()
    if delete_clicked:
        if selected_id:
            delete_entry(entries, selected_id); st.success("Peer consultation entry deleted."); st.rerun()
        else: st.warning("Select an existing peer consultation entry first.")
