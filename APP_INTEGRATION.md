# Version 3.0 integration

## Files changed or added

- `constants.py`: set `APP_VERSION = "3.0.0"`. Preserve the remainder of the existing constants file.
- `cloud_storage.py`: Supabase authentication and persistence client.
- `cloud_sync.py`: Streamlit account controls, initial cloud load, save, reload and conflict handling.
- `supabase_schema.sql`: database table, triggers, grants and Row Level Security policies.
- `requirements-cloud.txt`: dependency to merge into `requirements.txt`.
- `secrets.toml.example`: required Streamlit secrets structure.

## Why the first cloud release uses JSONB

The current application already treats one portfolio dictionary as the source of truth. Storing that portfolio in one protected JSONB row provides cross-device persistence without rewriting CPD, peer consultation, registrar, competency, calculations and export modules in the same release. Existing JSON files remain valid imports and backups.

This is an intentionally staged architecture. Individual tables can be introduced later for analytics and supervisor workflows.

## app.py integration

After the application creates or normalises `st.session_state["portfolio"]`, add:

```python
from cloud_sync import render_cloud_account
from models import normalise_portfolio

render_cloud_account("portfolio", normalise_portfolio)
```

Use the actual session-state key if the current project uses a different name.

## Saving changes

Version 3.0 provides an explicit **Save portfolio to cloud** control. This matches the existing explicit-save privacy philosophy and prevents a partially completed form from being persisted unexpectedly.

To save immediately after a successful create, edit or delete operation, add this after the portfolio mutation and before `st.rerun()`:

```python
from cloud_sync import save_cloud_portfolio

save_cloud_portfolio("portfolio", silent_when_unchanged=True)
```

This can be added progressively to `cpd.py`, `peer.py`, `registrar.py`, `learning_plan.py` and other edit workflows. The explicit sidebar save remains available throughout the transition.

## Supabase setup

1. Create a Supabase project in an Australian region where available.
2. Open SQL Editor and run `supabase_schema.sql`.
3. In Authentication settings, enable Email authentication.
4. Add the Supabase URL and anonymous key to Streamlit Community Cloud under **App settings → Secrets** using the structure in `secrets.toml.example`.
5. Add `requests>=2.32,<3` to the existing `requirements.txt`.
6. Commit and push the changed files.
7. Reboot the Streamlit app once after changing dependencies or secrets.

## Existing JSON portfolios

The existing JSON import remains unchanged. Recommended first-use process:

1. Sign in to the cloud-enabled application.
2. If the cloud account is empty, the currently loaded/default portfolio becomes the initial cloud record.
3. To migrate an existing portfolio, use the existing JSON load function.
4. Select **Save portfolio to cloud**.
5. Reconcile CPD, peer, practice, client-contact, supervision and active-CPD totals.
6. Retain the original JSON file as an offline backup.

## Conflict protection

Each save increments a revision number. If another device has already saved a newer revision, the stale session is prevented from overwriting it. Reload the cloud portfolio, reconcile any changes, then save again.

## Security boundaries

- The anonymous key is safe to place in Streamlit secrets only when Row Level Security remains enabled.
- Never place the Supabase service-role key in Streamlit or client-facing code.
- Each user can access only the row whose `user_id` matches their authenticated Supabase identity.
- Evidence attachments are not migrated in this release. Existing evidence references remain in the portfolio. Private object storage should be the next migration stage.
