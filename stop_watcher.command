#!/usr/bin/env bash
set -u

BLINK_DIR="$(cd "$(dirname "$0")" && pwd -P)"
WATCHER="$BLINK_DIR/watcher.py"
PID_FILE="$BLINK_DIR/watcher.pid"

is_expected_process() {
  local pid="$1"
  local command
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command" =~ [Pp]ython && ( "$command" == *"$WATCHER"* || "$command" == *" watcher.py"* ) ]]
}

if [[ ! -f "$PID_FILE" ]]; then
  printf 'Watcher is not running: watcher.pid is missing.\n'
  exit 0
fi

PID="$(tr -dc '0-9' < "$PID_FILE")"
if [[ -z "$PID" ]] || ! is_expected_process "$PID"; then
  rm -f "$PID_FILE"
  printf 'Watcher was already stopped or watcher.pid was stale.\n'
  exit 0
fi

kill -TERM "$PID" 2>/dev/null || true
for _ in 1 2 3 4 5; do
  sleep 1
  if ! is_expected_process "$PID"; then
    rm -f "$PID_FILE"
    printf 'Watcher stopped.\n'
    exit 0
  fi
done

if is_expected_process "$PID"; then
  kill -KILL "$PID" 2>/dev/null || true
fi
rm -f "$PID_FILE"
printf 'Watcher stopped.\n'
