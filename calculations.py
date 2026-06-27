from __future__ import annotations
from typing import Any

from constants import REGISTRAR_REQUIREMENTS
from utils import available_cpd_cycle_years, cpd_cycle_label, in_cpd_cycle, safe_float


def selected_cpd_cycle_year_end(portfolio: dict[str, Any]) -> int:
    """Return the annual CPD cycle currently being viewed."""
    settings = portfolio.get("cpd_cycle_settings", {})
    profile = portfolio.get("profile", {})
    return int(settings.get("selected_year_end") or profile.get("registration_cycle_year_end"))


def compute_targets(profile: dict[str, Any]) -> dict[str, Any]:
    full_year = bool(profile.get("full_year_general_registration", True))
    months = max(0, min(int(profile.get("months_general_registration", 12) or 12), 12))

    if full_year:
        total_target, peer_target, general_target = 30.0, 10.0, 20.0
    else:
        total_target = round(months * 2.5, 2)
        peer_target = round(months * (50 / 60), 2)
        general_target = round(months * (100 / 60), 2)

    year_end = int(profile["registration_cycle_year_end"])
    return {
        "total_target": total_target,
        "peer_target": peer_target,
        "general_target": general_target,
        "cycle_year_end": year_end,
        "cycle_label": cpd_cycle_label(year_end),
    }


def _annual_registrar_cpd_in_cycle(portfolio: dict[str, Any], cycle_year_end: int) -> list[dict[str, Any]]:
    return [
        {**x, "source": "registrar_active_cpd"}
        for x in portfolio.get("registrar_cpd_entries", [])
        if x.get("counts_towards_annual_cpd", True) and in_cpd_cycle(x.get("date"), cycle_year_end)
    ]


def _annual_registrar_supervision_in_cycle(portfolio: dict[str, Any], cycle_year_end: int) -> list[dict[str, Any]]:
    return [
        {**x, "source": "registrar_supervision"}
        for x in portfolio.get("supervision_entries", [])
        if x.get("counts_towards_peer_consultation", True) and in_cpd_cycle(x.get("date"), cycle_year_end)
    ]


def compute_metrics(portfolio: dict[str, Any]) -> dict[str, Any]:
    """Compute annual CPD metrics for the selected CPD cycle.

    General CPD is entered in the CPD tab. Registrar active CPD and registrar
    supervision are entered in the Endorsement / Registrar tab and flow down
    into annual CPD/peer-consultation documentation when marked eligible.
    """
    profile = portfolio["profile"]
    profile["registration_cycle_year_end"] = selected_cpd_cycle_year_end(portfolio)
    targets = compute_targets(profile)
    cycle_year_end = int(targets["cycle_year_end"])

    general_cpd_in_cycle = [
        {**x, "source": x.get("source", "general_cpd")}
        for x in portfolio.get("cpd_entries", [])
        if in_cpd_cycle(x.get("date"), cycle_year_end)
    ]
    registrar_cpd_in_cycle = _annual_registrar_cpd_in_cycle(portfolio, cycle_year_end)

    peer_in_cycle = [
        {**x, "source": x.get("source", "peer_consultation")}
        for x in portfolio.get("peer_entries", [])
        if in_cpd_cycle(x.get("date"), cycle_year_end)
    ]
    registrar_supervision_in_cycle = _annual_registrar_supervision_in_cycle(portfolio, cycle_year_end)

    cpd_in_cycle = general_cpd_in_cycle + registrar_cpd_in_cycle
    peer_sources_in_cycle = peer_in_cycle + registrar_supervision_in_cycle

    general_cpd_hours = round(sum(safe_float(x.get("hours")) for x in general_cpd_in_cycle), 2)
    registrar_active_cpd_hours = round(sum(safe_float(x.get("hours")) for x in registrar_cpd_in_cycle), 2)
    cpd_hours = round(general_cpd_hours + registrar_active_cpd_hours, 2)

    standalone_peer_hours = round(sum(safe_float(x.get("own_practice_hours")) for x in peer_in_cycle), 2)
    registrar_supervision_peer_hours = round(sum(safe_float(x.get("hours")) for x in registrar_supervision_in_cycle), 2)
    peer_hours = round(standalone_peer_hours + registrar_supervision_peer_hours, 2)

    total_hours = round(cpd_hours + peer_hours, 2)

    return {
        **targets,
        "cpd_hours": cpd_hours,
        "general_cpd_hours": general_cpd_hours,
        "registrar_active_cpd_hours_in_cycle": registrar_active_cpd_hours,
        "peer_hours": peer_hours,
        "standalone_peer_hours": standalone_peer_hours,
        "registrar_supervision_peer_hours_in_cycle": registrar_supervision_peer_hours,
        "total_hours": total_hours,
        "cpd_remaining": round(max(0.0, targets["general_target"] - cpd_hours), 2),
        "peer_remaining": round(max(0.0, targets["peer_target"] - peer_hours), 2),
        "total_remaining": round(max(0.0, targets["total_target"] - total_hours), 2),
        "cpd_in_cycle": cpd_in_cycle,
        "peer_in_cycle": peer_sources_in_cycle,
        "general_cpd_in_cycle": general_cpd_in_cycle,
        "registrar_cpd_in_cycle": registrar_cpd_in_cycle,
        "standalone_peer_in_cycle": peer_in_cycle,
        "registrar_supervision_in_cycle": registrar_supervision_in_cycle,
        "all_available_cycle_years": available_cpd_cycle_years(portfolio),
    }


