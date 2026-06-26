from __future__ import annotations
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
from calculations import compute_registrar_metrics
from constants import COMPETENCY_RATINGS, ENDORSEMENT_OPTIONS, REGISTRAR_REQUIREMENTS, get_competency_map
from models import new_id


def _upcoming_registrar_deadlines(portfolio: dict, days: int = 60) -> list[dict]:
    """Return upcoming or overdue registrar deadlines that are not completed/submitted."""
    today = date.today()
    upcoming: list[dict] = []
    for item in portfolio.get("registrar_deadlines", []):
        try:
            due = datetime.strptime(item.get("due_date", ""), "%Y-%m-%d").date()
        except Exception:
            continue
        if item.get("status") not in ["Submitted", "Completed", "Not applicable"] and due <= today + timedelta(days=days):
            upcoming.append(item)
    return upcoming


def _competency_summary(portfolio: dict, endorsement_area: str) -> dict:
    """Summarise competency ratings for the selected endorsement area."""
    rows = [
        x for x in portfolio.get("competency_assessments", [])
        if x.get("endorsement_area") == endorsement_area
    ]
    total = len(rows)
    supervisor_confirmed = sum(1 for x in rows if x.get("rating") == "Supervisor confirmed")
    achieved_or_confirmed = sum(1 for x in rows if x.get("rating") in ["Achieved", "Supervisor confirmed"])
    developing_or_better = sum(1 for x in rows if x.get("rating") in ["Developing", "Consolidating", "Achieved", "Supervisor confirmed"])
    return {
        "total": total,
        "supervisor_confirmed": supervisor_confirmed,
        "achieved_or_confirmed": achieved_or_confirmed,
        "developing_or_better": developing_or_better,
    }


def render_registrar_progress_dashboard(portfolio: dict, *, compact: bool = False) -> None:
    """Reusable registrar dashboard panel for the main dashboard and the Registrar tab."""
    registrar = portfolio.get("registrar", {})
    area = registrar.get("area") or portfolio.get("profile", {}).get("registrar_area", "")
    metrics = compute_registrar_metrics(portfolio)
    req = metrics["requirements"]

    if area:
        st.caption(f"Registrar area: {area}")

    a, b, c = st.columns(3)
    a.metric(
        "Registrar practice hours",
        f"{metrics['practice_hours']} / {req['practice_hours']}",
        f"{metrics['practice_remaining']} remaining",
    )
    b.metric(
        "Registrar supervision hours",
        f"{metrics['supervision_hours']} / {req['supervision_hours']}",
        f"{metrics['supervision_remaining']} remaining",
    )
    c.metric(
        "Registrar active CPD hours",
        f"{metrics['active_cpd_hours']} / {req['active_cpd_hours']}",
        f"{metrics['active_cpd_remaining']} remaining",
    )

    if metrics["half_practice_report_due"]:
        st.warning("Half-way supervised practice threshold reached. Progress report may be due.")
    else:
        st.info(f"Half-way progress report trigger: {metrics['half_practice_due_at']} practice hours.")

    if area:
        summary = _competency_summary(portfolio, area)
        if summary["total"] > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Competencies developing+", f"{summary['developing_or_better']} / {summary['total']}")
            c2.metric("Competencies achieved+", f"{summary['achieved_or_confirmed']} / {summary['total']}")
            c3.metric("Supervisor confirmed", f"{summary['supervisor_confirmed']} / {summary['total']}")

    upcoming = _upcoming_registrar_deadlines(portfolio)
    if upcoming:
        st.warning("Upcoming or overdue registrar deadlines within 60 days.")
        if not compact:
            st.dataframe(pd.DataFrame(upcoming), use_container_width=True, hide_index=True)


