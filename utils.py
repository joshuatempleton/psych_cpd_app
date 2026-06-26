from __future__ import annotations
from datetime import date, datetime
from typing import Any

def safe_float(v: Any) -> float:
    try:
        return round(float(v), 2)
    except Exception:
        return 0.0

def parse_iso_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return date.today()
    return date.today()

def cpd_cycle_label(year_end: int) -> str:
    return f"1 Dec {year_end - 1} to 30 Nov {year_end}"

def in_cpd_cycle(entry_date: str | None, cycle_year_end: int) -> bool:
    if not entry_date:
        return False
    try:
        d = datetime.strptime(entry_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    return date(cycle_year_end - 1, 12, 1) <= d <= date(cycle_year_end, 11, 30)

def goal_title_map(goals: list[dict[str, Any]]) -> dict[str, str]:
    return {g["id"]: (g.get("title") or "Untitled goal") for g in goals}

def format_goal_links(goal_ids: list[str], goals_map: dict[str, str]) -> str:
    return "; ".join(goals_map.get(gid, gid) for gid in goal_ids or [])

def get_entry_by_id(entries: list[dict[str, Any]], entry_id: str | None) -> dict[str, Any] | None:
    if not entry_id:
        return None
    return next((entry for entry in entries if entry.get("id") == entry_id), None)

def upsert_entry(entries: list[dict[str, Any]], new_entry: dict[str, Any]) -> None:
    for idx, entry in enumerate(entries):
        if entry.get("id") == new_entry.get("id"):
            entries[idx] = new_entry
            return
    entries.append(new_entry)

def delete_entry(entries: list[dict[str, Any]], entry_id: str) -> None:
    entries[:] = [e for e in entries if e.get("id") != entry_id]
