from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .persistence import append_jsonl, atomic_write_json

log = logging.getLogger("jarvis.plaid")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_plaid_root() -> Path:
    explicit = str(os.getenv("JARVIS_PLAID_DATA_PATH", "") or "").strip()
    if explicit:
        return Path(explicit).expanduser()
    data_root = str(os.getenv("DATA_PATH", "") or "").strip()
    if data_root:
        return Path(data_root).expanduser() / "plaid"
    app_data = Path("/app/data")
    if app_data.exists():
        return app_data / "plaid"
    return Path.home() / ".jarvis" / "plaid"


class PlaidConnector:
    def __init__(self, config: Any | None = None, finance_store: Any | None = None) -> None:
        self._config = config
        self._finance_store = finance_store
        self._root = _default_plaid_root()
        self._root.mkdir(parents=True, exist_ok=True)
        self._items_path = self._root / "items.json"
        self._sync_meta_path = self._root / "sync_meta.json"

    def status(self) -> dict[str, Any]:
        items = self._load_items()
        meta = self._load_sync_meta()
        configured = self._configured()
        connected_accounts = 0
        if self._finance_store is not None:
            try:
                connected_accounts = len([a for a in self._finance_store.load_accounts() if not getattr(a, "is_manual", True)])
            except Exception:
                connected_accounts = 0
        return {
            "available": True,
            "configured": configured,
            "connected": bool(items),
            "environment": self._env_name(),
            "item_count": len(items),
            "linked_account_count": connected_accounts,
            "last_sync_at": meta.get("last_sync_at"),
            "detail": self._detail_message(configured=configured, items=items, meta=meta),
        }

    def create_link_token(self, *, user_id: str = "chris") -> dict[str, Any]:
        if not self._configured():
            return {"ok": False, "available": True, "detail": "Plaid is not configured yet. Add JARVIS_PLAID_CLIENT_ID and JARVIS_PLAID_SECRET first."}
        payload: dict[str, Any] = {
            "client_name": "Jarvis",
            "language": "en",
            "country_codes": self._country_codes(),
            "products": ["transactions"],
            "user": {"client_user_id": user_id},
            "transactions": {"days_requested": 180},
        }
        webhook = str(self._get("plaid_webhook", "") or os.getenv("JARVIS_PLAID_WEBHOOK_URL", "")).strip()
        if webhook:
            payload["webhook"] = webhook
        data = self._post("/link/token/create", payload)
        token = str(data.get("link_token", "")).strip()
        if not token:
            raise RuntimeError("Plaid did not return a link_token.")
        return {"ok": True, "available": True, "link_token": token, "expiration": data.get("expiration"), "request_id": data.get("request_id")}

    def exchange_public_token(
        self,
        *,
        public_token: str,
        owner_user_id: str = "chris",
        institution_name: str = "",
        institution_id: str = "",
        accounts_metadata: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not public_token.strip():
            raise ValueError("public_token is required")
        if not self._configured():
            return {"ok": False, "available": True, "detail": "Plaid is not configured yet."}
        exchange = self._post("/item/public_token/exchange", {"public_token": public_token})
        access_token = str(exchange.get("access_token", "")).strip()
        item_id = str(exchange.get("item_id", "")).strip()
        if not access_token or not item_id:
            raise RuntimeError("Plaid token exchange did not return an access_token and item_id.")

        item_record = {
            "item_id": item_id,
            "access_token": access_token,
            "owner_user_id": owner_user_id,
            "institution_name": institution_name.strip(),
            "institution_id": institution_id.strip(),
            "accounts_metadata": list(accounts_metadata or []),
            "status": "connected",
            "cursor": None,
            "created_at": _now_iso(),
            "last_sync_at": None,
        }
        self._upsert_item(item_record)
        sync_result = self.sync_item(item_id)
        item_record = self._get_item(item_id) or item_record
        return {
            "ok": True,
            "available": True,
            "item_id": item_id,
            "institution_name": item_record.get("institution_name", ""),
            "imported_accounts": sync_result.get("imported_accounts", 0),
            "imported_transactions": sync_result.get("imported_transactions", 0),
            "request_id": exchange.get("request_id"),
        }

    def sync_all(self) -> dict[str, Any]:
        items = self._load_items()
        imported_accounts = 0
        imported_transactions = 0
        synced_items = 0
        for item in items:
            result = self.sync_item(str(item.get("item_id", "")))
            imported_accounts += int(result.get("imported_accounts", 0))
            imported_transactions += int(result.get("imported_transactions", 0))
            synced_items += 1
        return {
            "ok": True,
            "available": True,
            "synced_items": synced_items,
            "imported_accounts": imported_accounts,
            "imported_transactions": imported_transactions,
            "last_sync_at": self._load_sync_meta().get("last_sync_at"),
        }

    def sync_item(self, item_id: str) -> dict[str, Any]:
        item = self._get_item(item_id)
        if not item:
            raise KeyError(item_id)
        access_token = str(item.get("access_token", "")).strip()
        if not access_token:
            raise RuntimeError("Plaid item is missing an access token.")

        accounts_payload = self._post("/accounts/get", {"access_token": access_token})
        accounts = list(accounts_payload.get("accounts") or [])
        imported_accounts = self._import_accounts(accounts, item=item)

        cursor = item.get("cursor")
        added: list[dict[str, Any]] = []
        modified: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        while True:
            body: dict[str, Any] = {"access_token": access_token, "count": 500}
            if cursor:
                body["cursor"] = cursor
            sync_payload = self._post("/transactions/sync", body)
            added.extend(list(sync_payload.get("added") or []))
            modified.extend(list(sync_payload.get("modified") or []))
            removed.extend(list(sync_payload.get("removed") or []))
            cursor = sync_payload.get("next_cursor") or cursor
            if not sync_payload.get("has_more"):
                break

        imported_transactions = self._import_transactions(
            added=added,
            modified=modified,
            removed=removed,
            item=item,
        )

        item["cursor"] = cursor
        item["status"] = "synced"
        item["last_sync_at"] = _now_iso()
        if accounts and not item.get("institution_name"):
            item["institution_name"] = self._guess_institution_name(item, accounts)
        self._upsert_item(item)
        self._save_sync_meta(
            {
                "last_sync_at": item["last_sync_at"],
                "item_id": item_id,
                "imported_accounts": imported_accounts,
                "imported_transactions": imported_transactions,
            }
        )
        return {
            "ok": True,
            "available": True,
            "item_id": item_id,
            "imported_accounts": imported_accounts,
            "imported_transactions": imported_transactions,
            "last_sync_at": item["last_sync_at"],
        }

    def _import_accounts(self, accounts: list[dict[str, Any]], *, item: dict[str, Any]) -> int:
        if self._finance_store is None:
            return 0
        from .financial_intelligence import Account

        imported = 0
        institution_name = self._guess_institution_name(item, accounts)
        for raw in accounts:
            plaid_account_id = str(raw.get("account_id", "")).strip()
            if not plaid_account_id:
                continue
            subtype = str(raw.get("subtype", "") or "")
            account_type = self._map_account_type(str(raw.get("type", "") or ""), subtype)
            balances = dict(raw.get("balances") or {})
            balance_value = balances.get("current")
            if balance_value is None:
                balance_value = balances.get("available")
            if balance_value is None:
                balance_value = 0.0
            account = Account(
                account_id=f"plaid:{plaid_account_id}",
                name=str(raw.get("official_name") or raw.get("name") or "Linked account").strip(),
                account_type=account_type,
                institution=institution_name,
                balance=float(balance_value or 0.0),
                currency=str(raw.get("iso_currency_code") or balances.get("iso_currency_code") or "USD"),
                last_updated=_now_iso(),
                notes=f"Linked via Plaid Item {item.get('item_id', '')}".strip(),
                is_manual=False,
                hidden=False,
            )
            self._finance_store.upsert_account(account)
            imported += 1
        return imported

    def _import_transactions(
        self,
        *,
        added: list[dict[str, Any]],
        modified: list[dict[str, Any]],
        removed: list[dict[str, Any]],
        item: dict[str, Any],
    ) -> int:
        if self._finance_store is None:
            return 0
        from .financial_intelligence import Transaction

        linked_transactions: list[Transaction] = []
        for raw in [*added, *modified]:
            plaid_txn_id = str(raw.get("transaction_id", "")).strip()
            plaid_account_id = str(raw.get("account_id", "")).strip()
            if not plaid_txn_id or not plaid_account_id:
                continue
            amount = float(raw.get("amount") or 0.0)
            category = self._map_transaction_category(raw)
            note_bits = []
            merchant_name = str(raw.get("merchant_name") or "").strip()
            if merchant_name:
                note_bits.append(f"merchant={merchant_name}")
            pending = raw.get("pending")
            if pending is not None:
                note_bits.append(f"pending={bool(pending)}")
            note_bits.append(f"plaid_item={item.get('item_id', '')}")
            linked_transactions.append(
                Transaction(
                    transaction_id=f"plaid:{plaid_txn_id}",
                    account_id=f"plaid:{plaid_account_id}",
                    date=str(raw.get("date") or "").strip() or _now_iso()[:10],
                    description=str(raw.get("name") or raw.get("merchant_name") or "Plaid transaction").strip(),
                    amount=round(-amount, 2),
                    category=category,
                    subcategory=str(raw.get("personal_finance_category", {}).get("detailed") or "").strip(),
                    notes="; ".join(note_bits),
                    is_passive_income=False,
                    source_agent="plaid",
                )
            )
        self._finance_store.upsert_linked_transactions(linked_transactions)
        removed_ids = [f"plaid:{str(entry.get('transaction_id', '')).strip()}" for entry in removed if str(entry.get("transaction_id", "")).strip()]
        self._finance_store.remove_linked_transactions(removed_ids)
        return len(linked_transactions)

    def _map_account_type(self, plaid_type: str, subtype: str) -> str:
        plaid_type = plaid_type.strip().lower()
        subtype = subtype.strip().lower()
        if plaid_type == "depository":
            if subtype == "checking":
                return "checking"
            if subtype == "savings":
                return "savings"
            return "checking"
        if plaid_type == "investment":
            if subtype in {"401a", "401k", "403b", "457b", "ira", "roth", "simple ira", "sep ira"}:
                return "retirement"
            return "investment"
        if plaid_type == "credit":
            return "credit"
        if plaid_type == "loan":
            return "loan"
        return "other"

    def _map_transaction_category(self, txn: dict[str, Any]) -> str:
        detailed = str((txn.get("personal_finance_category") or {}).get("primary") or "").strip().lower()
        if not detailed:
            raw = list(txn.get("category") or [])
            detailed = str(raw[0] if raw else "").strip().lower()
        mapping = {
            "income": "income",
            "transfer": "transfer",
            "loan_payments": "other",
            "bank_fees": "other",
            "entertainment": "entertainment",
            "food_and_drink": "food",
            "general_merchandise": "other",
            "general_services": "other",
            "government_and_non_profit": "other",
            "home_improvement": "housing",
            "medical": "health",
            "personal_care": "health",
            "rent_and_utilities": "housing",
            "travel": "transport",
            "transportation": "transport",
        }
        for prefix, category in mapping.items():
            if detailed.startswith(prefix):
                return category
        return "other"

    def _detail_message(self, *, configured: bool, items: list[dict[str, Any]], meta: dict[str, Any]) -> str:
        if not configured:
            return "Plaid is not configured yet. Add the Plaid client id and secret to enable live bank connections."
        if not items:
            return "No bank accounts connected yet."
        last_sync = str(meta.get("last_sync_at") or "").strip()
        if last_sync:
            return f"{len(items)} linked financial item(s). Last synced {last_sync}."
        return f"{len(items)} linked financial item(s)."

    def _configured(self) -> bool:
        return bool(self._get("plaid_client_id", "") and self._get("plaid_secret", ""))

    def _env_name(self) -> str:
        env_name = str(self._get("plaid_env", "") or os.getenv("JARVIS_PLAID_ENV", "sandbox")).strip().lower()
        return env_name if env_name in {"sandbox", "development", "production"} else "sandbox"

    def _country_codes(self) -> list[str]:
        raw = str(self._get("plaid_country_codes", "") or os.getenv("JARVIS_PLAID_COUNTRY_CODES", "US")).strip()
        parts = [part.strip().upper() for part in raw.split(",") if part.strip()]
        return parts or ["US"]

    def _base_url(self) -> str:
        env_name = self._env_name()
        if env_name == "production":
            return "https://production.plaid.com"
        if env_name == "development":
            return "https://development.plaid.com"
        return "https://sandbox.plaid.com"

    def _headers(self) -> dict[str, str]:
        return {
            "PLAID-CLIENT-ID": str(self._get("plaid_client_id", "")).strip(),
            "PLAID-SECRET": str(self._get("plaid_secret", "")).strip(),
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{self._base_url()}{path}", headers=self._headers(), json=payload)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected Plaid response for {path}.")
        return data

    def _load_items(self) -> list[dict[str, Any]]:
        return self._load_list(self._items_path)

    def _get_item(self, item_id: str) -> dict[str, Any] | None:
        for item in self._load_items():
            if str(item.get("item_id", "")).strip() == item_id:
                return dict(item)
        return None

    def _upsert_item(self, item_record: dict[str, Any]) -> None:
        items = self._load_items()
        next_items: list[dict[str, Any]] = []
        replaced = False
        item_id = str(item_record.get("item_id", "")).strip()
        for item in items:
            if str(item.get("item_id", "")).strip() == item_id:
                next_items.append(dict(item_record))
                replaced = True
            else:
                next_items.append(dict(item))
        if not replaced:
            next_items.append(dict(item_record))
        self._save_list(self._items_path, next_items)

    def _load_sync_meta(self) -> dict[str, Any]:
        if not self._sync_meta_path.exists():
            return {}
        try:
            payload = json.loads(self._sync_meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save_sync_meta(self, payload: dict[str, Any]) -> None:
        self._sync_meta_path.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(
            self._sync_meta_path.with_name(f"{self._sync_meta_path.stem}_log.jsonl"),
            {"saved_at": _now_iso(), "record": payload},
        )
        atomic_write_json(self._sync_meta_path, payload)

    def _load_list(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return [dict(item) for item in payload] if isinstance(payload, list) else []

    def _save_list(self, path: Path, payload: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(
            path.with_name(f"{path.stem}_log.jsonl"),
            {"saved_at": _now_iso(), "records": payload},
        )
        atomic_write_json(path, payload)

    def _guess_institution_name(self, item: dict[str, Any], accounts: list[dict[str, Any]]) -> str:
        name = str(item.get("institution_name", "") or "").strip()
        if name:
            return name
        account_names = [str(entry.get("official_name") or entry.get("name") or "").strip() for entry in accounts]
        return next((entry for entry in account_names if entry), "Linked financial institution")

    def _get(self, name: str, default: Any = "") -> Any:
        if self._config is None:
            return default
        return getattr(self._config, name, default)
