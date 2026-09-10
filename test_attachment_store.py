import tempfile
import unittest
from pathlib import Path

from app import attachment_store
from app import agenda_store


class AttachmentStoreTests(unittest.TestCase):
    def test_owner_id_uses_event_id_for_non_recurring_event(self):
        event = {"id": "event-123", "title": "Call"}
        self.assertEqual(attachment_store.owner_id_for_event(event), "event-123")

    def test_owner_id_uses_occurrence_id_for_recurring_event(self):
        event = {"id": "series-1-g4", "series_id": "series-1", "title": "Standup"}
        self.assertEqual(attachment_store.owner_id_for_event(event), "series-1-g4")
        self.assertEqual(attachment_store.legacy_owner_id_for_event(event), "series-1")

    def test_manifest_normalizes_missing_and_valid_metadata(self):
        event = {"id": "event-123", "title": "Call"}
        self.assertEqual(
            attachment_store.attachment_manifest(None, event),
            {"owner_id": "event-123", "count": 0, "has_files": False},
        )
        self.assertEqual(
            attachment_store.attachment_manifest(
                {"owner_id": "event-123", "count": 2, "has_files": True}, event
            ),
            {"owner_id": "event-123", "count": 2, "has_files": True},
        )

    def test_duplicate_event_gets_new_id_and_unfinished_state(self):
        source = {
            "id": "old",
            "title": "Old title",
            "description": "Old description",
            "start": "2026-09-08T10:00:00-07:00",
            "reminders_minutes_before": [30],
            "enabled": False,
            "requires_done": True,
            "done": True,
            "done_at": "2026-09-08T10:00:00-07:00",
            "attachments": {"owner_id": "old", "count": 2, "has_files": True},
        }
        duplicate = agenda_store.duplicate_event(
            source,
            new_id="new",
            new_start="2026-09-12T11:00:00-07:00",
        )
        self.assertEqual(source["id"], "old")
        self.assertEqual(source["done"], True)
        self.assertEqual(duplicate["id"], "new")
        self.assertEqual(duplicate["start"], "2026-09-12T11:00:00-07:00")
        self.assertTrue(duplicate["enabled"])
        self.assertFalse(duplicate["done"])
        self.assertIsNone(duplicate["done_at"])
        self.assertEqual(
            duplicate["attachments"],
            {"owner_id": "new", "count": 0, "has_files": False},
        )

    def test_attachment_paths_stay_under_blink_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                attachment_store.attachments_root(root), root / "event_data" / "attachments"
            )
            self.assertEqual(
                attachment_store.draft_root(root), root / "event_data" / "drafts"
            )

    def test_legacy_series_migration_is_idempotent_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = attachment_store.attachments_root(root) / "series-1"
            source.mkdir(parents=True)
            (source / "report.pdf").write_bytes(b"pdf")
            events = [
                {"id": "series-1-g1", "series_id": "series-1"},
                {"id": "series-1-g2", "series_id": "series-1"},
            ]
            first = attachment_store.migrate_legacy_series_attachments(root, events)
            second = attachment_store.migrate_legacy_series_attachments(root, events)
            self.assertEqual(first, {"series-1-g1": 1, "series-1-g2": 1})
            self.assertEqual(second, {})
            self.assertTrue((source / "report.pdf").exists())
            self.assertTrue((attachment_store.attachments_root(root) / "series-1-g1" / "report.pdf").exists())
            self.assertTrue((attachment_store.attachments_root(root) / "series-1-g2" / "report.pdf").exists())


if __name__ == "__main__":
    unittest.main()
