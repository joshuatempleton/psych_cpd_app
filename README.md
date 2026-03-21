# Psychologist CPD Portfolio Tracker

A local-only Streamlit web app for tracking Psychology Board CPD requirements.

## Features
- Session-only privacy design (no database, no server-side persistence)
- Save and load a single JSON portfolio file
- Dashboard for:
  - total CPD hours
  - general CPD hours
  - peer consultation hours
  - endorsement tracking
- Learning plan tab with unlimited goals (3 preloaded)
- General CPD log with reflection and evidence fields
- Peer consultation log with own-practice hours and reflection
- Export to:
  - Word (.docx)
  - PDF (.pdf)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate  # Windows

pip install -r requirements.txt
streamlit run app.py
```

## Privacy note
This app does not store information after the app closes.
Users must download and keep their JSON portfolio file safe, as that file is their ongoing record.
