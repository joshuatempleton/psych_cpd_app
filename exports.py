from __future__ import annotations
import io, zipfile
from typing import Any
import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt
from calculations import build_insights, compute_metrics, compute_registrar_metrics, compute_targets
from utils import format_goal_links, goal_title_map

def export_csv_zip(portfolio: dict[str, Any]) -> bytes:
    out = io.BytesIO()
    tables = {"learning_goals.csv": portfolio.get("learning_goals", []), "cpd_entries.csv": portfolio.get("cpd_entries", []), "peer_consultation_entries.csv": portfolio.get("peer_entries", []), "registrar_supervision_entries.csv": portfolio.get("supervision_entries", []), "registrar_competencies.csv": portfolio.get("competency_assessments", []), "registrar_deadlines.csv": portfolio.get("registrar_deadlines", [])}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, rows in tables.items():
            zf.writestr(filename, pd.DataFrame(rows).to_csv(index=False))
        metrics, reg = compute_metrics(portfolio), compute_registrar_metrics(portfolio)
        zf.writestr("summary.csv", pd.DataFrame([{"Metric": "Total CPD hours", "Value": metrics["total_hours"]}, {"Metric": "General CPD hours", "Value": metrics["cpd_hours"]}, {"Metric": "Peer consultation hours", "Value": metrics["peer_hours"]}, {"Metric": "Registrar practice hours", "Value": reg["practice_hours"]}, {"Metric": "Registrar supervision hours", "Value": reg["supervision_hours"]}, {"Metric": "Registrar active CPD hours", "Value": reg["active_cpd_hours"]}]).to_csv(index=False))
    out.seek(0)
    return out.getvalue()

def _add_table(doc: Document, headers: list[str], rows: list[list[Any]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for row_data in rows:
        row = table.add_row().cells
        for i, value in enumerate(row_data):
            row[i].text = "" if value is None else str(value)

def export_docx(portfolio: dict[str, Any]) -> bytes:
    metrics = compute_metrics(portfolio)
    goals_map = goal_title_map(portfolio["learning_goals"])
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Inches(0.6)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)
    title = doc.add_heading("Psychology CPD Portfolio Export", level=0)
    title.alignment = 1
    profile = portfolio["profile"]
    targets = compute_targets(profile)
    doc.add_heading("Portfolio details", level=1)
    _add_table(doc, ["Field", "Value"], [["Psychologist name", profile.get("psychologist_name", "")], ["Registration cycle", targets["cycle_label"]], ["Endorsements", ", ".join(profile.get("endorsements", []))], ["Registrar", "Yes" if profile.get("is_registrar") else "No"], ["Registrar area", portfolio.get("registrar", {}).get("area", "")]])
    doc.add_heading("Summary insights", level=1)
    for line in (portfolio.get("summary_insights") or build_insights(portfolio, metrics)).splitlines():
        doc.add_paragraph(line)
    doc.add_heading("Learning plan", level=1)
    _add_table(doc, ["Goal", "Learning need", "Proposed activities", "Dates", "Anticipated outcomes", "Review date", "Outcomes achieved"], [[g.get("title"), g.get("learning_need"), g.get("proposed_activities"), g.get("proposed_dates"), g.get("anticipated_outcomes"), g.get("review_date"), g.get("outcomes_achieved")] for g in portfolio.get("learning_goals", [])])
    doc.add_heading("CPD activity log", level=1)
    _add_table(doc, ["Date", "Type", "Details", "Area", "Endorsement area", "Hours", "Registrar active CPD", "Goals", "Evidence", "Reflection"], [[e.get("date"), e.get("activity_type"), e.get("activity_details"), e.get("area_of_practice"), e.get("endorsement_area"), e.get("hours"), "Yes" if e.get("counts_towards_registrar") else "No", format_goal_links(e.get("goal_ids", []), goals_map), f"{e.get('evidence_type','')}: {e.get('evidence_details','')}", e.get("reflection")] for e in portfolio.get("cpd_entries", [])])
    doc.add_heading("Peer consultation log", level=1)
    _add_table(doc, ["Date", "Format", "Focus", "Colleagues", "Total hours", "Own-practice hours", "Area", "Goals", "Evidence", "Reflection"], [[e.get("date"), e.get("format"), e.get("focus"), e.get("colleagues"), e.get("total_hours"), e.get("own_practice_hours"), e.get("area_of_practice"), format_goal_links(e.get("goal_ids", []), goals_map), f"{e.get('evidence_type','')}: {e.get('evidence_details','')}", e.get("reflection")] for e in portfolio.get("peer_entries", [])])
    doc.add_heading("Registrar supervision log", level=1)
    _add_table(doc, ["Date", "Hours", "Practice hours", "Supervisor", "Type", "Competency domains", "Notes", "Evidence"], [[e.get("date"), e.get("hours"), e.get("practice_hours"), e.get("supervisor_name"), e.get("supervision_type"), "; ".join(e.get("competency_domains", [])), e.get("notes"), e.get("evidence")] for e in portfolio.get("supervision_entries", [])])
    doc.add_heading("Endorsement competencies", level=1)
    _add_table(doc, ["Endorsement area", "Domain", "Subdomain", "Rating", "Last reviewed", "Evidence / comments"], [[e.get("endorsement_area"), e.get("domain"), e.get("subdomain"), e.get("rating"), e.get("last_reviewed"), e.get("evidence")] for e in portfolio.get("competency_assessments", [])])
    doc.add_heading("Registrar deadlines", level=1)
    _add_table(doc, ["Type", "Due date", "Status", "Notes"], [[e.get("type"), e.get("due_date"), e.get("status"), e.get("notes")] for e in portfolio.get("registrar_deadlines", [])])
    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out.getvalue()
