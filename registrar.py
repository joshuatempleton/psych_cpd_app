from __future__ import annotations
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from calculations import compute_registrar_metrics
from constants import COMPETENCY_RATINGS, ENDORSEMENT_OPTIONS, EVIDENCE_OPTIONS, REGISTRAR_REQUIREMENTS, get_competency_map
from models import new_id
from utils import delete_entry, get_entry_by_id, parse_iso_date, safe_float, upsert_entry


def _upcoming_registrar_deadlines(portfolio: dict, days: int = 60) -> list[dict]:
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

    p1, p2 = st.columns(2)
    p1.metric(
        "Practice log entries",
        metrics["practice_log_entry_count"],
        "source of practice hours",
    )
    p2.metric(
        "Direct client contact in selected annual cycle",
        f"{metrics['direct_client_contact_hours_selected_cycle']} / 176.0",
        f"{metrics['direct_client_contact_remaining_selected_cycle']} remaining",
    )
    st.caption("Registrar practice hours are calculated only from the Registrar Practice Log to avoid duplicate counting.")

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


def _render_registrar_active_cpd(portfolio: dict, endorsement_area: str) -> None:
    st.markdown("### Registrar active CPD")
    st.caption(
        "Enter registrar active CPD here first. Eligible hours are counted toward the registrar active CPD total "
        "and also flow into the selected annual CPD cycle as general CPD documentation."
    )

    entries = portfolio.setdefault("registrar_cpd_entries", [])

    if entries:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Date": e.get("date"),
                        "Endorsement area": e.get("endorsement_area"),
                        "Activity": e.get("activity_details"),
                        "Hours": e.get("hours"),
                        "Counts to annual CPD": "Yes" if e.get("counts_towards_annual_cpd", True) else "No",
                        "Evidence": e.get("evidence_type"),
                        "Reflection": e.get("reflection"),
                    }
                    for e in entries
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    entry_options = {"New registrar CPD entry": None}
    for e in entries:
        entry_options[
            f"{e.get('date', '')} | {safe_float(e.get('hours'))}h | {e.get('activity_details', '')[:50]}"
        ] = e.get("id")

    selected_label = st.selectbox(
        "Choose a registrar CPD entry to edit, or leave on New registrar CPD entry",
        list(entry_options.keys()),
        key="registrar_cpd_select_entry",
    )
    selected_id = entry_options[selected_label]
    selected_entry = get_entry_by_id(entries, selected_id)

    default_evidence = selected_entry.get("evidence_type", EVIDENCE_OPTIONS[0]) if selected_entry else EVIDENCE_OPTIONS[0]
    if default_evidence not in EVIDENCE_OPTIONS:
        default_evidence = "Other"

    competency_map = get_competency_map(endorsement_area)
    domain_options = list(competency_map.keys())
    default_domains = selected_entry.get("competency_domains", []) if selected_entry else []

    with st.form("registrar_cpd_form", clear_on_submit=False):
        c1, c2 = st.columns([1, 1])
        entry_date = c1.date_input(
            "Date of registrar CPD",
            value=parse_iso_date(selected_entry.get("date")) if selected_entry else date.today(),
        )
        hours = c2.number_input(
            "Active CPD hours",
            min_value=0.0,
            step=0.25,
            format="%.2f",
            value=safe_float(selected_entry.get("hours")) if selected_entry else 0.0,
        )

        activity_details = st.text_area(
            "Activity details",
            value=selected_entry.get("activity_details", "") if selected_entry else "",
            help="Include title, provider, learning format, and why it is active CPD.",
        )
        competency_domains = st.multiselect(
            "Competency domains supported",
            options=domain_options,
            default=[d for d in default_domains if d in domain_options],
        )
        reflection = st.text_area(
            "Reflection / application to endorsed practice",
            value=selected_entry.get("reflection", "") if selected_entry else "",
        )
        e1, e2 = st.columns([2, 3])
        evidence_type = e1.selectbox("Evidence type", EVIDENCE_OPTIONS, index=EVIDENCE_OPTIONS.index(default_evidence))
        evidence_details = e2.text_input(
            "Evidence detail / where stored",
            value=selected_entry.get("evidence_details", "") if selected_entry else "",
        )
        counts_towards_annual_cpd = st.checkbox(
            "Also count this toward annual general CPD",
            value=selected_entry.get("counts_towards_annual_cpd", True) if selected_entry else True,
            help="Use this when the activity is eligible for both registrar active CPD and annual general CPD documentation.",
        )

        col1, col2 = st.columns(2)
        save_clicked = col1.form_submit_button("Save registrar CPD entry")
        delete_clicked = col2.form_submit_button("Delete selected registrar CPD entry")

    if save_clicked:
        upsert_entry(
            entries,
            {
                "id": selected_entry.get("id") if selected_entry else new_id(),
                "date": entry_date.isoformat(),
                "endorsement_area": endorsement_area,
                "hours": round(float(hours), 2),
                "activity_details": activity_details,
                "competency_domains": competency_domains,
                "reflection": reflection,
                "evidence_type": evidence_type,
                "evidence_details": evidence_details,
                "counts_towards_annual_cpd": counts_towards_annual_cpd,
                "source": "registrar_active_cpd",
            },
        )
        st.success("Registrar CPD entry saved.")
        st.rerun()

    if delete_clicked:
        if selected_id:
            delete_entry(entries, selected_id)
            st.success("Registrar CPD entry deleted.")
            st.rerun()
        else:
            st.warning("Select an existing registrar CPD entry first.")



