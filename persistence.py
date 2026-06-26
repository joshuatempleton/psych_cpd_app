from __future__ import annotations
import json
from copy import deepcopy
from datetime import datetime
from typing import Any
from models import normalise_portfolio

def portfolio_json_bytes(portfolio: dict[str, Any]) -> bytes:
    payload = deepcopy(portfolio)
    payload["meta"]["last_saved_at"] = datetime.now().isoformat()
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

def load_portfolio_from_bytes(raw: bytes) -> dict[str, Any]:
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Uploaded file is not a valid portfolio JSON object.")
    required = {"meta", "profile", "learning_goals", "cpd_entries", "peer_entries"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Uploaded file is missing required keys: {', '.join(sorted(missing))}")
    return normalise_portfolio(data)
