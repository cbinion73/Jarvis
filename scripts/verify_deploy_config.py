#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


EXPECTED_DB_USER = "your-jarvis-db-user-here"
EXPECTED_DB_PASSWORD = "your-jarvis-db-password-here"
EXPOSED_PASSWORD = "JarvisFamily2026!"
REQUIRED_DB_INTERPOLATION = "${DB_USER:?DB_USER is required}:${DB_PASSWORD:?DB_PASSWORD is required}"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required file: {path.relative_to(path.parents[1])}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"invalid YAML structure in {path.name}")
    return data


def _env_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(k): "" if v is None else str(v) for k, v in value.items()}


def _failure(messages: list[str]) -> int:
    for message in messages:
        print(f"ERROR: {message}")
    return 1


def _check_chronicle(compose: dict[str, Any], messages: list[str]) -> None:
    services = compose.get("services")
    if not isinstance(services, dict):
        messages.append("deploy/docker-compose.yml is missing services")
        return

    chronicle = services.get("chronicle")
    if not isinstance(chronicle, dict):
        messages.append("deploy/docker-compose.yml is missing the chronicle service")
        return

    build = chronicle.get("build")
    environment = _env_map(chronicle.get("environment"))
    database_url = environment.get("CHRONICLE_DATABASE_URL", "")

    if REQUIRED_DB_INTERPOLATION not in database_url:
        messages.append(
            "CHRONICLE_DATABASE_URL must use required DB_USER and DB_PASSWORD interpolation"
        )
    if "postgresql://jarvis:" in database_url or EXPOSED_PASSWORD in database_url:
        messages.append("CHRONICLE_DATABASE_URL still contains a literal credential")
    if "@postgres:5432/chronicle" not in database_url or "postgresql://" not in database_url:
        messages.append("CHRONICLE_DATABASE_URL topology is not preserved")

    expected_chronicle = {
        "build": {"context": "../../chronicle", "dockerfile": "Dockerfile"},
        "restart": "unless-stopped",
        "env_file": ".env",
        "volumes": ["chronicle_snapshots:/app/chronicle-data"],
        "depends_on": {"postgres": {"condition": "service_healthy"}},
        "networks": ["internal"],
    }

    if not isinstance(build, dict) or build.get("context") != expected_chronicle["build"]["context"]:
        messages.append("chronicle build context changed")
    elif build.get("dockerfile") != expected_chronicle["build"]["dockerfile"]:
        messages.append("chronicle build dockerfile changed")
    if chronicle.get("restart") != expected_chronicle["restart"]:
        messages.append("chronicle restart policy changed")
    if chronicle.get("env_file") != expected_chronicle["env_file"]:
        messages.append("chronicle env_file changed")
    if chronicle.get("volumes") != expected_chronicle["volumes"]:
        messages.append("chronicle volumes changed")
    if chronicle.get("depends_on") != expected_chronicle["depends_on"]:
        messages.append("chronicle dependencies changed")
    if chronicle.get("networks") != expected_chronicle["networks"]:
        messages.append("chronicle networks changed")

    postgres = services.get("postgres")
    if not isinstance(postgres, dict):
        messages.append("deploy/docker-compose.yml is missing the postgres service")
        return
    postgres_env = _env_map(postgres.get("environment"))
    if postgres_env.get("POSTGRES_USER") != "${DB_USER:?DB_USER is required}":
        messages.append("postgres POSTGRES_USER must fail closed on DB_USER")
    if postgres_env.get("POSTGRES_PASSWORD") != "${DB_PASSWORD:?DB_PASSWORD is required}":
        messages.append("postgres POSTGRES_PASSWORD must fail closed on DB_PASSWORD")
    if postgres_env.get("POSTGRES_DB") != "ghostwritr":
        messages.append("postgres POSTGRES_DB changed")

    healthcheck = postgres.get("healthcheck")
    if not isinstance(healthcheck, dict):
        messages.append("postgres healthcheck changed")
    else:
        test = healthcheck.get("test")
        if test != ["CMD-SHELL", "pg_isready -U ${DB_USER:?DB_USER is required}"]:
            messages.append("postgres healthcheck must use required DB_USER interpolation")


def _check_shared_db_urls(compose: dict[str, Any], messages: list[str]) -> None:
    services = compose.get("services")
    if not isinstance(services, dict):
        return
    for service_name in ("jarvis",):
        service = services.get(service_name)
        if not isinstance(service, dict):
            continue
        env = _env_map(service.get("environment"))
        for key in ("CATALYST_DB_URL", "JARVIS_HOME_DB_URL"):
            value = env.get(key, "")
            if "${DB_USER:?DB_USER is required}" not in value or "${DB_PASSWORD:?DB_PASSWORD is required}" not in value:
                messages.append(f"{service_name} {key} must fail closed on DB_USER and DB_PASSWORD")


def _check_example(example_path: Path, messages: list[str]) -> None:
    values: dict[str, str] = {}
    for line in example_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()

    if values.get("DB_USER") != EXPECTED_DB_USER:
        messages.append(".env.example DB_USER must use a non-secret placeholder")
    if values.get("DB_PASSWORD") != EXPECTED_DB_PASSWORD:
        messages.append(".env.example DB_PASSWORD must use a non-secret placeholder")
    if values.get("DB_PASSWORD") == EXPOSED_PASSWORD:
        messages.append(".env.example still contains the exposed Chronicle credential")


def verify(repo_root: Path) -> list[str]:
    messages: list[str] = []
    compose_path = repo_root / "deploy" / "docker-compose.yml"
    example_path = repo_root / ".env.example"
    compose = _load_yaml(compose_path)
    _check_chronicle(compose, messages)
    _check_shared_db_urls(compose, messages)
    try:
        _check_example(example_path, messages)
    except FileNotFoundError:
        messages.append("missing required file: .env.example")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline deploy configuration verifier")
    parser.add_argument("--repo", default=".", help="repository root")
    args = parser.parse_args()
    repo_root = Path(args.repo).resolve()
    try:
        messages = verify(repo_root)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    if messages:
        return _failure(messages)
    print("OK: deploy configuration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