def _render_practice_diary(portfolio: dict, selected_area: str, competency_map: dict) -> None:
    st.markdown("### Registrar practice log")
    st.caption(
        "Record each work day that contributes to registrar supervised practice. Practice hours for the registrar "
        "program are calculated from this log only. Supervision is recorded separately and does not add practice hours."
    )

    entries = portfolio.setdefault("registrar_practice_entries", [])
    domain_options = list(competency_map.keys())
    direct_contact_tasks = [
        "Psychological assessment",
        "Intervention",
        "Prevention",
        "Consultation",
        "Management planning",
        "Other direct client contact",
    ]

    if entries:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Date": e.get("date", ""),
                        "Endorsement area": e.get("endorsement_area", ""),
                        "Practice hours": e.get("practice_hours", 0.0),
                        "Direct client contact hours": e.get("direct_client_contact_hours", 0.0),
                        "Description": e.get("practice_description", ""),
                        "Competency domains": "; ".join(e.get("competency_domains", [])),
                        "Supervisor reviewed": "Yes" if e.get("supervisor_reviewed", False) else "No",
                        "Evidence": e.get("evidence", ""),
                    }
                    for e in entries
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    entry_options = {"New practice log entry": None}
    for e in entries:
        label = (
            f"{e.get('date', '')} | "
            f"{safe_float(e.get('practice_hours'))}h practice | "
            f"{e.get('practice_description', '')[:60]}"
        )
        entry_options[label] = e.get("id")

    selected_label = st.selectbox(
        "Choose a practice log entry to edit, or leave on New practice log entry",
        list(entry_options.keys()),
        key="registrar_practice_select_entry",
    )
    selected_id = entry_options[selected_label]
    selected_entry = get_entry_by_id(entries, selected_id)

    default_domains = selected_entry.get("competency_domains", []) if selected_entry else []
    default_tasks = selected_entry.get("direct_client_contact_tasks", []) if selected_entry else []

    with st.form("registrar_practice_form", clear_on_submit=False):
        d1, d2, d3 = st.columns(3)
        practice_date = d1.date_input(
            "Work date",
            value=parse_iso_date(selected_entry.get("date")) if selected_entry else date.today(),
        )
        practice_hours = d2.number_input(
            "Registrar practice hours for this day",
            min_value=0.0,
            step=0.25,
            format="%.2f",
            value=safe_float(selected_entry.get("practice_hours")) if selected_entry else 0.0,
            help="These hours are the single source of truth for registrar practice-hour totals.",
        )
        direct_client_contact_hours = d3.number_input(
            "Direct client contact hours",
            min_value=0.0,
            step=0.25,
            format="%.2f",
            value=safe_float(selected_entry.get("direct_client_contact_hours")) if selected_entry else 0.0,
            help="Direct client contact includes psychological assessment, intervention, prevention, consultation and management planning.",
        )

        practice_description = st.text_area(
            "Description of psychological practice performed",
            value=selected_entry.get("practice_description", "") if selected_entry else "",
            help="Use a de-identified description. Include the work performed and why it is within the approved registrar area.",
        )
        role_context = st.text_input(
            "Practice context / work role",
            value=selected_entry.get("role_context", "") if selected_entry else "",
            help="For example: psychosocial risk consulting, organisational assessment, advisory, research, training, policy or client consultation.",
        )
        competency_domains = st.multiselect(
            "Competency domains evidenced",
            options=domain_options,
            default=[d for d in default_domains if d in domain_options],
        )
        direct_client_contact_tasks_selected = st.multiselect(
            "Direct client contact task types",
            options=direct_contact_tasks,
            default=[t for t in default_tasks if t in direct_contact_tasks],
        )
        reflection = st.text_area(
            "Brief reflection / supervisor discussion points",
            value=selected_entry.get("reflection", "") if selected_entry else "",
        )
        evidence = st.text_input(
            "Evidence / where stored",
            value=selected_entry.get("evidence", "") if selected_entry else "",
            help="For example: de-identified work log, project file, supervision agenda, report reference or timesheet reference.",
        )
        supervisor_reviewed = st.checkbox(
            "Supervisor has reviewed or discussed this practice entry",
            value=selected_entry.get("supervisor_reviewed", False) if selected_entry else False,
        )

        col1, col2 = st.columns(2)
        save_clicked = col1.form_submit_button("Save practice log entry")
        delete_clicked = col2.form_submit_button("Delete selected practice log entry")

    if save_clicked:
        if direct_client_contact_hours > practice_hours:
            st.warning("Direct client contact hours cannot exceed total practice hours for the day.")
            return
        if not practice_description.strip():
            st.warning("Add a de-identified description of the work performed before saving.")
            return

        upsert_entry(
            entries,
            {
                "id": selected_entry.get("id") if selected_entry else new_id(),
                "date": practice_date.isoformat(),
                "endorsement_area": selected_area,
                "practice_hours": round(float(practice_hours), 2),
                "direct_client_contact_hours": round(float(direct_client_contact_hours), 2),
                "practice_description": practice_description,
                "role_context": role_context,
                "competency_domains": competency_domains,
                "direct_client_contact_tasks": direct_client_contact_tasks_selected,
                "reflection": reflection,
                "evidence": evidence,
                "supervisor_reviewed": supervisor_reviewed,
                "source": "registrar_practice_log",
            },
        )
        st.success("Practice log entry saved.")
        st.rerun()

    if delete_clicked:
        if selected_id:
            delete_entry(entries, selected_id)
            st.success("Practice log entry deleted.")
            st.rerun()
        else:
            st.warning("Select an existing practice log entry first.")


