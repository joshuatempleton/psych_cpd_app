from __future__ import annotations
import pandas as pd
import streamlit as st
from calculations import build_insights, compute_metrics
from registrar import render_registrar_progress_dashboard
from utils import in_cpd_cycle

def render_dashboard(portfolio: dict) -> None:
    metrics = compute_metrics(portfolio)
    st.subheader("Dashboard")
    st.caption(f"Tracking cycle: {metrics['cycle_label']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total hours", f"{metrics['total_hours']} / {metrics['total_target']}", f"{metrics['total_remaining']} remaining")
    c2.metric("General CPD hours", f"{metrics['cpd_hours']} / {metrics['general_target']}", f"{metrics['cpd_remaining']} remaining")
    c3.metric("Peer consultation hours", f"{metrics['peer_hours']} / {metrics['peer_target']}", f"{metrics['peer_remaining']} remaining")
    if portfolio["profile"].get("is_registrar") and portfolio.get("registrar", {}).get("enabled"):
        st.markdown("### Registrar progress")
        render_registrar_progress_dashboard(portfolio, compact=True)
    st.info("Use decimal hours throughout the app. Example: 1.5 means 1 hour 30 minutes.")
    if portfolio["profile"].get("endorsements"):
        rows = []
        for area, target in metrics["endorsement_targets"].items():
            actual = round(metrics["endorsement_hours"].get(area, 0.0), 2)
            rows.append({"Area": area, "Logged hours": actual, "Target / expectation": target, "Remaining": round(max(0.0, target - actual), 2)})
        st.markdown("**Endorsement tracking**")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    warnings = []
    if metrics["peer_hours"] < metrics["peer_target"]: warnings.append("Peer consultation target is not yet met.")
    if metrics["cpd_hours"] < metrics["general_target"]: warnings.append("General CPD target is not yet met.")
    cycle_end = portfolio["profile"]["registration_cycle_year_end"]
    if any(x.get("date") and not in_cpd_cycle(x.get("date"), cycle_end) for x in portfolio.get("cpd_entries", [])): warnings.append("Some CPD entries fall outside the selected CPD cycle.")
    if any(x.get("date") and not in_cpd_cycle(x.get("date"), cycle_end) for x in portfolio.get("peer_entries", [])): warnings.append("Some peer entries fall outside the selected CPD cycle.")
    for warning in warnings: st.warning(warning)
    if not warnings: st.success("Current logged hours meet the main Board minimum targets for this cycle.")
    portfolio["summary_insights"] = st.text_area("Summary insights", value=portfolio.get("summary_insights") or build_insights(portfolio, metrics), height=180)
