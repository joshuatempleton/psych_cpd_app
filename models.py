from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Any
from constants import APP_TITLE, APP_VERSION


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def current_cpd_cycle_year_end() -> int:
    current_year = date.today().year
    return current_year if date.today() <= date(current_year, 11, 30) else current_year + 1


def default_profile() -> dict[str, Any]:
    year_end = current_cpd_cycle_year_end()
    return {
        "psychologist_name": "",
        "signature_name": "",
        # This is the annual CPD cycle currently being viewed/calculated.
        # The JSON keeps all years; dashboard/export functions filter by this value.
        "registration_cycle_year_end": year_end,
        "full_year_general_registration": True,
        "months_general_registration": 12,
        "has_board_exemption": False,
        "exemption_notes": "",
        "is_part_time": False,
        "has_endorsement": False,
        "endorsements": [],
        "is_registrar": False,
        "registrar_area": "",
        "is_board_approved_supervisor": False,
        "supervisor_last_training_date": "",
        "practice_context": "",
        "position_description_note": "",
    }


def default_goal(n: int) -> dict[str, Any]:
    return {
        "id": new_id(),
        "title": f"Goal {n}",
        "learning_need": "",
        "proposed_activities": "",
        "proposed_dates": "",
        "anticipated_outcomes": "",
        "review_date": "",
        "outcomes_achieved": "",
        "status": "Planned",
    }


def default_portfolio() -> dict[str, Any]:
    year_end = current_cpd_cycle_year_end()
    return {
        "meta": {
            "app_title": APP_TITLE,
            "app_version": APP_VERSION,
            "created_at": datetime.now().isoformat(),
            "last_saved_at": None,
            "portfolio_id": new_id(),
        },
        "profile": default_profile(),
        "cpd_cycle_settings": {
            "selected_year_end": year_end,
            "note": "The portfolio file keeps all years. Annual CPD dashboards filter by selected_year_end.",
        },
        "learning_goals": [default_goal(1), default_goal(2), default_goal(3)],
        "cpd_entries": [],
        "peer_entries": [],
        # Registrar CPD entries are logged in the registrar module first.
        # Eligible hours are also counted in the annual CPD dashboard/export.
        "registrar_cpd_entries": [],
        "registrar_practice_entries": [],
        "summary_insights": "",
        "registrar": {
            "enabled": False,
            "area": "",
            "qualification_pathway": "Approved sixth-year Masters pathway",
            "program_approval_date": "",
            "program_start_date": "",
            "target_completion_date": "",
            "principal_supervisor": "",
            "secondary_supervisors": "",
            "practice_role": "",
            "notes": "",
            "status": "Active",
        },
        "supervision_entries": [],
        "competency_assessments": [],
        "registrar_deadlines": [],
    }


def _migrate_legacy_supervision_practice_hours(data: dict[str, Any]) -> None:
    """Move older supervision-accrued practice hours into the practice log.

    Version 2.6 makes registrar practice log entries the single source of
    truth for registrar practice hours. Earlier portfolios could store
    practice hours against supervision entries. This migration preserves those
    hours as auditable legacy practice log entries and clears the old
    supervision practice-hours field to avoid double counting.
    """
    practice_entries = data.setdefault("registrar_practice_entries", [])
    supervision_entries = data.setdefault("supervision_entries", [])

    migrated_supervision_ids = {
        entry.get("original_supervision_entry_id")
        for entry in practice_entries
        if entry.get("source") == "legacy_supervision_practice_migration"
    }

    migrated_any = False
    for supervision in supervision_entries:
        supervision_id = supervision.get("id") or new_id()
        supervision["id"] = supervision_id
        legacy_hours = safe_float_local(supervision.get("practice_hours"))
        already_migrated = supervision.get("practice_hours_migrated_to_practice_log", False)

        if legacy_hours > 0 and supervision_id not in migrated_supervision_ids and not already_migrated:
            practice_entries.append(
                {
                    "id": new_id(),
                    "date": supervision.get("date", ""),
                    "endorsement_area": supervision.get("endorsement_area", data.get("registrar", {}).get("area", "")),
                    "practice_hours": round(legacy_hours, 2),
                    "direct_client_contact_hours": 0.0,
                    "practice_description": (
                        "Legacy registrar practice hours migrated from a supervision entry. "
                        "Replace this with day-level practice log entries where possible."
                    ),
                    "organisation_or_client_context": "Legacy supervision entry",
                    "competency_domains": supervision.get("competency_domains", []),
                    "evidence": supervision.get("evidence", ""),
                    "supervisor_reviewed": True,
                    "source": "legacy_supervision_practice_migration",
                    "original_supervision_entry_id": supervision_id,
                }
            )
            migrated_any = True

        if legacy_hours > 0 or already_migrated:
            supervision["legacy_practice_hours_migrated"] = round(legacy_hours, 2)
            supervision["practice_hours"] = 0.0
            supervision["practice_hours_migrated_to_practice_log"] = True

    if migrated_any:
        data.setdefault("meta", {})["v2_6_practice_hour_migration"] = datetime.now().isoformat()


def safe_float_local(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalise_portfolio(data: dict[str, Any]) -> dict[str, Any]:
    template = default_portfolio()
    for key, value in template.items():
        data.setdefault(key, value)

    data.setdefault("profile", {})
    for key, value in default_profile().items():
        data["profile"].setdefault(key, value)

    data.setdefault("cpd_cycle_settings", {})
    data["cpd_cycle_settings"].setdefault(
        "selected_year_end",
        int(data["profile"].get("registration_cycle_year_end", current_cpd_cycle_year_end())),
    )
    data["cpd_cycle_settings"].setdefault(
        "note",
        "The portfolio file keeps all years. Annual CPD dashboards filter by selected_year_end.",
    )

    # Keep the older profile field and the newer cycle settings in sync.
    data["profile"]["registration_cycle_year_end"] = int(data["cpd_cycle_settings"]["selected_year_end"])

    data.setdefault("registrar", {})
    for key, value in template["registrar"].items():
        data["registrar"].setdefault(key, value)

    data.setdefault("registrar_cpd_entries", [])
    data.setdefault("registrar_practice_entries", [])
    data.setdefault("supervision_entries", [])
    data.setdefault("competency_assessments", [])
    data.setdefault("registrar_deadlines", [])

    while len(data.get("learning_goals", [])) < 3:
        data.setdefault("learning_goals", []).append(default_goal(len(data["learning_goals"]) + 1))

    _migrate_legacy_supervision_practice_hours(data)

    return data