def render_endorsement_registrar(portfolio: dict) -> None:
    st.subheader("Endorsement / Registrar tracking")
    profile = portfolio["profile"]
    registrar = portfolio.setdefault("registrar", {})
    portfolio.setdefault("supervision_entries", [])
    portfolio.setdefault("competency_assessments", [])
    portfolio.setdefault("registrar_deadlines", [])
    if not (profile.get("is_registrar") or profile.get("has_endorsement")):
        st.info("Enable endorsement or registrar status in the sidebar to use this section.")
        return
    registrar["enabled"] = st.checkbox("Enable registrar tracking", value=registrar.get("enabled", profile.get("is_registrar", False)))
    if not registrar["enabled"]:
        st.info("Registrar tracking is currently disabled.")
        return
    st.markdown("### Registrar setup")
    c1, c2 = st.columns(2)
    current_area = registrar.get("area") or profile.get("registrar_area") or (profile.get("endorsements", [ENDORSEMENT_OPTIONS[0]])[0] if profile.get("endorsements") else ENDORSEMENT_OPTIONS[0])
    registrar["area"] = c1.selectbox("Endorsement / registrar area", ENDORSEMENT_OPTIONS, index=ENDORSEMENT_OPTIONS.index(current_area) if current_area in ENDORSEMENT_OPTIONS else 0)
    pathways = list(REGISTRAR_REQUIREMENTS.keys())
    registrar["qualification_pathway"] = c2.selectbox("Qualification pathway", pathways, index=pathways.index(registrar.get("qualification_pathway", pathways[-1])) if registrar.get("qualification_pathway") in pathways else len(pathways)-1)
    c3, c4, c5 = st.columns(3)
    registrar["program_approval_date"] = c3.text_input("Program approval date", value=registrar.get("program_approval_date", ""))
    registrar["program_start_date"] = c4.text_input("Program start date", value=registrar.get("program_start_date", ""))
    registrar["target_completion_date"] = c5.text_input("Target completion date", value=registrar.get("target_completion_date", ""))
    registrar["principal_supervisor"] = st.text_input("Principal supervisor", value=registrar.get("principal_supervisor", ""))
    registrar["secondary_supervisors"] = st.text_area("Secondary supervisor(s)", value=registrar.get("secondary_supervisors", ""))
    registrar["practice_role"] = st.text_area("Approved practice role / work role", value=registrar.get("practice_role", ""))
    st.markdown("### Registrar progress dashboard")
    render_registrar_progress_dashboard(portfolio, compact=False)
    st.markdown("### Supervision log")
    competency_map = get_competency_map(registrar["area"])
    with st.form("registrar_supervision_form", clear_on_submit=True):
        s1, s2, s3 = st.columns(3)
        supervision_date = s1.date_input("Supervision date", value=date.today())
        supervision_hours = s2.number_input("Supervision hours", min_value=0.0, step=0.25, format="%.2f")
        practice_hours = s3.number_input("Practice hours accrued since last supervision", min_value=0.0, step=0.25, format="%.2f")
        supervisor_name = st.text_input("Supervisor name")
        supervision_type = st.selectbox("Supervision type", ["Principal", "Secondary", "Group", "Other"])
        competency_domains = st.multiselect("Competency domains discussed", list(competency_map.keys()))
        notes = st.text_area("Supervision notes / learning points")
        evidence = st.text_input("Evidence / where stored")
        if st.form_submit_button("Add supervision entry"):
            portfolio["supervision_entries"].append({"id": new_id(), "date": supervision_date.isoformat(), "hours": round(float(supervision_hours), 2), "practice_hours": round(float(practice_hours), 2), "supervisor_name": supervisor_name, "supervision_type": supervision_type, "competency_domains": competency_domains, "notes": notes, "evidence": evidence, "endorsement_area": registrar["area"]})
            st.success("Supervision entry added."); st.rerun()
    if portfolio["supervision_entries"]:
        st.dataframe(pd.DataFrame(portfolio["supervision_entries"]), use_container_width=True, hide_index=True)
    selected_area = registrar["area"]
    st.markdown(f"### Competency development tracker — {selected_area}")
    existing = {(x.get("endorsement_area"), x.get("domain"), x.get("subdomain")): x for x in portfolio["competency_assessments"]}
    updated = [x for x in portfolio["competency_assessments"] if x.get("endorsement_area") != selected_area]
    for domain, subdomains in competency_map.items():
        with st.expander(domain):
            for subdomain in subdomains:
                current = existing.get((selected_area, domain, subdomain), {})
                c1, c2 = st.columns([2, 1])
                rating = c1.selectbox(subdomain, COMPETENCY_RATINGS, index=COMPETENCY_RATINGS.index(current.get("rating", "Not yet addressed")) if current.get("rating") in COMPETENCY_RATINGS else 0, key=f"competency_{selected_area}_{domain}_{subdomain}")
                last_reviewed = c2.text_input("Last reviewed", value=current.get("last_reviewed", ""), key=f"reviewed_{selected_area}_{domain}_{subdomain}")
                evidence = st.text_area("Evidence / supervisor comments", value=current.get("evidence", ""), key=f"evidence_{selected_area}_{domain}_{subdomain}")
                updated.append({"endorsement_area": selected_area, "domain": domain, "subdomain": subdomain, "rating": rating, "last_reviewed": last_reviewed, "evidence": evidence})
    portfolio["competency_assessments"] = updated
    st.markdown("### Progress reports and deadlines")
    with st.form("registrar_deadline_form", clear_on_submit=True):
        d1, d2 = st.columns(2)
        deadline_type = d1.selectbox("Deadline type", ["Six-month progress report", "Half-way progress report", "Final progress report", "Endorsement application", "Supervisor change", "Practice role change", "Other"])
        due_date = d2.date_input("Due date", value=date.today())
        status = st.selectbox("Status", ["Not started", "In progress", "Submitted", "Completed", "Not applicable"])
        notes = st.text_area("Deadline notes")
        if st.form_submit_button("Add deadline"):
            portfolio["registrar_deadlines"].append({"id": new_id(), "type": deadline_type, "due_date": due_date.isoformat(), "status": status, "notes": notes})
            st.success("Deadline added."); st.rerun()
    if portfolio["registrar_deadlines"]:
        st.dataframe(pd.DataFrame(portfolio["registrar_deadlines"]), use_container_width=True, hide_index=True)
        today = date.today()
        upcoming = []
        for item in portfolio["registrar_deadlines"]:
            try:
                due = datetime.strptime(item["due_date"], "%Y-%m-%d").date()
                if item.get("status") not in ["Submitted", "Completed", "Not applicable"] and due <= today + timedelta(days=60):
                    upcoming.append(item)
            except Exception:
                pass
        if upcoming:
            st.warning("You have upcoming or overdue registrar deadlines within 60 days.")
            st.dataframe(pd.DataFrame(upcoming), use_container_width=True, hide_index=True)
