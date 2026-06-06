"""
epic_fhir.py — Epic FHIR R4 Integration
=========================================
Implements SMART on FHIR OAuth 2.0 PKCE for patient-facing Epic access.

Setup:
    1. Register at https://fhir.epic.com/Developer/Apps
    2. Set redirect URI to: http://127.0.0.1:8787/api/epic/auth/callback
    3. Save client_id to ~/.jarvis/health/epic_config.json

Config schema (~/.jarvis/health/epic_config.json):
    {
      "client_id": "your-client-id",
      "fhir_base": "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
      "auth_url":  "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize",
      "token_url": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
      "redirect_uri": "http://127.0.0.1:8787/api/epic/auth/callback",
      "scopes": "openid fhirUser patient/Patient.read patient/Observation.read patient/Condition.read patient/MedicationRequest.read patient/Appointment.read patient/AllergyIntolerance.read patient/Immunization.read patient/DiagnosticReport.read"
    }
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

from .persistence import append_jsonl, atomic_write_json

_HEALTH_DIR   = Path.home() / ".jarvis" / "health"
_CONFIG_PATH  = _HEALTH_DIR / "epic_config.json"
_TOKEN_PATH   = _HEALTH_DIR / "epic_token.json"
_STATE_PATH   = _HEALTH_DIR / "epic_pkce_state.json"  # temp during auth flow
_CONFIG_LOG_PATH = _HEALTH_DIR / "epic_config_log.jsonl"
_TOKEN_LOG_PATH = _HEALTH_DIR / "epic_token_log.jsonl"
_STATE_LOG_PATH = _HEALTH_DIR / "epic_pkce_state_log.jsonl"
_CONFIG_STATE_LOG_PATH = _HEALTH_DIR / "epic_config_state_log.jsonl"
_TOKEN_STATE_LOG_PATH = _HEALTH_DIR / "epic_token_state_log.jsonl"
_STATE_STATE_LOG_PATH = _HEALTH_DIR / "epic_pkce_state_state_log.jsonl"
_lock = threading.Lock()

DEFAULT_CONFIG = {
    "client_id":    "",
    "fhir_base":    "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
    "auth_url":     "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize",
    "token_url":    "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
    "redirect_uri": "http://127.0.0.1:8787/api/epic/auth/callback",
    "scopes": (
        "openid fhirUser "
        "patient/Patient.read "
        "patient/Observation.read "
        "patient/Condition.read "
        "patient/MedicationRequest.read "
        "patient/Appointment.read "
        "patient/AllergyIntolerance.read "
        "patient/Immunization.read "
        "patient/DiagnosticReport.read"
    ),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Config + token helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if _CONFIG_PATH.exists():
            stored = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **stored}
    except Exception:
        replayed = _load_config_from_state_log()
        if replayed:
            return {**DEFAULT_CONFIG, **replayed}
        return {**DEFAULT_CONFIG, **_load_config_from_log()}
    if not _CONFIG_PATH.exists():
        replayed = _load_config_from_state_log()
        if replayed:
            return {**DEFAULT_CONFIG, **replayed}
        return {**DEFAULT_CONFIG, **_load_config_from_log()}
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(_CONFIG_PATH, cfg)
    append_jsonl(_CONFIG_LOG_PATH, {"saved_at": _now_iso(), "config": cfg})
    append_jsonl(_CONFIG_STATE_LOG_PATH, {"saved_at": _now_iso(), "config": cfg})


def _load_config_from_log() -> dict:
    try:
        if _CONFIG_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _CONFIG_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                config = payload.get("config")
                if isinstance(config, dict):
                    latest = dict(config)
            return latest or {}
    except Exception:
        pass
    return {}


def _load_config_from_state_log() -> dict:
    try:
        if _CONFIG_STATE_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _CONFIG_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                config = payload.get("config")
                if isinstance(config, dict):
                    latest = dict(config)
            return latest or {}
    except Exception:
        pass
    return {}


def _load_token() -> dict | None:
    try:
        if _TOKEN_PATH.exists():
            return json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        replayed = _load_token_from_state_log()
        if replayed is not None:
            return replayed
        return _load_token_from_log()
    if not _TOKEN_PATH.exists():
        replayed = _load_token_from_state_log()
        if replayed is not None:
            return replayed
        return _load_token_from_log()
    return None


def _save_token(token: dict) -> None:
    atomic_write_json(_TOKEN_PATH, token)
    append_jsonl(_TOKEN_LOG_PATH, {"saved_at": _now_iso(), "token": token})
    append_jsonl(_TOKEN_STATE_LOG_PATH, {"saved_at": _now_iso(), "token": token})
    _TOKEN_PATH.chmod(0o600)  # owner-only


def _load_token_from_log() -> dict | None:
    try:
        if _TOKEN_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _TOKEN_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                token = payload.get("token")
                if isinstance(token, dict):
                    latest = dict(token)
            return latest
    except Exception:
        pass
    return None


def _load_token_from_state_log() -> dict | None:
    try:
        if _TOKEN_STATE_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _TOKEN_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                token = payload.get("token")
                if isinstance(token, dict):
                    latest = dict(token)
            return latest
    except Exception:
        pass
    return None


def is_connected() -> bool:
    token = _load_token()
    return bool(token and token.get("access_token"))


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def _pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge)."""
    verifier  = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest    = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------

