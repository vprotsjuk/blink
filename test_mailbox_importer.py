import json
import tempfile
import unittest
import uuid
from pathlib import Path

from app import mailbox_importer


def write_ready_package(root: Path, package_id: str, payload: dict, attachment: bytes | None = None) -> None:
    (root / f"{package_id}.event.json").write_text(json.dumps(payload), encoding="utf-8")
    if attachment is not None:
        (root / f"{package_id}.attachment.pdf").write_bytes(attachment)
    (root / f"{package_id}.ready").write_text("ready\n", encoding="utf-8")


def create_payload(package_id: str, *, attachment: bool = False) -> dict:
    payload = {
        "version": 1,
        "type": "CREATE_EVENT",
        "transfer_id": package_id,
        "title": "Remote event",
        "description": "Optional text",
        "start": "2026-09-13T09:00:00-07:00",
        "reminder_intent": {"offsets_minutes_before": [30, 0]},
        "attention_level": "yellow",
        "blinker_intent": {"minutes_before": 0},
        "created_at": "2026-09-12T18:30:00-07:00",
    }
    if attachment:
        payload["attachment"] = {
            "basename": f"{package_id}.attachment.pdf",
            "original_filename": "contract.pdf",
        }
    return payload


class MailboxImporterTests(unittest.TestCase):
    def test_valid_done_requires_ready_and_matching_command_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_id = str(uuid.uuid4())
            (root / f"{command_id}.done.json").write_text(
                json.dumps({
                    "version": 1,
                    "type": "DONE",
                    "command_id": command_id,
                    "event_id": "event-123",
                }),
                encoding="utf-8",
            )
            (root / f"{command_id}.ready").write_text("ready\n", encoding="utf-8")
            candidate = mailbox_importer.discover_packages(root)[0]
            parsed = mailbox_importer.parse_package(candidate)
            self.assertEqual(parsed.kind, "DONE")
            self.assertEqual(parsed.event_id, "event-123")

    def test_ready_missing_json_is_pending_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            (root / f"{package_id}.ready").write_text("ready\n", encoding="utf-8")
            candidate = mailbox_importer.discover_packages(root)[0]
            with self.assertRaises(mailbox_importer.PendingSync):
                mailbox_importer.parse_package(candidate)

    def test_no_ready_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            (root / f"{package_id}.done.json").write_text("{}", encoding="utf-8")
            self.assertEqual(mailbox_importer.discover_packages(root), [])

    def test_valid_create_with_attachment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            write_ready_package(root, package_id, create_payload(package_id, attachment=True), b"pdf")
            parsed = mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])
            self.assertEqual(parsed.kind, "CREATE_EVENT")
            self.assertEqual(parsed.transfer_id, package_id)
            self.assertEqual(parsed.attachment_path.name, f"{package_id}.attachment.pdf")

    def test_create_rejects_internal_agenda_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            payload = create_payload(package_id)
            payload["done"] = False
            write_ready_package(root, package_id, payload)
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_done_rejects_occurrence_id_transport_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_id = str(uuid.uuid4())
            payload = {
                "version": 1,
                "type": "DONE",
                "command_id": command_id,
                "event_id": "event-123",
                "occurrence_id": "occ-123",
            }
            (root / f"{command_id}.done.json").write_text(json.dumps(payload), encoding="utf-8")
            (root / f"{command_id}.ready").write_text("ready\n", encoding="utf-8")
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_mismatched_filename_and_json_identity_is_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            filename_id = str(uuid.uuid4())
            payload_id = str(uuid.uuid4())
            write_ready_package(root, filename_id, create_payload(payload_id))
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_symlink_attachment_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            payload = create_payload(package_id, attachment=True)
            (root / "source.pdf").write_bytes(b"pdf")
            (root / f"{package_id}.event.json").write_text(json.dumps(payload), encoding="utf-8")
            (root / f"{package_id}.attachment.pdf").symlink_to(root / "source.pdf")
            (root / f"{package_id}.ready").write_text("ready\n", encoding="utf-8")
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_create_rejects_path_like_original_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            payload = create_payload(package_id, attachment=True)
            payload["attachment"]["original_filename"] = "../secret.pdf"
            write_ready_package(root, package_id, payload, b"pdf")
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_ready_attachment_missing_is_pending_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            write_ready_package(root, package_id, create_payload(package_id, attachment=True), None)
            candidate = mailbox_importer.discover_packages(root)[0]
            with self.assertRaises(mailbox_importer.PendingSync):
                mailbox_importer.parse_package(candidate)

    def test_multiple_attachments_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            write_ready_package(root, package_id, create_payload(package_id, attachment=True), b"pdf")
            (root / f"{package_id}.attachment.jpg").write_bytes(b"jpg")
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_invalid_attachment_filename_is_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            write_ready_package(root, package_id, create_payload(package_id))
            (root / f"{package_id}.attachment.").write_bytes(b"bad")
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_multiple_command_json_files_are_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            write_ready_package(root, package_id, create_payload(package_id))
            (root / f"{package_id}.done.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_unrelated_owner_files_are_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owner_file = root / "owner-not-a-package.pdf"
            owner_file.write_bytes(b"keep")
            self.assertEqual(mailbox_importer.discover_packages(root), [])
            self.assertEqual(owner_file.read_bytes(), b"keep")

    def test_ledger_is_indefinite_and_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = mailbox_importer.ProcessedLedger(root)
            package_id = str(uuid.uuid4())
            self.assertFalse(ledger.contains(package_id))
            ledger.record(package_id, "CREATE_EVENT", "applied")
            ledger.record(package_id, "CREATE_EVENT", "applied")
            self.assertTrue(ledger.contains(package_id))
            reloaded = mailbox_importer.ProcessedLedger(root)
            self.assertTrue(reloaded.contains(package_id))
            self.assertEqual(len(reloaded.records()), 1)
            self.assertEqual(reloaded.records()[0]["transport_id"], package_id)

    def test_journal_round_trip_and_restart_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = mailbox_importer.JournalStore(root)
            package_id = str(uuid.uuid4())
            journal.write(package_id, {"phase": "attachment_staged", "transport_id": package_id})
            self.assertEqual(mailbox_importer.JournalStore(root).load(package_id)["phase"], "attachment_staged")
            self.assertEqual(mailbox_importer.JournalStore(root).pending()[0]["transport_id"], package_id)

    def test_quarantine_removes_only_exact_package_and_keeps_unrelated_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            write_ready_package(root, package_id, {"bad": True})
            unrelated = root / "owner.txt"
            unrelated.write_text("keep", encoding="utf-8")
            candidate = mailbox_importer.discover_packages(root)[0]
            quarantine = mailbox_importer.quarantine_package(candidate, root / "blink", "malformed_json")
            self.assertTrue(quarantine.exists())
            self.assertFalse((root / f"{package_id}.event.json").exists())
            self.assertFalse((root / f"{package_id}.ready").exists())
            self.assertTrue(unrelated.exists())

    def test_stage_attachment_copies_bytes_to_local_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blink_root = root / "blink"
            package_id = str(uuid.uuid4())
            write_ready_package(root, package_id, create_payload(package_id, attachment=True), b"pdf")
            candidate = mailbox_importer.discover_packages(root)[0]
            parsed = mailbox_importer.parse_package(candidate)
            staged = mailbox_importer.stage_attachment(parsed, blink_root)
            self.assertEqual(staged.read_bytes(), b"pdf")
            self.assertTrue(staged.is_relative_to(blink_root / "mailbox" / "journal"))