def compute_all_cycle_summaries(portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    """Return annual CPD summaries for every cycle represented in the JSON file."""
    original_selected = selected_cpd_cycle_year_end(portfolio)
    rows: list[dict[str, Any]] = []

    for year_end in available_cpd_cycle_years(portfolio):
        portfolio.setdefault("cpd_cycle_settings", {})["selected_year_end"] = year_end
        portfolio["profile"]["registration_cycle_year_end"] = year_end
        metrics = compute_metrics(portfolio)
        rows.append(
            {
                "cycle_year_end": year_end,
                "cycle_label": metrics["cycle_label"],
                "total_hours": metrics["total_hours"],
                "general_cpd_hours_total": metrics["cpd_hours"],
                "general_cpd_hours_from_general_log": metrics["general_cpd_hours"],
                "general_cpd_hours_from_registrar_active_cpd": metrics["registrar_active_cpd_hours_in_cycle"],
                "peer_consultation_hours_total": metrics["peer_hours"],
                "peer_hours_from_peer_log": metrics["standalone_peer_hours"],
                "peer_hours_from_registrar_supervision": metrics["registrar_supervision_peer_hours_in_cycle"],
                "total_target": metrics["total_target"],
                "general_cpd_target": metrics["general_target"],
                "peer_consultation_target": metrics["peer_target"],
                "total_remaining": metrics["total_remaining"],
                "general_cpd_remaining": metrics["cpd_remaining"],
                "peer_consultation_remaining": metrics["peer_remaining"],
            }
        )

    portfolio.setdefault("cpd_cycle_settings", {})["selected_year_end"] = original_selected
    portfolio["profile"]["registration_cycle_year_end"] = original_selected
    return rows


def compute_registrar_metrics(portfolio: dict[str, Any]) -> dict[str, Any]:
    """Compute registrar metrics across the whole registrar program."""
    registrar = portfolio.get("registrar", {})
    pathway = registrar.get("qualification_pathway", "Approved sixth-year Masters pathway")
    requirements = REGISTRAR_REQUIREMENTS.get(
        pathway,
        REGISTRAR_REQUIREMENTS["Approved sixth-year Masters pathway"],
    )

    supervision_entries = portfolio.get("supervision_entries", [])
    registrar_cpd_entries = portfolio.get("registrar_cpd_entries", [])

    supervision_hours = round(sum(safe_float(x.get("hours")) for x in supervision_entries), 2)
    active_cpd_hours = round(sum(safe_float(x.get("hours")) for x in registrar_cpd_entries), 2)
    practice_hours = round(sum(safe_float(x.get("practice_hours")) for x in supervision_entries), 2)

    half_practice_due_at = requirements["practice_hours"] / 2

    return {
        "requirements": requirements,
        "practice_hours": practice_hours,
        "practice_remaining": round(max(0, requirements["practice_hours"] - practice_hours), 2),
        "supervision_hours": supervision_hours,
        "supervision_remaining": round(max(0, requirements["supervision_hours"] - supervision_hours), 2),
        "active_cpd_hours": active_cpd_hours,
        "active_cpd_remaining": round(max(0, requirements["active_cpd_hours"] - active_cpd_hours), 2),
        "half_practice_due_at": half_practice_due_at,
        "half_practice_report_due": practice_hours >= half_practice_due_at,
        "program_start_date": registrar.get("program_start_date", ""),
        "target_completion_date": registrar.get("target_completion_date", ""),
        "status": registrar.get("status", "Active"),
    }


def build_insights(portfolio: dict[str, Any], metrics: dict[str, Any]) -> str:
    lines = [
        "Annual CPD view:",
        f"- Registration cycle: {metrics['cycle_label']}",
        f"- Total logged hours in selected cycle: {metrics['total_hours']} / {metrics['total_target']}",
        f"- General CPD logged: {metrics['cpd_hours']} / {metrics['general_target']}",
        f"  - From general CPD log: {metrics['general_cpd_hours']}",
        f"  - From registrar active CPD: {metrics['registrar_active_cpd_hours_in_cycle']}",
        f"- Peer consultation logged: {metrics['peer_hours']} / {metrics['peer_target']}",
        f"  - From peer consultation log: {metrics['standalone_peer_hours']}",
        f"  - From registrar supervision: {metrics['registrar_supervision_peer_hours_in_cycle']}",
    ]
    lines.append(
        f"- Remaining total hours: {metrics['total_remaining']}"
        if metrics["total_remaining"] > 0
        else "- Total CPD target has been met or exceeded for the selected cycle."
    )
    lines.append(
        f"- Remaining peer consultation hours: {metrics['peer_remaining']}"
        if metrics["peer_remaining"] > 0
        else "- Peer consultation target has been met or exceeded for the selected cycle."
    )

    if portfolio["profile"].get("is_registrar") and portfolio.get("registrar", {}).get("enabled"):
        reg = compute_registrar_metrics(portfolio)
        lines += [
            "",
            "Registrar program view:",
            "- Registrar totals are cumulative across the whole program and do not reset each CPD year.",
            "- Registrar active CPD and supervision are also counted in annual CPD where marked eligible.",
            f"- Practice hours: {reg['practice_hours']} / {reg['requirements']['practice_hours']}",
            f"- Supervision hours: {reg['supervision_hours']} / {reg['requirements']['supervision_hours']}",
            f"- Active CPD hours: {reg['active_cpd_hours']} / {reg['requirements']['active_cpd_hours']}",
        ]

    return "\n".join(lines)
