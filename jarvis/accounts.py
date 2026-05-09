from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .models import HouseholdProfile


ACCOUNTS_PATH = Path.cwd() / "data" / "settings" / "accounts.json"
SUPPORTED_PROVIDERS = ("google", "outlook", "imap", "other")
SUPPORTED_SERVICES = ("mail", "calendar", "mail_calendar")


@dataclass(slots=True)
class PersonalAccount:
    account_id: str
    owner_user_id: str
    owner_display_name: str
    provider: str
    service_scope: str
    label: str
    login_hint: str
    status: str
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class AccountRegistry:
    def __init__(self, household: HouseholdProfile, path: Path = ACCOUNTS_PATH) -> None:
        self.household = household
        self.path = path

    def list_accounts(self) -> list[PersonalAccount]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        accounts: list[PersonalAccount] = []
        for item in payload if isinstance(payload, list) else []:
            try:
                accounts.append(self._coerce(item))
            except Exception:
                continue
        return accounts

    def describe(self) -> dict:
        return {
            "accounts": [item.to_dict() for item in self.list_accounts()],
            "owners": [
                {
                    "id": user.user_id,
                    "label": user.display_name,
                }
                for user in self.household.users.values()
            ],
            "providers": [
                {"id": item, "label": item.replace("_", " ").title()}
                for item in SUPPORTED_PROVIDERS
            ],
            "services": [
                {"id": item, "label": item.replace("_", " / ").replace("mail", "Mail").replace("calendar", "Calendar")}
                for item in SUPPORTED_SERVICES
            ],
        }

    def save_account(self, payload: dict) -> PersonalAccount:
        existing = self.list_accounts()
        account_id = str(payload.get("account_id", "")).strip() or str(uuid.uuid4())
        updated = self._coerce({**payload, "account_id": account_id})
        next_accounts: list[PersonalAccount] = []
        replaced = False
        for item in existing:
            if item.account_id == account_id:
                next_accounts.append(updated)
                replaced = True
            else:
                next_accounts.append(item)
        if not replaced:
            next_accounts.append(updated)
        self._save(next_accounts)
        return updated

    def update_status(self, account_id: str, status: str, notes: str = "") -> PersonalAccount | None:
        accounts = self.list_accounts()
        target: PersonalAccount | None = None
        for item in accounts:
            if item.account_id == account_id:
                item.status = status
                if notes:
                    item.notes = notes
                target = item
                break
        if not target:
            return None
        self._save(accounts)
        return target

    def get(self, account_id: str) -> PersonalAccount | None:
        for item in self.list_accounts():
            if item.account_id == account_id:
                return item
        return None

    def _save(self, accounts: list[PersonalAccount]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([item.to_dict() for item in accounts], indent=2) + "\n",
            encoding="utf-8",
        )

    def _coerce(self, payload: dict) -> PersonalAccount:
        owner_user_id = str(payload.get("owner_user_id", "")).strip().lower()
        if owner_user_id not in self.household.users:
            raise ValueError("Unknown owner user id")
        owner = self.household.users[owner_user_id]
        provider = str(payload.get("provider", "google")).strip().lower()
        if provider not in SUPPORTED_PROVIDERS:
            provider = "other"
        service_scope = str(payload.get("service_scope", "mail_calendar")).strip().lower()
        if service_scope not in SUPPORTED_SERVICES:
            service_scope = "mail_calendar"
        label = str(payload.get("label", "")).strip() or f"{owner.display_name} {provider.title()}"
        login_hint = str(payload.get("login_hint", "")).strip()
        status = str(payload.get("status", "planned")).strip().lower() or "planned"
        notes = str(payload.get("notes", "")).strip()
        return PersonalAccount(
            account_id=str(payload.get("account_id", "")).strip() or str(uuid.uuid4()),
            owner_user_id=owner.user_id,
            owner_display_name=owner.display_name,
            provider=provider,
            service_scope=service_scope,
            label=label,
            login_hint=login_hint,
            status=status,
            notes=notes,
        )
