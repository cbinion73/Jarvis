#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAUNCHD_DIR="${HOME}/Library/LaunchAgents"
LOG_DIR="${REPO_ROOT}/data/logs"

mkdir -p "${LAUNCHD_DIR}"
mkdir -p "${LOG_DIR}"

runtime_template="${REPO_ROOT}/ops/launchd/com.jarvis.runtime.plist.template"
openviking_template="${REPO_ROOT}/ops/launchd/com.jarvis.openviking.plist.template"
assistant_template="${REPO_ROOT}/ops/launchd/com.jarvis.assistant-autonomy.plist.template"
guardian_template="${REPO_ROOT}/ops/launchd/com.jarvis.guardian.plist.template"

runtime_target="${LAUNCHD_DIR}/com.jarvis.runtime.plist"
openviking_target="${LAUNCHD_DIR}/com.jarvis.openviking.plist"
assistant_target="${LAUNCHD_DIR}/com.jarvis.assistant-autonomy.plist"
guardian_target="${LAUNCHD_DIR}/com.jarvis.guardian.plist"

render_template() {
  local src="$1"
  local dst="$2"
  sed "s|/ABSOLUTE/PATH/TO/JARVIS|${REPO_ROOT}|g" "${src}" > "${dst}"
}

render_template "${runtime_template}" "${runtime_target}"
render_template "${openviking_template}" "${openviking_target}"
render_template "${assistant_template}" "${assistant_target}"
render_template "${guardian_template}" "${guardian_target}"

launchctl bootout "gui/$(id -u)" "${runtime_target}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${openviking_target}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${assistant_target}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${guardian_target}" >/dev/null 2>&1 || true
launchctl unload "${runtime_target}" >/dev/null 2>&1 || true
launchctl unload "${openviking_target}" >/dev/null 2>&1 || true
launchctl unload "${assistant_target}" >/dev/null 2>&1 || true
launchctl unload "${guardian_target}" >/dev/null 2>&1 || true

launchctl bootstrap "gui/$(id -u)" "${runtime_target}"
launchctl bootstrap "gui/$(id -u)" "${openviking_target}"
launchctl bootstrap "gui/$(id -u)" "${assistant_target}"
launchctl bootstrap "gui/$(id -u)" "${guardian_target}"

launchctl enable "gui/$(id -u)/com.jarvis.runtime" >/dev/null 2>&1 || true
launchctl enable "gui/$(id -u)/com.jarvis.openviking" >/dev/null 2>&1 || true
launchctl enable "gui/$(id -u)/com.jarvis.assistant-autonomy" >/dev/null 2>&1 || true
launchctl enable "gui/$(id -u)/com.jarvis.guardian" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$(id -u)/com.jarvis.runtime" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$(id -u)/com.jarvis.openviking" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$(id -u)/com.jarvis.assistant-autonomy" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$(id -u)/com.jarvis.guardian" >/dev/null 2>&1 || true

cat <<EOF
Installed launchd services:
  ${runtime_target}
  ${openviking_target}
  ${assistant_target}
  ${guardian_target}

Quick checks:
  launchctl list | rg jarvis
  curl http://127.0.0.1:8787/health
  curl http://127.0.0.1:1933/health

Logs:
  ${REPO_ROOT}/data/logs/jarvis-runtime.stdout.log
  ${REPO_ROOT}/data/logs/jarvis-runtime.stderr.log
  ${REPO_ROOT}/data/logs/openviking.stdout.log
  ${REPO_ROOT}/data/logs/openviking.stderr.log
  ${REPO_ROOT}/data/logs/jarvis-assistant-autonomy.stdout.log
  ${REPO_ROOT}/data/logs/jarvis-assistant-autonomy.stderr.log
  ${REPO_ROOT}/data/logs/jarvis-guardian.stdout.log
  ${REPO_ROOT}/data/logs/jarvis-guardian.stderr.log
EOF
