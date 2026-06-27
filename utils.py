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


def cycle_year_end_for_date(value: Any) -> int | None:
    """Return the CPD cycle year-end for a date.

    CPD cycles run 1 Dec to 30 Nov. Example:
    - 2026-11-30 -> 2026
    - 2026-12-01 -> 2027
    """
    if not value:
        return None
    d = parse_iso_date(value)
    if not isinstance(d, date):
        return None
    return d.year + 1 if d.month == 12 else d.year


def in_cpd_cycle(entry_date: str | None, cycle_year_end: int) -> bool:
    if not entry_date:
        return False
    try:
        d = datetime.strptime(entry_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    return date(cycle_year_end - 1, 12, 1) <= d <= date(cycle_year_end, 11, 30)


def available_cpd_cycle_years(portfolio: dict[str, Any]) -> list[int]:
    """Return all CPD cycle year-ends represented in the portfolio.

    The JSON portfolio keeps all historical entries. This helper lets the UI
    filter annual CPD views without deleting or splitting old data.
    """
    years: set[int] = set()

    profile = portfolio.get("profile", {})
    if profile.get("registration_cycle_year_end"):
        years.add(int(profile["registration_cycle_year_end"]))

    current_year = date.today().year
    years.add(current_year if date.today() <= date(current_year, 11, 30) else current_year + 1)

    for collection in ("cpd_entries", "peer_entries", "registrar_cpd_entries", "supervision_entries"):
        for entry in portfolio.get(collection, []):
            year_end = cycle_year_end_for_date(entry.get("date"))
            if year_end:
                years.add(year_end)

    return sorted(years, reverse=True)


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
