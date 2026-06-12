#!/usr/bin/env bash
# =============================================================================
# start_agent.sh — One-click boot sequence for the Hybrid-Local Voice Agent
# =============================================================================
#
# Architecture:
#   TTS  → Local Kokoro-82M  (Docker, port 8888)  — zero API cost
#   LLM  → Ollama :cloud     (localhost:11434)     — M1 RAM stays free
#   STT  → Deepgram cloud    (via LiveKit plugin)
#   SIP  → Vobiz trunk       (via LiveKit SIP)
#
# First-time setup (run once):
#   chmod +x start_agent.sh
#
# Usage:
#   ./start_agent.sh          — normal boot
#   ./start_agent.sh --clean  — pull latest Docker image before starting
# =============================================================================

set -euo pipefail   # exit on error, undefined var, or pipe failure

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m';      RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ── Script directory (works even with symlinks) ───────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Load environment ──────────────────────────────────────────────────────────
if [[ ! -f ".env" ]]; then
  error ".env file not found. Copy .env.example → .env and fill in your credentials."
fi
# Export only the variables we need for health checks (don't source full .env
# into shell — keeps secrets out of process environment of child subshells)
LOCAL_TTS_BASE_URL=$(grep -E '^LOCAL_TTS_BASE_URL=' .env | cut -d= -f2- | tr -d '"' || echo "http://localhost:8888/v1")
LOCAL_LLM_BASE_URL=$(grep -E '^LOCAL_LLM_BASE_URL=' .env | cut -d= -f2- | tr -d '"' || echo "http://localhost:11434/v1")
LOCAL_LLM_MODEL=$(grep -E '^LOCAL_LLM_MODEL=' .env | cut -d= -f2- | tr -d '"' || echo "qwen3:latest")

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       🎙  Hybrid-Local Voice Agent — Boot Sequence       ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Optional: pull latest image ───────────────────────────────────────────────
if [[ "${1:-}" == "--clean" ]]; then
  info "Pulling latest Kokoro-FastAPI image..."
  docker compose -f docker-compose.tts.yml pull
fi

# =============================================================================
# STEP 1 — Start Local Kokoro TTS Engine
# =============================================================================
echo -e "\n${BOLD}STEP 1 of 3 — Starting Local Kokoro TTS Engine...${RESET}"
info "Launching kokoro-tts container (port 8888)..."

docker compose -f docker-compose.tts.yml up -d

# Wait for the health endpoint to become responsive (up to 90 seconds)
TTS_HOST="${LOCAL_TTS_BASE_URL%/v1}"   # strip /v1 suffix → http://localhost:8888
WAIT_SECS=90
ELAPSED=0
printf "${CYAN}[INFO]${RESET}  Waiting for Kokoro TTS health check"
until curl -sf "${TTS_HOST}/health" > /dev/null 2>&1; do
  if (( ELAPSED >= WAIT_SECS )); then
    echo ""
    warn "Kokoro TTS did not become healthy within ${WAIT_SECS}s."
    warn "Check logs: docker compose -f docker-compose.tts.yml logs -f"
    warn "Continuing anyway — TTS calls may fail until it's ready."
    break
  fi
  printf "."
  sleep 3
  (( ELAPSED += 3 ))
done
echo ""
success "Kokoro TTS is up at ${TTS_HOST}"

# =============================================================================
# STEP 2 — Verify Ollama Cloud Connection
# =============================================================================
echo -e "\n${BOLD}STEP 2 of 3 — Verifying Ollama Cloud connection...${RESET}"

# Check that the Ollama daemon is running locally
OLLAMA_BASE="${LOCAL_LLM_BASE_URL%/v1}"   # → http://localhost:11434
if curl -sf "${OLLAMA_BASE}/api/version" > /dev/null 2>&1; then
  OLLAMA_VERSION=$(curl -sf "${OLLAMA_BASE}/api/version" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','unknown'))" 2>/dev/null || echo "running")
  success "Ollama daemon is running (version: ${OLLAMA_VERSION})"
else
  warn "Ollama daemon not detected at ${OLLAMA_BASE}."
  warn "Install from https://ollama.com/download, then run: ollama serve"
  warn "Continuing — agent will fail at LLM calls until Ollama is available."
fi

# Check the target model is pulled (non-fatal)
info "Checking model availability: ${LOCAL_LLM_MODEL}"
if ollama list 2>/dev/null | grep -q "${LOCAL_LLM_MODEL%%:*}"; then
  success "Model '${LOCAL_LLM_MODEL}' found in local Ollama registry."
else
  warn "Model '${LOCAL_LLM_MODEL}' not found locally."
  info "Pulling model now (this may take a few minutes on first run)..."
  ollama pull "${LOCAL_LLM_MODEL}" || warn "Pull failed — check your internet connection or model name."
fi

# =============================================================================
# STEP 3 — Boot the LiveKit Voice Agent
# =============================================================================
echo -e "\n${BOLD}STEP 3 of 3 — Booting LiveKit Voice Agent...${RESET}"
info "Loading environment and starting agent worker..."
echo ""

# Activate virtualenv if present
if [[ -f "venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "venv/bin/activate"
  info "Activated venv."
elif [[ -f ".venv/bin/activate" ]]; then
  source ".venv/bin/activate"
  info "Activated .venv."
fi

# Hand off to the agent — all .env vars are loaded by python-dotenv inside agent.py
exec python agent.py start
