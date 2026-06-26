from __future__ import annotations
from typing import Any
from constants import REGISTRAR_REQUIREMENTS
from utils import cpd_cycle_label, in_cpd_cycle, safe_float

def compute_targets(profile: dict[str, Any]) -> dict[str, Any]:
    full_year = bool(profile.get("full_year_general_registration", True))
    months = max(0, min(int(profile.get("months_general_registration", 12) or 12), 12))
    if full_year:
        total_target, peer_target, general_target = 30.0, 10.0, 20.0
    else:
        total_target = round(months * 2.5, 2)
        peer_target = round(months * (50 / 60), 2)
        general_target = round(months * (100 / 60), 2)
    endorsement_rules = {}
    endorsements = [e for e in profile.get("endorsements", []) if e]
    if len(endorsements) == 1:
        endorsement_rules[endorsements[0]] = 16.0
    elif len(endorsements) == 2:
        endorsement_rules[endorsements[0]] = 15.0
        endorsement_rules[endorsements[1]] = 15.0
    elif len(endorsements) >= 3:
        split = round(30.0 / len(endorsements), 2)
        for e in endorsements:
            endorsement_rules[e] = split
    year_end = int(profile["registration_cycle_year_end"])
    return {"total_target": total_target, "peer_target": peer_target, "general_target": general_target, "endorsement_targets": endorsement_rules, "cycle_label": cpd_cycle_label(year_end)}

def compute_metrics(portfolio: dict[str, Any]) -> dict[str, Any]:
    profile = portfolio["profile"]
    targets = compute_targets(profile)
    cycle_year_end = int(profile["registration_cycle_year_end"])
    cpd_in_cycle = [x for x in portfolio.get("cpd_entries", []) if in_cpd_cycle(x.get("date"), cycle_year_end)]
    peer_in_cycle = [x for x in portfolio.get("peer_entries", []) if in_cpd_cycle(x.get("date"), cycle_year_end)]
    cpd_hours = round(sum(safe_float(x.get("hours")) for x in cpd_in_cycle), 2)
    peer_hours = round(sum(safe_float(x.get("own_practice_hours")) for x in peer_in_cycle), 2)
    total_hours = round(cpd_hours + peer_hours, 2)
    endorsement_hours = {}
    for entry in cpd_in_cycle:
        area = entry.get("endorsement_area") or entry.get("area_of_practice") or "Unspecified"
        endorsement_hours[area] = round(endorsement_hours.get(area, 0.0) + safe_float(entry.get("hours")), 2)
    for entry in peer_in_cycle:
        area = entry.get("endorsement_area") or entry.get("area_of_practice") or "Unspecified"
        endorsement_hours[area] = round(endorsement_hours.get(area, 0.0) + safe_float(entry.get("own_practice_hours")), 2)
    return {**targets, "cpd_hours": cpd_hours, "peer_hours": peer_hours, "total_hours": total_hours, "cpd_remaining": round(max(0.0, targets["general_target"] - cpd_hours), 2), "peer_remaining": round(max(0.0, targets["peer_target"] - peer_hours), 2), "total_remaining": round(max(0.0, targets["total_target"] - total_hours), 2), "cpd_in_cycle": cpd_in_cycle, "peer_in_cycle": peer_in_cycle, "endorsement_hours": endorsement_hours}

def compute_registrar_metrics(portfolio: dict[str, Any]) -> dict[str, Any]:
    registrar = portfolio.get("registrar", {})
    pathway = registrar.get("qualification_pathway", "Approved sixth-year Masters pathway")
    requirements = REGISTRAR_REQUIREMENTS.get(pathway, REGISTRAR_REQUIREMENTS["Approved sixth-year Masters pathway"])
    supervision_hours = round(sum(safe_float(x.get("hours")) for x in portfolio.get("supervision_entries", [])), 2)
    active_cpd_hours = round(sum(safe_float(x.get("hours")) for x in portfolio.get("cpd_entries", []) if x.get("counts_towards_registrar")), 2)
    practice_hours = round(sum(safe_float(x.get("practice_hours")) for x in portfolio.get("supervision_entries", [])), 2)
    half_practice_due_at = requirements["practice_hours"] / 2
    return {"requirements": requirements, "practice_hours": practice_hours, "practice_remaining": round(max(0, requirements["practice_hours"] - practice_hours), 2), "supervision_hours": supervision_hours, "supervision_remaining": round(max(0, requirements["supervision_hours"] - supervision_hours), 2), "active_cpd_hours": active_cpd_hours, "active_cpd_remaining": round(max(0, requirements["active_cpd_hours"] - active_cpd_hours), 2), "half_practice_due_at": half_practice_due_at, "half_practice_report_due": practice_hours >= half_practice_due_at}

def build_insights(portfolio: dict[str, Any], metrics: dict[str, Any]) -> str:
    lines = [f"Registration cycle: {metrics['cycle_label']}", f"Total logged hours in cycle: {metrics['total_hours']} / {metrics['total_target']}", f"General CPD logged: {metrics['cpd_hours']} / {metrics['general_target']}", f"Peer consultation logged: {metrics['peer_hours']} / {metrics['peer_target']}"]
    lines.append(f"Remaining total hours: {metrics['total_remaining']}" if metrics["total_remaining"] > 0 else "Total CPD target has been met or exceeded.")
    lines.append(f"Remaining peer consultation hours: {metrics['peer_remaining']}" if metrics["peer_remaining"] > 0 else "Peer consultation target has been met or exceeded.")
    if portfolio["profile"].get("is_registrar") and portfolio.get("registrar", {}).get("enabled"):
        reg = compute_registrar_metrics(portfolio)
        lines += ["Registrar tracking:", f"- Practice hours: {reg['practice_hours']} / {reg['requirements']['practice_hours']}", f"- Supervision hours: {reg['supervision_hours']} / {reg['requirements']['supervision_hours']}", f"- Active CPD hours: {reg['active_cpd_hours']} / {reg['requirements']['active_cpd_hours']}"]
    return "\n".join(lines)