def _render_supervision_log(portfolio: dict, selected_area: str, competency_map: dict) -> None:
    st.markdown("### Supervision log")
    st.caption(
        "Eligible registrar supervision can also be documented as annual peer consultation. "
        "Practice hours are intentionally not entered here; they are calculated from the Registrar Practice Log only."
    )

    entries = portfolio.setdefault("supervision_entries", [])

    if entries:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Date": e.get("date", ""),
                        "Endorsement area": e.get("endorsement_area", ""),
                        "Supervisor": e.get("supervisor_name", ""),
                        "Type": e.get("supervision_type", ""),
                        "Supervision hours": e.get("hours", 0.0),
                        "Counts to annual peer consultation": "Yes" if e.get("counts_towards_peer_consultation", True) else "No",
                        "Competency domains": "; ".join(e.get("competency_domains", [])),
                        "Evidence": e.get("evidence", ""),
                    }
                    for e in entries
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    entry_options = {"New supervision entry": None}
    for e in entries:
        label = (
            f"{e.get('date', '')} | "
            f"{safe_float(e.get('hours'))}h supervision | "
            f"{e.get('supervisor_name', '')[:40]}"
        )
        entry_options[label] = e.get("id")

    selected_label = st.selectbox(
        "Choose a supervision entry to edit, or leave on New supervision entry",
        list(entry_options.keys()),
        key="registrar_supervision_select_entry",
    )
    selected_id = entry_options[selected_label]
    selected_entry = get_entry_by_id(entries, selected_id)

    default_type = selected_entry.get("supervision_type", "Principal") if selected_entry else "Principal"
    supervision_types = ["Principal", "Secondary", "Group", "Other"]
    if default_type not in supervision_types:
        default_type = "Other"

    domain_options = list(competency_map.keys())
    default_domains = selected_entry.get("competency_domains", []) if selected_entry else []

    with st.form("registrar_supervision_form", clear_on_submit=False):
        s1, s2 = st.columns(2)
        supervision_date = s1.date_input(
            "Supervision date",
            value=parse_iso_date(selected_entry.get("date")) if selected_entry else date.today(),
        )
        supervision_hours = s2.number_input(
            "Supervision hours",
            min_value=0.0,
            step=0.25,
            format="%.2f",
            value=safe_float(selected_entry.get("hours")) if selected_entry else 0.0,
        )
        supervisor_name = st.text_input(
            "Supervisor name",
            value=selected_entry.get("supervisor_name", "") if selected_entry else "",
        )
        supervision_type = st.selectbox(
            "Supervision type",
            supervision_types,
            index=supervision_types.index(default_type),
        )
        competency_domains = st.multiselect(
            "Competency domains discussed",
            options=domain_options,
            default=[d for d in default_domains if d in domain_options],
        )
        notes = st.text_area(
            "Supervision notes / learning points",
            value=selected_entry.get("notes", "") if selected_entry else "",
        )
        evidence = st.text_input(
            "Evidence / where stored",
            value=selected_entry.get("evidence", "") if selected_entry else "",
        )
        counts_towards_peer = st.checkbox(
            "Also count this supervision toward annual peer consultation",
            value=selected_entry.get("counts_towards_peer_consultation", True) if selected_entry else True,
            help="Use this when registrar supervision is eligible to document annual peer consultation requirements.",
        )

        col1, col2 = st.columns(2)
        save_clicked = col1.form_submit_button("Save supervision entry")
        delete_clicked = col2.form_submit_button("Delete selected supervision entry")

    if save_clicked:
        upsert_entry(
            entries,
            {
                "id": selected_entry.get("id") if selected_entry else new_id(),
                "date": supervision_date.isoformat(),
                "hours": round(float(supervision_hours), 2),
                "practice_hours": 0.0,
                "supervisor_name": supervisor_name,
                "supervision_type": supervision_type,
                "competency_domains": competency_domains,
                "notes": notes,
                "evidence": evidence,
                "endorsement_area": selected_area,
                "counts_towards_peer_consultation": counts_towards_peer,
                "source": "registrar_supervision",
            },
        )
        st.success("Supervision entry saved.")
        st.rerun()

    if delete_clicked:
        if selected_id:
            delete_entry(entries, selected_id)
            st.success("Supervision entry deleted.")
            st.rerun()
        else:
            st.warning("Select an existing supervision entry first.")


