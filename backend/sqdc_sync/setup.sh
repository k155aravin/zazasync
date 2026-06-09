#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/venv"
LOG_DIR="$ROOT_DIR/logs"
CRON_MARKER="# ZAZASYNC_SYNC_MANAGED"

cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example."
  echo "Fill in the real credentials, then run ./setup.sh again."
  exit 1
fi

set -a
source .env
set +a

required=(SUPABASE_URL SUPABASE_SERVICE_KEY SUPABASE_DB_URL)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" || "${!name}" == *"xxxx"* || "${!name}" == *"yourproject"* ]]; then
    echo "Missing or placeholder value: $name"
    exit 1
  fi
done

command -v python3 >/dev/null || { echo "python3 is required."; exit 1; }
command -v psql >/dev/null || { echo "psql is required to apply schema.sql."; exit 1; }
command -v crontab >/dev/null || { echo "crontab is required."; exit 1; }

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt
"$VENV_DIR/bin/playwright" install chromium

mkdir -p "$LOG_DIR"
chmod 700 .env

echo "Applying Supabase schema..."
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f schema.sql

echo "Running first synchronization..."
"$VENV_DIR/bin/python" sqdc_sync.py stores
"$VENV_DIR/bin/python" sqdc_sync.py products
"$VENV_DIR/bin/python" sqdc_sync.py full

cron_block=$(cat <<EOF
$CRON_MARKER
*/15 * * * * cd $ROOT_DIR && $VENV_DIR/bin/python sqdc_sync.py stock >> logs/sync.log 2>&1
0 3 * * * cd $ROOT_DIR && $VENV_DIR/bin/python sqdc_sync.py full >> logs/full.log 2>&1
*/5 * * * * cd $ROOT_DIR && $VENV_DIR/bin/python alerts.py >> logs/alerts.log 2>&1
EOF
)

if [[ -n "${ANTHROPIC_API_KEY:-}" && "${ANTHROPIC_API_KEY}" != *"xxxx"* ]]; then
  cron_block+=$'\n'"*/30 * * * * cd $ROOT_DIR && $VENV_DIR/bin/python vision_fallback.py >> logs/fallback.log 2>&1"
else
  echo "Anthropic key is not configured; vision fallback cron remains disabled."
fi

existing="$(crontab -l 2>/dev/null || true)"
cleaned="$(printf '%s\n' "$existing" | awk -v marker="$CRON_MARKER" '
  $0 == marker { next }
  /sqdc_sync\.py (stock|full)/ { next }
  /vision_fallback\.py/ { next }
  /alerts\.py/ { next }
  { print }
')"
printf '%s\n%s\n' "$cleaned" "$cron_block" | crontab -

echo
echo "ZazaSync sync system setup completed."
echo "Logs: $LOG_DIR"
echo "Verify with: tail -f $LOG_DIR/sync.log"
