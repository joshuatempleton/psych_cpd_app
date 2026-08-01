from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests


class CloudStorageError(RuntimeError):
    """Raised when authentication or cloud persistence fails."""


class CloudConflictError(CloudStorageError):
    """Raised when another device has saved a newer portfolio revision."""


@dataclass(frozen=True)
class AuthSession:
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    expires_in: int


@dataclass(frozen=True)
class SignUpResult:
    session: AuthSession | None
    confirmation_required: bool
    email: str


@dataclass(frozen=True)
class CloudPortfolio:
    portfolio: dict[str, Any]
    revision: int
    updated_at: str | None


class SupabasePortfolioStore:
    """Small Supabase REST client for one cloud portfolio per user.

    The application continues to work with its existing in-memory portfolio
    dictionary. Supabase stores that dictionary in a JSONB column. This keeps
    all current application features intact while providing cross-device
    persistence and retaining JSON import/export as backup functionality.
    """

    def __init__(self, url: str, anon_key: str, timeout_seconds: int = 20) -> None:
        self.url = url.rstrip("/")
        self.anon_key = anon_key.strip()
        self.timeout_seconds = timeout_seconds
        if not self.url.startswith("https://"):
            raise ValueError("Supabase URL must use HTTPS.")
        if not self.anon_key:
            raise ValueError("Supabase anonymous key is required.")

    @property
    def configured(self) -> bool:
        return bool(self.url and self.anon_key)

    def sign_up(self, email: str, password: str) -> SignUpResult:
        normalised_email = email.strip().lower()
        response = requests.post(
            f"{self.url}/auth/v1/signup",
            headers=self._public_headers(),
            json={"email": normalised_email, "password": password},
            timeout=self.timeout_seconds,
        )
        data = self._json_or_error(response)

        # Supabase returns no access token when email confirmation is enabled.
        # A user object may still be returned, including for privacy-preserving
        # duplicate-signup responses, so the UI must present a neutral message.
        if not data.get("access_token"):
            return SignUpResult(
                session=None,
                confirmation_required=True,
                email=normalised_email,
            )

        return SignUpResult(
            session=self._auth_session_from_response(data, fallback_email=normalised_email),
            confirmation_required=False,
            email=normalised_email,
        )

    def sign_in(self, email: str, password: str) -> AuthSession:
        response = requests.post(
            f"{self.url}/auth/v1/token?grant_type=password",
            headers=self._public_headers(),
            json={"email": email.strip(), "password": password},
            timeout=self.timeout_seconds,
        )
        data = self._json_or_error(response)
        return self._auth_session_from_response(data, fallback_email=email)

    def refresh_session(self, refresh_token: str) -> AuthSession:
        response = requests.post(
            f"{self.url}/auth/v1/token?grant_type=refresh_token",
            headers=self._public_headers(),
            json={"refresh_token": refresh_token},
            timeout=self.timeout_seconds,
        )
        data = self._json_or_error(response)
        return self._auth_session_from_response(data)

    def load_portfolio(self, access_token: str) -> CloudPortfolio | None:
        response = requests.get(
            f"{self.url}/rest/v1/portfolios",
            headers=self._user_headers(access_token, prefer=None),
            params={"select": "portfolio,revision,updated_at", "limit": "1"},
            timeout=self.timeout_seconds,
        )
        data = self._json_or_error(response)
        if not data:
            return None
        row = data[0]
        portfolio = row.get("portfolio")
        if not isinstance(portfolio, dict):
            raise CloudStorageError("The cloud portfolio record is not valid JSON data.")
        return CloudPortfolio(
            portfolio=portfolio,
            revision=int(row.get("revision", 0)),
            updated_at=row.get("updated_at"),
        )

    def create_portfolio(self, access_token: str, portfolio: dict[str, Any]) -> CloudPortfolio:
        payload = copy.deepcopy(portfolio)
        self._stamp_saved_metadata(payload, revision=1)
        response = requests.post(
            f"{self.url}/rest/v1/portfolios",
            headers=self._user_headers(access_token, prefer="return=representation"),
            json={"portfolio": payload, "revision": 1},
            timeout=self.timeout_seconds,
        )
        data = self._json_or_error(response)
        row = data[0]
        return CloudPortfolio(row["portfolio"], int(row["revision"]), row.get("updated_at"))

    def save_portfolio(
        self,
        access_token: str,
        portfolio: dict[str, Any],
        expected_revision: int,
    ) -> CloudPortfolio:
        """Save with optimistic concurrency control.

        A revision match prevents a stale browser session from silently
        overwriting changes made on another device.
        """
        new_revision = expected_revision + 1
        payload = copy.deepcopy(portfolio)
        self._stamp_saved_metadata(payload, revision=new_revision)
        response = requests.patch(
            f"{self.url}/rest/v1/portfolios",
            headers=self._user_headers(access_token, prefer="return=representation"),
            params={"revision": f"eq.{expected_revision}"},
            json={"portfolio": payload, "revision": new_revision},
            timeout=self.timeout_seconds,
        )
        data = self._json_or_error(response)
        if not data:
            raise CloudConflictError(
                "This portfolio was updated by another session. Reload the cloud copy before saving again."
            )
        row = data[0]
        return CloudPortfolio(row["portfolio"], int(row["revision"]), row.get("updated_at"))

    @staticmethod
    def portfolio_hash(portfolio: dict[str, Any]) -> str:
        stable = json.dumps(portfolio, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(stable.encode("utf-8")).hexdigest()

    def _public_headers(self) -> dict[str, str]:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {self.anon_key}",
            "Content-Type": "application/json",
        }

    def _user_headers(self, access_token: str, prefer: str | None) -> dict[str, str]:
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    @staticmethod
    def _stamp_saved_metadata(portfolio: dict[str, Any], revision: int) -> None:
        meta = portfolio.setdefault("meta", {})
        meta["last_saved_at"] = datetime.now(timezone.utc).isoformat()
        meta["cloud_revision"] = revision
        meta["storage_mode"] = "supabase_jsonb"

    @staticmethod
    def _json_or_error(response: requests.Response) -> Any:
        try:
            data = response.json()
        except ValueError as exc:
            raise CloudStorageError(
                f"Cloud service returned an invalid response ({response.status_code})."
            ) from exc
        if not response.ok:
            message = data.get("msg") or data.get("message") or data.get("error_description") or data.get("error")
            raise CloudStorageError(str(message or f"Cloud request failed ({response.status_code})."))
        return data

    @staticmethod
    def _auth_session_from_response(data: dict[str, Any], fallback_email: str = "") -> AuthSession:
        user = data.get("user") or {}
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        user_id = user.get("id")
        if not access_token or not refresh_token or not user_id:
            raise CloudStorageError("Authentication succeeded but the returned session was incomplete.")
        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id,
            email=user.get("email") or fallback_email,
            expires_in=int(data.get("expires_in", 3600)),
        )
