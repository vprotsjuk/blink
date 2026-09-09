#!/usr/bin/env bash
set -u

BLINK_DIR="$(cd "$(dirname "$0")" && pwd -P)"
CONFIG="$BLINK_DIR/config.json"

read_config() {
  /usr/bin/env python3 - "$CONFIG" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
server = str(data.get("ntfy_server", "https://ntfy.sh")).strip().rstrip("/")
topic = str(data.get("ntfy_topic", "")).strip()
if not topic or topic.startswith("REPLACE_WITH"):
    print("Setup error: paste the full private ntfy topic into config.json first.", file=sys.stderr)
    raise SystemExit(3)
print(server)
print(topic)
PY
}

CONFIG_VALUES="$(read_config)" || exit 1
SERVER="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '1p')"
TOPIC="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '2p')"
REDACTED_TOPIC="$(/usr/bin/env python3 - "$TOPIC" <<'PY'
import sys
topic = sys.argv[1]
print("<redacted>" if len(topic) <= 8 else f"{topic[:16]}...{topic[-3:]}")
PY
)"
URL="$SERVER/$TOPIC"
BODY="The Blink push notification connection is working."

if command -v curl >/dev/null 2>&1; then
  HTTP_CODE="$(curl -sS -o /dev/null -w '%{http_code}' \
    -X POST "$URL" \
    -H 'Title: Blink manual test' \
    -H 'Priority: high' \
    -H 'Tags: calendar,test' \
    -H 'Content-Type: text/plain; charset=utf-8' \
    --data-binary "$BODY")"
  if [[ "$HTTP_CODE" == 2* ]]; then
    printf 'Manual push test succeeded for topic %s.\n' "$REDACTED_TOPIC"
    exit 0
  fi
  printf 'Manual push test failed with HTTP status %s for topic %s.\n' "$HTTP_CODE" "$REDACTED_TOPIC" >&2
  exit 1
fi

/usr/bin/env python3 - "$URL" "$REDACTED_TOPIC" <<'PY'
import sys
import urllib.request

url, redacted = sys.argv[1], sys.argv[2]
body = "The Blink push notification connection is working.".encode("utf-8")
request = urllib.request.Request(
    url,
    data=body,
    method="POST",
    headers={
        "Title": "Blink manual test",
        "Priority": "high",
        "Tags": "calendar,test",
        "Content-Type": "text/plain; charset=utf-8",
    },
)
try:
    with urllib.request.urlopen(request, timeout=10) as response:
        status = response.getcode()
except Exception as exc:
    print(f"Manual push test failed for topic {redacted}: {exc}", file=sys.stderr)
    raise SystemExit(1)

if 200 <= status < 300:
    print(f"Manual push test succeeded for topic {redacted}.")
else:
    print(f"Manual push test failed with HTTP status {status} for topic {redacted}.", file=sys.stderr)
    raise SystemExit(1)
PY
