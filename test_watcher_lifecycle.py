import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import watcher_lifecycle


class WatcherLifecycleTests(unittest.TestCase):
    def test_heartbeat_records_pid_and_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watcher_runtime.json"
            now = datetime.fromisoformat("2026-09-07T12:00:00-07:00")

            watcher_lifecycle.write_heartbeat(path, now=now, pid=1234)

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["pid"], 1234)
            self.assertEqual(payload["last_heartbeat_at"], "2026-09-07T12:00:00-07:00")

    def test_status_reports_running_for_current_pid_and_fresh_heartbeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watcher_runtime.json"
            now = datetime.now(timezone.utc).astimezone()
            watcher_lifecycle.write_heartbeat(path, now=now, pid=os.getpid())

            status = watcher_lifecycle.status(path, now=now + timedelta(seconds=30))

            self.assertEqual(status["state"], "running")
            self.assertEqual(status["pid"], os.getpid())

    def test_status_reports_stale_when_heartbeat_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watcher_runtime.json"
            now = datetime.fromisoformat("2026-09-07T12:00:00+00:00")
            watcher_lifecycle.write_heartbeat(path, now=now, pid=os.getpid())

            status = watcher_lifecycle.status(path, now=now + timedelta(minutes=6), stale_after_seconds=120)

            self.assertEqual(status["state"], "stale")

    def test_status_reports_stopped_for_missing_runtime_file(self):
        status = watcher_lifecycle.status(Path("/tmp/blink-missing-runtime-file.json"))
        self.assertEqual(status["state"], "stopped")

    def test_sleep_gap_detected_only_after_threshold(self):
        before = datetime.fromisoformat("2026-09-07T12:00:00+00:00")
        after = datetime.fromisoformat("2026-09-07T12:09:00+00:00")
        short = datetime.fromisoformat("2026-09-07T12:01:00+00:00")

        self.assertTrue(watcher_lifecycle.detect_sleep_gap(before, after, poll_interval_seconds=10))
        self.assertFalse(watcher_lifecycle.detect_sleep_gap(before, short, poll_interval_seconds=10))


if __name__ == "__main__":
    unittest.main()
