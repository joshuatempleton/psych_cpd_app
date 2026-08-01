# Version 3.1.0 cloud-first update

Replace these files in the repository root:

- `cloud_sync.py`
- `save_load.py`
- `constants.py`

Keep the existing `cloud_storage.py`, Supabase schema and Streamlit secrets.

## Expected behaviour

- Sign-in is required when Supabase is configured.
- The cloud portfolio loads automatically after sign-in.
- Portfolio changes are detected and saved automatically every two seconds after the app commits them to session state.
- The previous save/load page becomes **Portfolio backup and recovery**.
- JSON is retained only for legacy import, offline backup and recovery.
- A revision conflict still blocks an older device from overwriting a newer cloud revision.

## app.py requirement

The existing call must remain near the beginning of `app.py`, after the default portfolio is initialised:

```python
from cloud_sync import render_cloud_account
from models import normalise_portfolio

render_cloud_account("portfolio", normalise_portfolio)
```

If the application uses a session-state key other than `portfolio`, use that key consistently in both `render_cloud_account()` and `render_save_load()`.

## Deployment

1. Replace the three files.
2. Commit and push to the deployed GitHub branch.
3. Reboot the Streamlit app once.
4. Sign in and confirm the sidebar shows **Saved to cloud**.
5. Add a test CPD entry and wait up to two seconds. The status should return to **Saved to cloud**.
6. Open the app in another browser/device and use **Reload** to confirm the entry is present.
