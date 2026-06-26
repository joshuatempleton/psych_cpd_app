# Psychologist CPD Portfolio Tracker

A local/session-first Streamlit app for tracking CPD, peer consultation, learning goals, registrar supervision, endorsement competencies, deadlines, and audit-style exports.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```

## Privacy

This app does not automatically persist data after a session. The JSON portfolio file is the user's saved record. Keep it safe.


## V2.1 update

Registrar progress is now shown in both the main Dashboard tab and the Endorsement / Registrar tab when registrar tracking is enabled. The shared panel includes practice hours, supervision hours, active CPD hours, halfway progress-report warning, competency summary, and upcoming registrar deadlines.
