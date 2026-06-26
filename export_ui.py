from __future__ import annotations
import streamlit as st
from calculations import build_insights, compute_metrics
from exports import export_csv_zip, export_docx

def render_export(portfolio: dict) -> None:
    st.subheader("Audit-style export")
    st.write("Exports include a Word document and a CSV package for CPD, peer consultation, registrar supervision, competencies, and deadlines.")
    metrics = compute_metrics(portfolio)
    st.text_area("Export preview summary", value=portfolio.get("summary_insights") or build_insights(portfolio, metrics), height=160, disabled=True)
    base_name = portfolio["profile"].get("psychologist_name", "").strip().replace(" ", "_") or "psychology_cpd_portfolio"
    st.download_button("Download Word export (.docx)", data=export_docx(portfolio), file_name=f"{base_name}_audit_export.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    st.download_button("Download CSV export package (.zip)", data=export_csv_zip(portfolio), file_name=f"{base_name}_csv_export.zip", mime="application/zip")
    st.info("Store your external evidence files separately and keep them together with your Word export, CSV package, and JSON portfolio file.")
