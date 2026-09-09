#!/usr/bin/env bash
set -u

BLINK_DIR="$(cd "$(dirname "$0")" && pwd -P)"
WATCHER="$BLINK_DIR/watcher.py"
PYTHON="$BLINK_DIR/.venv/bin/python"
CONFIG="$BLINK_DIR/config.json"
AGENDA="$BLINK_DIR/agenda.json"
PID_FILE="$BLINK_DIR/watcher.pid"
STDOUT_LOG="$BLINK_DIR/watcher.stdout.log"
STDERR_LOG="$BLINK_DIR/watcher.stderr.log"
LAUNCHD_LABEL="com.vitalii.blink.watcher"

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

is_expected_process() {
  local pid="$1"
  local command
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command" =~ [Pp]ython && ( "$command" == *"$WATCHER"* || "$command" == *" watcher.py"* ) ]]
}

running_launch_agent_pid() {
  launchctl list 2>/dev/null | awk -v label="$LAUNCHD_LABEL" '$3 == label && $1 ~ /^[0-9]+$/ {print $1; exit}'
}

launch_agent_is_loaded() {
  launchctl list 2>/dev/null | awk -v label="$LAUNCHD_LABEL" '$3 == label {found=1} END {exit found ? 0 : 1}'
}

running_watcher_pids() {
  ps ax -o pid= -o command= | awk -v watcher="$WATCHER" '($0 ~ watcher || $0 ~ / watcher.py/) && $0 ~ /[Pp]ython/ {print $1}'
}

[[ -f "$WATCHER" ]] || fail "Missing watcher.py in $BLINK_DIR"
[[ -x "$PYTHON" ]] || fail "Missing executable project Python: $PYTHON"
[[ -f "$CONFIG" ]] || fail "Missing config.json in $BLINK_DIR"
[[ -f "$AGENDA" ]] || fail "Missing agenda.json in $BLINK_DIR"

TOPIC_CHECK="$(/usr/bin/env python3 - "$CONFIG" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"invalid config.json: {exc}", file=sys.stderr)
    raise SystemExit(2)

topic = str(data.get("ntfy_topic", "")).strip()
if not topic or topic.startswith("REPLACE_WITH"):
    print("placeholder", file=sys.stderr)
    raise SystemExit(3)
print("ok")
PY
)"
STATUS=$?
if [[ $STATUS -ne 0 ]]; then
  fail "Setup error: paste the full private ntfy topic into config.json before starting Watcher."
fi

if [[ -f "$PID_FILE" ]]; then
  PID="$(tr -dc '0-9' < "$PID_FILE")"
  if [[ -n "$PID" ]] && is_expected_process "$PID"; then
    printf 'Watcher is already running.\nPID: %s\nLog: %s\n' "$PID" "$BLINK_DIR/watcher.log"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

LAUNCHD_PID="$(running_launch_agent_pid)"
if [[ -n "$LAUNCHD_PID" ]] && is_expected_process "$LAUNCHD_PID"; then
  printf 'Watcher is already running under LaunchAgent.\nPID: %s\nStatus: %s/status_watcher.command\n' "$LAUNCHD_PID" "$BLINK_DIR"
  exit 0
fi

if launch_agent_is_loaded; then
  launchctl kickstart -k "gui/$(id -u)/$LAUNCHD_LABEL" >/dev/null 2>&1 || launchctl start "$LAUNCHD_LABEL" >/dev/null 2>&1 || true
  sleep 2
  LAUNCHD_PID="$(running_launch_agent_pid)"
  if [[ -n "$LAUNCHD_PID" ]] && is_expected_process "$LAUNCHD_PID"; then
    printf 'Watcher LaunchAgent was restarted.\nPID: %s\nStatus: %s/status_watcher.command\n' "$LAUNCHD_PID" "$BLINK_DIR"
    exit 0
  fi
  fail "Watcher LaunchAgent is loaded but did not start. Run install_launch_agent.command and then status_watcher.command."
fi

EXISTING_PIDS="$(running_watcher_pids | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
if [[ -n "$EXISTING_PIDS" ]]; then
  printf 'Watcher is already running.\nPID(s): %s\nUse status_watcher.command to inspect.\n' "$EXISTING_PIDS"
  exit 0
fi

cd "$BLINK_DIR" || exit 1
nohup "$PYTHON" "$WATCHER" > "$STDOUT_LOG" 2> "$STDERR_LOG" &
PID=$!
printf '%s\n' "$PID" > "$PID_FILE"

sleep 1
if ! is_expected_process "$PID"; then
  rm -f "$PID_FILE"
  fail "Watcher failed to stay running. Check $STDERR_LOG and $STDOUT_LOG."
fi

printf 'Watcher started.\nPID: %s\nLog: %s\n' "$PID" "$BLINK_DIR/watcher.log"