def start_auth() -> str:
    """
    Generate the Epic authorization URL. Stores PKCE state for callback.
    Returns the URL to redirect the user to.
    """
    cfg = load_config()
    if not cfg.get("client_id"):
        raise ValueError("Epic client_id not configured. Visit https://fhir.epic.com/Developer/Apps")
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)
    # Store verifier + state for callback validation
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    state_payload = {"verifier": verifier, "state": state}
    atomic_write_json(_STATE_PATH, state_payload)
    append_jsonl(_STATE_LOG_PATH, {"saved_at": _now_iso(), "state_payload": state_payload})
    append_jsonl(_STATE_STATE_LOG_PATH, {"saved_at": _now_iso(), "state_payload": state_payload})
    params = {
        "response_type": "code",
        "client_id":     cfg["client_id"],
        "redirect_uri":  cfg["redirect_uri"],
        "scope":         cfg["scopes"],
        "state":         state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "aud": cfg["fhir_base"],
    }
    return cfg["auth_url"] + "?" + urlencode(params)


def handle_callback(code: str, state: str) -> dict:
    """
    Exchange auth code for tokens. Called by the JARVIS callback endpoint.
    Returns {"ok": True, "patient_id": "..."} or {"ok": False, "error": "..."}.
    """
    cfg = load_config()
    try:
        if _STATE_PATH.exists():
            stored = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        else:
            stored = _load_state_from_state_log()
            if not stored:
                stored = _load_state_from_log()
    except Exception:
        stored = _load_state_from_state_log()
        if not stored:
            stored = _load_state_from_log()
    if not stored:
        return {"ok": False, "error": "No pending auth state. Start auth again."}
    if stored.get("state") != state:
        return {"ok": False, "error": "State mismatch — possible CSRF."}
    verifier = stored["verifier"]
    try:
        resp = httpx.post(cfg["token_url"], data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  cfg["redirect_uri"],
            "client_id":     cfg["client_id"],
            "code_verifier": verifier,
        }, timeout=15)
        resp.raise_for_status()
        token = resp.json()
        token["stored_at"] = time.time()
        _save_token(token)
        _STATE_PATH.unlink(missing_ok=True)
        return {"ok": True, "patient_id": token.get("patient", ""), "scope": token.get("scope", "")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def _load_state_from_log() -> dict | None:
    try:
        if _STATE_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                state_payload = payload.get("state_payload")
                if isinstance(state_payload, dict):
                    latest = dict(state_payload)
            return latest
    except Exception:
        pass
    return None


def _load_state_from_state_log() -> dict | None:
    try:
        if _STATE_STATE_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _STATE_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                state_payload = payload.get("state_payload")
                if isinstance(state_payload, dict):
                    latest = dict(state_payload)
            return latest
    except Exception:
        pass
    return None


def _get_access_token() -> str | None:
    """Return a valid access token, refreshing if needed."""
    token = _load_token()
    if not token:
        return None
    # Check expiry (Epic tokens typically expire in 3600s)
    stored_at  = token.get("stored_at", 0)
    expires_in = token.get("expires_in", 3600)
    if time.time() > stored_at + expires_in - 60:
        # Try refresh
        refresh = token.get("refresh_token")
        if refresh:
            cfg = load_config()
            try:
                r = httpx.post(cfg["token_url"], data={
                    "grant_type":    "refresh_token",
                    "refresh_token": refresh,
                    "client_id":     cfg["client_id"],
                }, timeout=15)
                r.raise_for_status()
                new_token = r.json()
                new_token["stored_at"] = time.time()
                _save_token(new_token)
                return new_token.get("access_token")
            except Exception:
                return None
        return None
    return token.get("access_token")


# ---------------------------------------------------------------------------
# FHIR resource fetchers
# ---------------------------------------------------------------------------

class EpicFHIRClient:
    def __init__(self):
        cfg = load_config()
        self._base = cfg["fhir_base"].rstrip("/")
        self._patient_id: str | None = None

    def _headers(self) -> dict:
        token = _get_access_token()
        if not token:
            raise PermissionError("Not authenticated. Please connect Epic first.")
        return {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}

    def _patient(self) -> str:
        if self._patient_id:
            return self._patient_id
        t = _load_token()
        self._patient_id = (t or {}).get("patient", "")
        return self._patient_id

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self._base}/{path.lstrip('/')}"
        r = httpx.get(url, headers=self._headers(), params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def _entries(self, bundle: dict) -> list[dict]:
        return [e.get("resource", {}) for e in bundle.get("entry", [])]

    def get_patient(self) -> dict:
        pid = self._patient()
        if not pid:
            return {}
        res = self._get(f"Patient/{pid}")
        name_parts = res.get("name", [{}])[0]
        given  = " ".join(name_parts.get("given", []))
        family = name_parts.get("family", "")
        dob    = res.get("birthDate", "")
        gender = res.get("gender", "")
        return {"id": pid, "name": f"{given} {family}".strip(), "dob": dob, "gender": gender, "raw": res}

    def get_observations(self, category: str = "laboratory", count: int = 50) -> list[dict]:
        """category: 'laboratory' | 'vital-signs' | 'social-history'"""
        bundle = self._get("Observation", params={
            "patient":  self._patient(),
            "category": category,
            "_count":   count,
            "_sort":    "-date",
        })
        results = []
        for obs in self._entries(bundle):
            code    = (obs.get("code", {}).get("coding", [{}])[0]).get("display", obs.get("code", {}).get("text", ""))
            val     = obs.get("valueQuantity", {})
            val_str = f"{val.get('value', '')} {val.get('unit', '')}".strip() if val else (
                obs.get("valueString", "") or obs.get("valueCodeableConcept", {}).get("text", "")
            )
            date   = obs.get("effectiveDateTime", obs.get("issued", ""))[:10] if (obs.get("effectiveDateTime") or obs.get("issued")) else ""
            status = obs.get("status", "")
            if code:
                results.append({"code": code, "value": val_str, "date": date, "status": status})
        return results

    def get_conditions(self) -> list[dict]:
        bundle = self._get("Condition", params={"patient": self._patient(), "clinical-status": "active", "_count": 50})
        results = []
        for c in self._entries(bundle):
            name  = c.get("code", {}).get("text", c.get("code", {}).get("coding", [{}])[0].get("display", "Unknown"))
            onset = c.get("onsetDateTime", c.get("recordedDate", ""))[:10] if (c.get("onsetDateTime") or c.get("recordedDate")) else ""
            results.append({"condition": name, "onset": onset, "status": c.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")})
        return results

    def get_medications(self) -> list[dict]:
        bundle = self._get("MedicationRequest", params={"patient": self._patient(), "status": "active", "_count": 50})
        results = []
        for m in self._entries(bundle):
            name   = m.get("medicationCodeableConcept", {}).get("text", m.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "Unknown"))
            dosage = (m.get("dosageInstruction", [{}])[0]).get("text", "") if m.get("dosageInstruction") else ""
            results.append({"medication": name, "dosage": dosage, "status": m.get("status", "")})
        return results

    def get_appointments(self, count: int = 10) -> list[dict]:
        bundle = self._get("Appointment", params={"patient": self._patient(), "status": "booked,pending", "_count": count, "_sort": "date"})
        results = []
        for a in self._entries(bundle):
            desc  = a.get("description", a.get("serviceType", [{}])[0].get("text", "Appointment") if a.get("serviceType") else "Appointment")
            start = a.get("start", "")[:16].replace("T", " ") if a.get("start") else ""
            loc   = (a.get("participant", [{}])[0]).get("actor", {}).get("display", "") if a.get("participant") else ""
            results.append({"description": desc, "start": start, "location": loc, "status": a.get("status", "")})
        return results

    def get_allergies(self) -> list[dict]:
        bundle = self._get("AllergyIntolerance", params={"patient": self._patient(), "_count": 30})
        results = []
        for a in self._entries(bundle):
            substance = a.get("code", {}).get("text", a.get("code", {}).get("coding", [{}])[0].get("display", "Unknown"))
            severity  = a.get("reaction", [{}])[0].get("severity", "") if a.get("reaction") else ""
            results.append({"substance": substance, "severity": severity, "status": a.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")})
        return results

    def get_immunizations(self) -> list[dict]:
        bundle = self._get("Immunization", params={"patient": self._patient(), "_count": 30, "_sort": "-date"})
        results = []
        for i in self._entries(bundle):
            name = i.get("vaccineCode", {}).get("text", i.get("vaccineCode", {}).get("coding", [{}])[0].get("display", "Unknown"))
            date = i.get("occurrenceDateTime", "")[:10] if i.get("occurrenceDateTime") else ""
            results.append({"vaccine": name, "date": date, "status": i.get("status", "")})
        return results
