from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_deploy_config.py"


GOOD_COMPOSE = textwrap.dedent(
    """
    name: jarvis-family
    services:
      jarvis:
        build:
          context: ../
          dockerfile: Dockerfile
        restart: unless-stopped
        env_file: .env
        volumes:
          - jarvis_data:/app/data
          - chronicle_snapshots:/chronicle-snapshots
        environment:
          CHRONICLE_SNAPSHOT_DIR: /chronicle-snapshots
          CHRONICLE_API_URL: http://chronicle:5174
          GHOSTWRITR_BASE_URL: http://ghostwritr:3000
          CATALYST_DB_URL: postgresql://${DB_USER:?DB_USER is required}:${DB_PASSWORD:?DB_PASSWORD is required}@postgres:5432/jarvis_catalyst
          JARVIS_HOME_DB_URL: postgresql://${DB_USER:?DB_USER is required}:${DB_PASSWORD:?DB_PASSWORD is required}@postgres:5432/jarvis_home
          JARVIS_BACKGROUND_AGENTS_ENABLED: "false"
        depends_on:
          postgres:
            condition: service_healthy
        networks:
          - internal
      chronicle:
        build:
          context: ../../chronicle
          dockerfile: Dockerfile
        restart: unless-stopped
        env_file: .env
        volumes:
          - chronicle_snapshots:/app/chronicle-data
        environment:
          CHRONICLE_DATABASE_URL: postgresql://${DB_USER:?DB_USER is required}:${DB_PASSWORD:?DB_PASSWORD is required}@postgres:5432/chronicle
        depends_on:
          postgres:
            condition: service_healthy
        networks:
          - internal
      postgres:
        image: postgres:16-alpine
        restart: unless-stopped
        env_file: .env
        environment:
          POSTGRES_USER: ${DB_USER:?DB_USER is required}
          POSTGRES_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD is required}
          POSTGRES_DB: ghostwritr
        volumes:
          - postgres_data:/var/lib/postgresql/data
          - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U ${DB_USER:?DB_USER is required}"]
          interval: 5s
          timeout: 5s
          retries: 10
        networks:
          - internal
      redis:
        image: redis:7-alpine
        restart: unless-stopped
        volumes:
          - redis_data:/data
        healthcheck:
          test: ["CMD", "redis-cli", "ping"]
          interval: 5s
          timeout: 3s
          retries: 5
        networks:
          - internal
      nginx:
        image: nginx:alpine
        restart: unless-stopped
        ports:
          - "80:80"
        volumes:
          - ./nginx.conf:/etc/nginx/nginx.conf:ro
        depends_on:
          - jarvis
        networks:
          - internal
      cloudflared:
        image: cloudflare/cloudflared:latest
        restart: unless-stopped
        command: tunnel --no-autoupdate run
        environment:
          TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN}
        depends_on:
          - nginx
        networks:
          - internal
    networks:
      internal:
        driver: bridge
    volumes:
      jarvis_data:
      chronicle_snapshots:
      postgres_data:
      redis_data:
    """
).strip()


GOOD_ENV = textwrap.dedent(
    """
    DB_USER=your-jarvis-db-user-here
    DB_PASSWORD=your-jarvis-db-password-here
    """
).strip()


def write_repo(root: Path, compose: str = GOOD_COMPOSE, env: str = GOOD_ENV) -> None:
    (root / "deploy").mkdir(parents=True, exist_ok=True)
    (root / "deploy" / "docker-compose.yml").write_text(compose + "\n", encoding="utf-8")
    (root / ".env.example").write_text(env + "\n", encoding="utf-8")


def run_verifier(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), "--repo", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


class DeployConfigVerifierTests(unittest.TestCase):
    def test_current_repo_passes(self) -> None:
        result = run_verifier(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("verified", result.stdout)

    def test_good_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_repo(repo)
            result = run_verifier(repo)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_literal_credential_is_rejected(self) -> None:
        bad_compose = GOOD_COMPOSE.replace(
            "postgresql://${DB_USER:?DB_USER is required}:${DB_PASSWORD:?DB_PASSWORD is required}@postgres:5432/chronicle",
            "postgresql://jarvis:JarvisFamily2026!@postgres:5432/chronicle",
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_repo(repo, compose=bad_compose)
            result = run_verifier(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("literal credential", result.stdout)

    def test_missing_required_interpolation_is_rejected(self) -> None:
        bad_compose = GOOD_COMPOSE.replace(
            "${DB_USER:?DB_USER is required}:${DB_PASSWORD:?DB_PASSWORD is required}",
            "${DB_USER}:${DB_PASSWORD}",
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_repo(repo, compose=bad_compose)
            result = run_verifier(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("required DB_USER and DB_PASSWORD interpolation", result.stdout)

    def test_example_must_use_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_repo(repo, env="DB_USER=jarvis\nDB_PASSWORD=JarvisFamily2026!")
            result = run_verifier(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("placeholder", result.stdout)


if __name__ == "__main__":
    unittest.main()
