"""Small CLI boundary for the UI location resolver."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import location_store


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    try:
        if args.validate:
            payload = json.load(sys.stdin)
            print(json.dumps({"location": location_store.validate_location(payload)}, ensure_ascii=False))
            return 0
        if not args.query:
            raise ValueError("query is required")
        results = location_store.search_city_from_url(args.url)
        print(json.dumps({"results": results}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI must return a concise failure to the UI.
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
