#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# JARVIS macOS Setup Script
# Idempotent — safe to run multiple times.
# =============================================================================

JARVIS_DIR="$HOME/.jarvis"
VENV_DIR="$JARVIS_DIR/venv"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_SRC="$PROJECT_ROOT/com.jarvis.backend.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.jarvis.backend.plist"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[JARVIS]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# -----------------------------------------------------------------------------
# 1. Homebrew
# -----------------------------------------------------------------------------
info "Checking Homebrew..."
if ! command -v brew &>/dev/null; then
  info "Homebrew not found — installing..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to PATH for Apple Silicon
  if [[ -f /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
else
  info "Homebrew already installed: $(brew --version | head -1)"
fi

# -----------------------------------------------------------------------------
# 2. Python 3.11+
# -----------------------------------------------------------------------------
info "Checking Python 3.11+..."
PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" &>/dev/null; then
    ver=$("$candidate" -c 'import sys; print(sys.version_info[:2])' 2>/dev/null || true)
    major=$("$candidate" -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo 0)
    minor=$("$candidate" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo 0)
    if [[ "$major" -ge 3 && "$minor" -ge 11 ]]; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  warn "Python 3.11+ not found — installing via Homebrew..."
  brew install python@3.11
  PYTHON_BIN="$(brew --prefix)/bin/python3.11"
fi
info "Using Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# -----------------------------------------------------------------------------
# 3. ~/.jarvis/ directory structure
# -----------------------------------------------------------------------------
info "Creating ~/.jarvis/ directory structure..."
for subdir in scheduler memory approvals health briefings data logs voices; do
  mkdir -p "$JARVIS_DIR/$subdir"
  info "  $JARVIS_DIR/$subdir"
done

# -----------------------------------------------------------------------------
# 4. Virtual environment
# -----------------------------------------------------------------------------
info "Setting up venv at $VENV_DIR..."
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  info "venv created."
else
  info "venv already exists — skipping creation."
fi

# Activate for the rest of this script
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
info "venv activated: $(python --version)"

# -----------------------------------------------------------------------------
# 5. Install project in editable mode
# -----------------------------------------------------------------------------
info "Installing project (pip install -e .) from $PROJECT_ROOT..."
pip install --upgrade pip --quiet
pip install -e "$PROJECT_ROOT" --quiet
info "Project installed."

# -----------------------------------------------------------------------------
# 6. Voice requirements (optional)
# -----------------------------------------------------------------------------
VOICE_REQS="$PROJECT_ROOT/requirements_voice.txt"
if [[ -f "$VOICE_REQS" ]]; then
  info "Installing requirements_voice.txt..."
  pip install -r "$VOICE_REQS" --quiet
  info "Voice requirements installed."
else
  warn "requirements_voice.txt not found — skipping voice dependencies."
fi

# -----------------------------------------------------------------------------
# 7. Ollama
# -----------------------------------------------------------------------------
info "Checking Ollama..."
if ! command -v ollama &>/dev/null; then
  info "Ollama not found — installing via Homebrew..."
  brew install ollama
else
  info "Ollama already installed: $(ollama --version 2>/dev/null || echo 'version unknown')"
fi

# Ensure Ollama server is running for model pulls
if ! pgrep -x ollama &>/dev/null; then
  info "Starting Ollama server in background for model pulls..."
  ollama serve &>/dev/null &
  OLLAMA_PID=$!
  sleep 3
  STARTED_OLLAMA=true
else
  STARTED_OLLAMA=false
fi

# Pull models
info "Pulling ollama model: phi3.5 (fast classifier)..."
ollama pull phi3.5 || warn "Failed to pull phi3.5 — pull manually with: ollama pull phi3.5"

# NOTE: 'gpt-oss-20b' is not a standard Ollama model name as of this writing.
# It is used here as the configured reasoning model ID (JARVIS_OLLAMA_REASONING_MODEL).
# If the model is not available in the Ollama registry under that name, the pull
# will fail gracefully and 'openhermes' is offered as a capable open-source substitute.
# To use openhermes instead, run: ollama pull openhermes
info "Pulling ollama model: gpt-oss-20b (reasoning model)..."
if ! ollama pull gpt-oss-20b 2>/dev/null; then
  warn "gpt-oss-20b not found in Ollama registry."
  warn "Pulling openhermes as a placeholder reasoning model instead."
  warn "Update JARVIS_OLLAMA_REASONING_MODEL in ~/.jarvis/.env when the correct model is available."
  ollama pull openhermes || warn "Failed to pull openhermes — pull manually with: ollama pull openhermes"
fi

# Stop the temporary Ollama process if we started it
if [[ "$STARTED_OLLAMA" == "true" ]]; then
  kill "$OLLAMA_PID" 2>/dev/null || true
fi

# -----------------------------------------------------------------------------
# 8. Friday's Piper voice — en_US-hfc_female-medium
# -----------------------------------------------------------------------------
VOICE_DIR="$JARVIS_DIR/voices"
PIPER_ONNX="$VOICE_DIR/en_US-hfc_female-medium.onnx"
PIPER_JSON="$VOICE_DIR/en_US-hfc_female-medium.onnx.json"
HF_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium"

info "Checking Friday's Piper voice..."
if [[ ! -f "$PIPER_ONNX" ]]; then
  info "Downloading en_US-hfc_female-medium.onnx (63 MB)..."
  curl -fL --progress-bar -o "$PIPER_ONNX" "${HF_BASE}/en_US-hfc_female-medium.onnx?download=true" \
    || warn "Voice download failed — run manually: curl -L -o '$PIPER_ONNX' '${HF_BASE}/en_US-hfc_female-medium.onnx?download=true'"
else
  info "Voice model already present: $PIPER_ONNX"
fi
if [[ ! -f "$PIPER_JSON" ]]; then
  info "Downloading en_US-hfc_female-medium.onnx.json..."
  curl -fsSL -o "$PIPER_JSON" "${HF_BASE}/en_US-hfc_female-medium.onnx.json?download=true" \
    || warn "Voice config download failed — run manually: curl -L -o '$PIPER_JSON' '${HF_BASE}/en_US-hfc_female-medium.onnx.json?download=true'"
else
  info "Voice config already present: $PIPER_JSON"
fi

# -----------------------------------------------------------------------------
# 10. .env file
# -----------------------------------------------------------------------------
info "Checking .env file..."
ENV_DST="$JARVIS_DIR/.env"
ENV_SRC="$PROJECT_ROOT/.env.example"

if [[ ! -f "$ENV_DST" ]]; then
  if [[ -f "$ENV_SRC" ]]; then
    cp "$ENV_SRC" "$ENV_DST"
    info "Copied .env.example → $ENV_DST"
  else
    warn ".env.example not found — skipping .env creation."
  fi
else
  info ".env already exists at $ENV_DST — not overwriting."
fi

# -----------------------------------------------------------------------------
# 11. launchd plist
# -----------------------------------------------------------------------------
info "Installing launchd plist..."
mkdir -p "$HOME/Library/LaunchAgents"

if [[ ! -f "$PLIST_SRC" ]]; then
  error "Plist source not found: $PLIST_SRC"
  error "Run this script from the project root or ensure com.jarvis.backend.plist exists."
  exit 1
fi

cp "$PLIST_SRC" "$PLIST_DST"
info "Copied plist → $PLIST_DST"

# Unload first if already loaded (idempotency)
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"
info "launchd service loaded: com.jarvis.backend"

# =============================================================================
# Final checklist
# =============================================================================
echo ""
echo -e "${GREEN}========================================================${NC}"
echo -e "${GREEN}  JARVIS setup complete!${NC}"
echo -e "${GREEN}========================================================${NC}"
echo ""
echo "  Backend will start automatically at login via launchd."
echo "  To start it now:  launchctl start com.jarvis.backend"
echo "  To stop it:       launchctl stop  com.jarvis.backend"
echo "  Logs:             ~/.jarvis/logs/jarvis.log"
echo "  Error log:        ~/.jarvis/logs/jarvis.error.log"
echo ""
echo -e "${YELLOW}  MANUAL STEPS STILL REQUIRED:${NC}"
echo "  Edit $ENV_DST and fill in:"
echo ""
echo "    [ ] OPENAI_API_KEY        — https://platform.openai.com/api-keys"
echo "    [ ] ELEVENLABS_API_KEY    — https://elevenlabs.io (optional, for ElevenLabs TTS)"
echo "    [ ] OPENWEATHER_API_KEY   — https://openweathermap.org/api"
echo "    [ ] HA_URL                — Your Home Assistant base URL"
echo "    [ ] HA_TOKEN              — HA profile → Long-Lived Access Tokens"
echo "    [ ] GOOGLE_CLIENT_ID      — https://console.cloud.google.com → OAuth credentials"
echo "    [ ] GOOGLE_CLIENT_SECRET  — same as above"
echo ""
echo "  OpenViking (already installed, enabled for localhost):"
echo "    [ ] Run: openviking-server init   (one-time setup)"
echo "    [ ] Then keep it running: nohup openviking-server > ~/.jarvis/logs/openviking.log 2>&1 &"
echo "    No API key needed — local server at http://127.0.0.1:1933"
echo ""
echo "  Friday's Piper voice:"
if [[ -f "$PIPER_ONNX" ]]; then
  echo "    [✓] Voice downloaded: $PIPER_ONNX"
else
  echo "    [ ] Voice not downloaded — check curl output above"
fi
echo ""
echo "  After editing .env, reload the plist so launchd picks up the new values:"
echo "    launchctl unload $PLIST_DST"
echo "    launchctl load   $PLIST_DST"
echo ""
echo -e "${YELLOW}  NOTE:${NC} launchd EnvironmentVariables in the plist are separate"
echo "  from ~/.jarvis/.env. If you change API keys, update BOTH the plist"
echo "  AND ~/.jarvis/.env (the plist is the authoritative source for launchd)."
echo ""