def render_endorsement_registrar(portfolio: dict) -> None:
    st.subheader("Endorsement / Registrar tracking")
    profile = portfolio["profile"]
    registrar = portfolio.setdefault("registrar", {})
    portfolio.setdefault("supervision_entries", [])
    portfolio.setdefault("registrar_cpd_entries", [])
    portfolio.setdefault("registrar_practice_entries", [])
    portfolio.setdefault("competency_assessments", [])
    portfolio.setdefault("registrar_deadlines", [])

    if not (profile.get("is_registrar") or profile.get("has_endorsement")):
        st.info("Enable endorsement or registrar status in the sidebar to use this section.")
        return

    registrar["enabled"] = st.checkbox(
        "Enable registrar tracking",
        value=registrar.get("enabled", profile.get("is_registrar", False)),
    )
    if not registrar["enabled"]:
        st.info("Registrar tracking is currently disabled.")
        return

    st.info(
        "Registrar tracking is the source of truth while enabled. Registrar active CPD and supervision are entered here, "
        "then automatically counted in annual CPD/peer consultation reporting where marked eligible."
    )

    st.markdown("### Registrar setup")
    c1, c2 = st.columns(2)
    current_area = registrar.get("area") or profile.get("registrar_area") or (
        profile.get("endorsements", [ENDORSEMENT_OPTIONS[0]])[0]
        if profile.get("endorsements")
        else ENDORSEMENT_OPTIONS[0]
    )
    registrar["area"] = c1.selectbox(
        "Endorsement / registrar area",
        ENDORSEMENT_OPTIONS,
        index=ENDORSEMENT_OPTIONS.index(current_area) if current_area in ENDORSEMENT_OPTIONS else 0,
    )
    pathways = list(REGISTRAR_REQUIREMENTS.keys())
    registrar["qualification_pathway"] = c2.selectbox(
        "Qualification pathway",
        pathways,
        index=pathways.index(registrar.get("qualification_pathway", pathways[-1]))
        if registrar.get("qualification_pathway") in pathways
        else len(pathways) - 1,
    )

    c3, c4, c5 = st.columns(3)
    registrar["program_approval_date"] = c3.text_input("Program approval date", value=registrar.get("program_approval_date", ""))
    registrar["program_start_date"] = c4.text_input("Program start date", value=registrar.get("program_start_date", ""))
    registrar["target_completion_date"] = c5.text_input("Target completion date", value=registrar.get("target_completion_date", ""))
    registrar["principal_supervisor"] = st.text_input("Principal supervisor", value=registrar.get("principal_supervisor", ""))
    registrar["secondary_supervisors"] = st.text_area("Secondary supervisor(s)", value=registrar.get("secondary_supervisors", ""))
    registrar["practice_role"] = st.text_area("Approved practice role / work role", value=registrar.get("practice_role", ""))

    st.markdown("### Registrar progress dashboard")
    render_registrar_progress_dashboard(portfolio, compact=False)

    selected_area = registrar["area"]
    competency_map = get_competency_map(selected_area)

    _render_practice_diary(portfolio, selected_area, competency_map)

    _render_supervision_log(portfolio, selected_area, competency_map)

    _render_registrar_active_cpd(portfolio, selected_area)

    st.markdown(f"### Competency development tracker — {selected_area}")
    existing = {
        (x.get("endorsement_area"), x.get("domain"), x.get("subdomain")): x
        for x in portfolio["competency_assessments"]
    }
    updated = [x for x in portfolio["competency_assessments"] if x.get("endorsement_area") != selected_area]

    for domain, subdomains in competency_map.items():
        with st.expander(domain):
            for subdomain in subdomains:
                current = existing.get((selected_area, domain, subdomain), {})
                c1, c2 = st.columns([2, 1])
                rating = c1.selectbox(
                    subdomain,
                    COMPETENCY_RATINGS,
                    index=COMPETENCY_RATINGS.index(current.get("rating", "Not yet addressed"))
                    if current.get("rating") in COMPETENCY_RATINGS
                    else 0,
                    key=f"competency_{selected_area}_{domain}_{subdomain}",
                )
                last_reviewed = c2.text_input(
                    "Last reviewed",
                    value=current.get("last_reviewed", ""),
                    key=f"reviewed_{selected_area}_{domain}_{subdomain}",
                )
                evidence = st.text_area(
                    "Evidence / supervisor comments",
                    value=current.get("evidence", ""),
                    key=f"evidence_{selected_area}_{domain}_{subdomain}",
                )
                updated.append(
                    {
                        "endorsement_area": selected_area,
                        "domain": domain,
                        "subdomain": subdomain,
                        "rating": rating,
                        "last_reviewed": last_reviewed,
                        "evidence": evidence,
                    }
                )

    portfolio["competency_assessments"] = updated

    st.markdown("### Progress reports and deadlines")
    with st.form("registrar_deadline_form", clear_on_submit=True):
        d1, d2 = st.columns(2)
        deadline_type = d1.selectbox(
            "Deadline type",
            [
                "Six-month progress report",
                "Half-way progress report",
                "Final progress report",
                "Endorsement application",
                "Supervisor change",
                "Practice role change",
                "Other",
            ],
        )
        due_date = d2.date_input("Due date", value=date.today())
        status = st.selectbox("Status", ["Not started", "In progress", "Submitted", "Completed", "Not applicable"])
        notes = st.text_area("Deadline notes")
        if st.form_submit_button("Add deadline"):
            portfolio["registrar_deadlines"].append(
                {"id": new_id(), "type": deadline_type, "due_date": due_date.isoformat(), "status": status, "notes": notes}
            )
            st.success("Deadline added.")
            st.rerun()

    if portfolio["registrar_deadlines"]:
        st.dataframe(pd.DataFrame(portfolio["registrar_deadlines"]), use_container_width=True, hide_index=True)
        upcoming = _upcoming_registrar_deadlines(portfolio)
        if upcoming:
            st.warning("You have upcoming or overdue registrar deadlines within 60 days.")
            st.dataframe(pd.DataFrame(upcoming), use_container_width=True, hide_index=True)
