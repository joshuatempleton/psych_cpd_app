from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Any
from constants import APP_TITLE, APP_VERSION

def new_id() -> str:
    return uuid.uuid4().hex[:10]

def default_profile() -> dict[str, Any]:
    current_year = date.today().year
    year_end = current_year if date.today() <= date(current_year, 11, 30) else current_year + 1
    return {
        "psychologist_name": "", "signature_name": "", "registration_cycle_year_end": year_end,
        "full_year_general_registration": True, "months_general_registration": 12,
        "has_board_exemption": False, "exemption_notes": "", "is_part_time": False,
        "has_endorsement": False, "endorsements": [], "is_registrar": False, "registrar_area": "",
        "is_board_approved_supervisor": False, "supervisor_last_training_date": "",
        "practice_context": "", "position_description_note": "",
    }

def default_goal(n: int) -> dict[str, Any]:
    return {"id": new_id(), "title": f"Goal {n}", "learning_need": "", "proposed_activities": "", "proposed_dates": "", "anticipated_outcomes": "", "review_date": "", "outcomes_achieved": "", "status": "Planned"}

def default_portfolio() -> dict[str, Any]:
    return {
        "meta": {"app_title": APP_TITLE, "app_version": APP_VERSION, "created_at": datetime.now().isoformat(), "last_saved_at": None, "portfolio_id": new_id()},
        "profile": default_profile(),
        "learning_goals": [default_goal(1), default_goal(2), default_goal(3)],
        "cpd_entries": [], "peer_entries": [], "summary_insights": "",
        "registrar": {"enabled": False, "area": "", "qualification_pathway": "Approved sixth-year Masters pathway", "program_approval_date": "", "program_start_date": "", "target_completion_date": "", "principal_supervisor": "", "secondary_supervisors": "", "practice_role": "", "notes": ""},
        "supervision_entries": [], "competency_assessments": [], "registrar_deadlines": [],
    }

def normalise_portfolio(data: dict[str, Any]) -> dict[str, Any]:
    template = default_portfolio()
    for key, value in template.items():
        data.setdefault(key, value)
    data.setdefault("profile", {})
    for key, value in default_profile().items():
        data["profile"].setdefault(key, value)
    data.setdefault("registrar", {})
    for key, value in template["registrar"].items():
        data["registrar"].setdefault(key, value)
    while len(data.get("learning_goals", [])) < 3:
        data.setdefault("learning_goals", []).append(default_goal(len(data["learning_goals"]) + 1))
    return data
