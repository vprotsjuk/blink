import json
import re
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app import to_phone_store


class ToPhoneStoreTests(unittest.TestCase):
    def event(self, **overrides):
        event = {
            "id": "event-123",
            "title": "Bring documents",
            "start": "2026-09-14T15:00:00-07:00",
            "start_dt": datetime.fromisoformat("2026-09-14T15:00:00-07:00"),
            "source": "personal",
            "done": False,
            "enabled": True,
            "reminders_minutes_before": [30],
        }
        event.update(overrides)
        return event

    def test_package_id_is_deterministic_and_safe(self):
        package = to_phone_store.package_id(self.event(), 30)
        self.assertRegex(package, r"^blink-files-v1-[0-9a-f]{32}$")
        self.assertEqual(package, to_phone_store.package_id(self.event(), 30))
        self.assertNotRegex(package, r"[^A-Za-z0-9_-]")

    def test_prepare_snapshot_writes_manifest_files_and_ready_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ToPhone"
            source = Path(tmp) / "attachments" / "event-123"
            source.mkdir(parents=True)
            (source / "Permit.pdf").write_bytes(b"pdf bytes")
            (source / "Photo.jpg").write_bytes(b"jpg bytes")
            (source / ".hidden").write_bytes(b"ignore")
            result = to_phone_store.prepare_snapshot(
                root,
                self.event(),
                30,
                source_root=Path(tmp) / "attachments",
                now=datetime.now(timezone.utc),
            )
            self.assertTrue(result.ready)
            self.assertTrue(result.has_files)
            package = result.package_id
            self.assertTrue((root / f"{package}.manifest.json").exists())
            self.assertTrue((root / f"{package}.ready").exists())
            names = sorted(path.name for path in root.iterdir())
            self.assertEqual(len(names), 4)
            manifest = json.loads((root / f"{package}.manifest.json").read_text())
            self.assertEqual(manifest["type"], "ATTACHMENTS")
            self.assertEqual(manifest["event_id"], "event-123")
            self.assertEqual(len(manifest["files"]), 2)
            self.assertIsNotNone(to_phone_store.validate_package(root, package))

    def test_no_files_produces_no_ready_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ToPhone"
            source = Path(tmp) / "attachments" / "event-123"
            source.mkdir(parents=True)
            result = to_phone_store.prepare_snapshot(
                root, self.event(), 30, source_root=Path(tmp) / "attachments", now=datetime.now(timezone.utc)
            )
            self.assertFalse(result.ready)
            self.assertFalse(result.has_files)
            self.assertEqual(list(root.glob("*")), [])

    def test_regeneration_is_idempotent_and_updates_queued_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ToPhone"
            source = Path(tmp) / "attachments" / "event-123"
            source.mkdir(parents=True)
            source_file = source / "Permit.pdf"
            source_file.write_bytes(b"old")
            kwargs = {"source_root": Path(tmp) / "attachments", "now": datetime.now(timezone.utc)}
            first = to_phone_store.prepare_snapshot(root, self.event(), 30, **kwargs)
            first_bytes = next(path for path in root.iterdir() if "__01__" in path.name).read_bytes()
            second = to_phone_store.prepare_snapshot(root, self.event(), 30, **kwargs)
            self.assertEqual(first.package_id, second.package_id)
            self.assertEqual(first.source_hash, second.source_hash)
            source_file.write_bytes(b"new")
            third = to_phone_store.prepare_snapshot(root, self.event(), 30, **kwargs)
            self.assertEqual(third.package_id, first.package_id)
            self.assertNotEqual(third.source_hash, first.source_hash)
            self.assertNotEqual(first_bytes, next(path for path in root.iterdir() if "__01__" in path.name).read_bytes())

    def test_delivered_snapshot_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ToPhone"
            source = Path(tmp) / "attachments" / "event-123"
            source.mkdir(parents=True)
            source_file = source / "Permit.pdf"
            source_file.write_bytes(b"old")
            kwargs = {"source_root": Path(tmp) / "attachments", "now": datetime.now(timezone.utc)}
            first = to_phone_store.prepare_snapshot(root, self.event(), 30, **kwargs)
            to_phone_store.mark_delivered(root, first.package_id, datetime.now(timezone.utc))
            source_file.write_bytes(b"new")
            second = to_phone_store.prepare_snapshot(root, self.event(), 30, **kwargs)
            self.assertEqual(first.source_hash, second.source_hash)
            self.assertEqual(next(path for path in root.iterdir() if "__01__" in path.name).read_bytes(), b"old")

    def test_invalid_package_stem_and_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ToPhone"
            root.mkdir()
            self.assertIsNone(to_phone_store.validate_package(root, "../../abc"))
            (root / "abc.manifest.json").write_text("{}")
            (root / "abc.ready").write_text("")
            self.assertIsNone(to_phone_store.validate_package(root, "abc"))

    def test_cleanup_removes_only_expired_delivered_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ToPhone"
            source = Path(tmp) / "attachments" / "event-123"
            source.mkdir(parents=True)
            (source / "Permit.pdf").write_bytes(b"pdf")
            old = datetime.now(timezone.utc) - timedelta(days=10)
            result = to_phone_store.prepare_snapshot(
                root, self.event(), 30, source_root=Path(tmp) / "attachments", now=old
            )
            to_phone_store.mark_delivered(root, result.package_id, old)
            removed = to_phone_store.cleanup(root, datetime.now(timezone.utc), ttl_seconds=3600)
            self.assertIn(result.package_id, removed)
            self.assertEqual(list(root.glob("*")), [])


if __name__ == "__main__":
    unittest.main()
