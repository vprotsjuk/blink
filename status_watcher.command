#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/vitaliiprotsiuk/Desktop/Blink"
cd "$PROJECT_DIR"

"$PROJECT_DIR/.venv/bin/python" - <<'PY'
from pathlib import Path
from app import watcher_lifecycle

status = watcher_lifecycle.status(Path("watcher_runtime.json"))
print(f"Blink Watcher status: {status['state']}")
if "pid" in status:
    print(f"pid: {status['pid']}")
if "last_heartbeat_at" in status:
    print(f"last heartbeat: {status['last_heartbeat_at']}")
if "age_seconds" in status:
    print(f"heartbeat age: {status['age_seconds']} seconds")
if "reason" in status:
    print(f"reason: {status['reason']}")
PY

echo ""
echo "watcher.py processes:"
ps ax -o pid= -o command= | awk -v project="$PROJECT_DIR" '($0 ~ project "/watcher.py" || $0 ~ / watcher.py/) && $0 ~ /[Pp]ython/ {print $0}' || true

echo ""
echo "launchctl:"
launchctl list | grep com.vitalii.blink.watcher || true
launchctl list | grep com.vitalii.blink.app || true
