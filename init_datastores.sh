#!/usr/bin/env bash
# init_datastores.sh — Initialise all local datastores (MongoDB, Bigtable, PubSub).
#
# Usage:
#   ./init_datastores.sh
#
# Prerequisites:
#   - docker compose up is running
#   - python3, mongosh, and mongorestore are available on PATH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() { echo "[init] $*"; }
die() { echo "[error] $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
command -v python3 &>/dev/null || die "python3 is not installed or not on PATH."
command -v docker  &>/dev/null || die "docker is not installed or not on PATH."

[[ -f "$SCRIPT_DIR/bigtable/scripts/setup_bigtable.py" ]] || die "setup_bigtable.py not found in $SCRIPT_DIR/bigtable/scripts"
[[ -f "$SCRIPT_DIR/pubsub/scripts/setup_pubsub.py"     ]] || die "setup_pubsub.py not found in $SCRIPT_DIR/pubsub/scripts"
[[ -f "$SCRIPT_DIR/mongodb/scripts/createMtcDB.js"     ]] || die "createMtcDB.js not found in $SCRIPT_DIR/mongodb/scripts"

# ---------------------------------------------------------------------------
# MongoDB setup
# ---------------------------------------------------------------------------
echo ""
log "=== Setting up MongoDB ==="

docker run --rm \
  --network sbe-localdev_default \
  -v "$SCRIPT_DIR/mongodb/scripts:/opt/symphony/scripts" \
  -v "$SCRIPT_DIR/mongodb/data:/opt/symphony/data" \
  mongo:8 bash -c \
    "sleep 5 \
     && mongosh --host mongodb:27017 -u root -p example < /opt/symphony/scripts/createMtcDB.js \
     && mongorestore --uri='mongodb://dbadmin:password@mongodb:27017/mtc' --gzip /opt/symphony/data"

log "MongoDB setup complete."

# ---------------------------------------------------------------------------
# Virtual environment
# ---------------------------------------------------------------------------
echo ""
if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating virtual environment at $VENV_DIR …"
  python3 -m venv "$VENV_DIR"
else
  log "Virtual environment already exists, reusing it."
fi

source "$VENV_DIR/bin/activate"
log "Python: $(python --version)"

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
log "Installing dependencies …"
pip install --quiet --upgrade pip
pip install --quiet google-cloud-bigtable google-cloud-pubsub
log "Dependencies installed."

# ---------------------------------------------------------------------------
# Bigtable setup
# ---------------------------------------------------------------------------
echo ""
log "=== Setting up Bigtable emulator ==="
python "$SCRIPT_DIR/bigtable/scripts/setup_bigtable.py"

# ---------------------------------------------------------------------------
# PubSub setup
# ---------------------------------------------------------------------------
echo ""
log "=== Setting up PubSub emulator ==="
python "$SCRIPT_DIR/pubsub/scripts/setup_pubsub.py"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
log "All done."
