from __future__ import annotations

import pandas as pd
import streamlit as st

from calculations import build_insights, compute_all_cycle_summaries, compute_metrics
from registrar import render_registrar_progress_dashboard
from utils import in_cpd_cycle


def render_dashboard(portfolio: dict) -> None:
    metrics = compute_metrics(portfolio)

    st.subheader("Dashboard")
    st.caption(
        f"Annual CPD view: {metrics['cycle_label']}. "
        "Your JSON portfolio keeps all years; this page filters annual CPD by the selected cycle."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Total annual CPD hours",
        f"{metrics['total_hours']} / {metrics['total_target']}",
        f"{metrics['total_remaining']} remaining",
    )
    c2.metric(
        "General CPD hours",
        f"{metrics['cpd_hours']} / {metrics['general_target']}",
        f"{metrics['cpd_remaining']} remaining",
    )
    c3.metric(
        "Peer consultation hours",
        f"{metrics['peer_hours']} / {metrics['peer_target']}",
        f"{metrics['peer_remaining']} remaining",
    )

    with st.expander("Annual CPD source breakdown", expanded=True):
        st.dataframe(
            pd.DataFrame(
                [
                    {"Annual requirement area": "General CPD", "Source": "General CPD log", "Hours": metrics["general_cpd_hours"]},
                    {"Annual requirement area": "General CPD", "Source": "Registrar active CPD", "Hours": metrics["registrar_active_cpd_hours_in_cycle"]},
                    {"Annual requirement area": "Peer consultation", "Source": "Peer consultation log", "Hours": metrics["standalone_peer_hours"]},
                    {"Annual requirement area": "Peer consultation", "Source": "Registrar supervision", "Hours": metrics["registrar_supervision_peer_hours_in_cycle"]},
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Registrar entries are documented in the Endorsement / Registrar tab first, then counted here for annual CPD where eligible."
        )

    if portfolio["profile"].get("is_registrar") and portfolio.get("registrar", {}).get("enabled"):
        st.markdown("### Registrar progress")
        st.caption("Registrar progress is cumulative across the whole registrar program and does not reset each CPD year.")
        render_registrar_progress_dashboard(portfolio, compact=True)

    st.info("Use decimal hours throughout the app. Example: 1.5 means 1 hour 30 minutes.")

    with st.expander("Historical annual CPD cycles in this portfolio"):
        st.caption("These summaries are derived from dates in your stored CPD, peer, registrar CPD, and registrar supervision entries.")
        st.dataframe(pd.DataFrame(compute_all_cycle_summaries(portfolio)), use_container_width=True, hide_index=True)

    warnings = []
    if metrics["peer_hours"] < metrics["peer_target"]:
        warnings.append("Peer consultation target is not yet met for the selected CPD cycle.")
    if metrics["cpd_hours"] < metrics["general_target"]:
        warnings.append("General CPD target is not yet met for the selected CPD cycle.")

    cycle_end = portfolio["profile"]["registration_cycle_year_end"]
    if any(x.get("date") and not in_cpd_cycle(x.get("date"), cycle_end) for x in portfolio.get("cpd_entries", [])):
        warnings.append("Some general CPD entries are stored in the portfolio but fall outside the selected CPD cycle.")
    if any(x.get("date") and not in_cpd_cycle(x.get("date"), cycle_end) for x in portfolio.get("peer_entries", [])):
        warnings.append("Some peer entries are stored in the portfolio but fall outside the selected CPD cycle.")

    for warning in warnings:
        st.warning(warning)
    if not warnings:
        st.success("Current logged hours meet the main Board minimum targets for the selected CPD cycle.")

    portfolio["summary_insights"] = st.text_area(
        "Summary insights",
        value=portfolio.get("summary_insights") or build_insights(portfolio, metrics),
        height=180,
    )
