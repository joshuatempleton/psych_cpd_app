from __future__ import annotations
import pandas as pd
import streamlit as st
from models import default_goal

def render_learning_plan(portfolio: dict) -> None:
    st.subheader("Learning plan")
    st.caption("At least three goals are preloaded, but you can add as many as you need.")
    goals = portfolio["learning_goals"]
    if st.button("Add learning goal"):
        goals.append(default_goal(len(goals) + 1))
    delete_idx = None
    for idx, goal in enumerate(goals):
        with st.expander(goal.get("title") or f"Goal {idx + 1}", expanded=(idx < 3)):
            col1, col2 = st.columns([4, 1])
            goal["title"] = col1.text_input("Goal title", value=goal.get("title", ""), key=f"goal_title_{goal['id']}")
            statuses = ["Planned", "In progress", "Reviewed", "Completed"]
            goal["status"] = col2.selectbox("Status", statuses, index=statuses.index(goal.get("status", "Planned")) if goal.get("status") in statuses else 0, key=f"goal_status_{goal['id']}")
            goal["learning_need"] = st.text_area("Learning needs identified and goals set", value=goal.get("learning_need", ""), key=f"goal_need_{goal['id']}")
            goal["proposed_activities"] = st.text_area("Type of activities proposed", value=goal.get("proposed_activities", ""), key=f"goal_activities_{goal['id']}")
            goal["proposed_dates"] = st.text_input("Dates proposed activities planned", value=goal.get("proposed_dates", ""), key=f"goal_dates_{goal['id']}")
            goal["anticipated_outcomes"] = st.text_area("Outcomes anticipated", value=goal.get("anticipated_outcomes", ""), key=f"goal_outcomes_{goal['id']}")
            goal["review_date"] = st.text_input("Review date", value=goal.get("review_date", ""), key=f"goal_review_{goal['id']}")
            goal["outcomes_achieved"] = st.text_area("Outcomes achieved", value=goal.get("outcomes_achieved", ""), key=f"goal_achieved_{goal['id']}")
            if len(goals) > 3 and st.button("Delete this goal", key=f"delete_goal_{goal['id']}"): delete_idx = idx
    if delete_idx is not None:
        del goals[delete_idx]; save_cloud_portfolio("portfolio", silent_when_unchanged=True); st.rerun()
    st.dataframe(pd.DataFrame([{"Goal": g.get("title"), "Status": g.get("status"), "Review date": g.get("review_date"), "Planned activities": g.get("proposed_activities")} for g in goals]), use_container_width=True, hide_index=True)
