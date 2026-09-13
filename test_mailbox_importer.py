import errno
import json
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

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


def done_payload(command_id: str, event_id: str) -> dict:
    return {
        "version": 1,
        "type": "DONE",
        "command_id": command_id,
        "event_id": event_id,
    }


class MailboxImporterTests(unittest.TestCase):
    def _agenda(self, root: Path, events: list[dict]) -> Path:
        path = root / "agenda.json"
        path.write_text(json.dumps({"version": 1, "events": events}), encoding="utf-8")
        return path

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

    def test_shortcuts_native_transport_id_is_accepted_for_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            transport_id = "20260912154532-482193775"
            (root / f"{transport_id}.done.json").write_text(
                json.dumps(done_payload(transport_id, "event-123")), encoding="utf-8"
            )
            (root / f"{transport_id}.ready").write_text("ready\n", encoding="utf-8")
            candidate = mailbox_importer.discover_packages(root)[0]
            parsed = mailbox_importer.parse_package(candidate)
            self.assertEqual(parsed.transport_id, transport_id)

    def test_shortcuts_native_transport_id_is_accepted_for_create_and_attachment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            transport_id = "20260912154532-482193775"
            write_ready_package(root, transport_id, create_payload(transport_id, attachment=True), b"pdf")
            candidate = mailbox_importer.discover_packages(root)[0]
            parsed = mailbox_importer.parse_package(candidate)
            self.assertEqual(parsed.transfer_id, transport_id)
            self.assertEqual(parsed.attachment_path.name, f"{transport_id}.attachment.pdf")

    def test_iCloud_resource_deadlock_while_staging_attachment_is_pending_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = "20260912154500-123456789"
            write_ready_package(root, package_id, create_payload(package_id, attachment=True), b"pdf")
            parsed = mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])
            with mock.patch.object(
                Path,
                "open",
                side_effect=OSError(errno.EDEADLK, "Resource deadlock avoided"),
            ):
                with self.assertRaises(mailbox_importer.PendingSync):
                    mailbox_importer.stage_attachment(parsed, root / "blink")

    def test_mailbox_iteration_keeps_pending_package_when_apply_hits_sync_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mailbox = root / "to_mac"
            mailbox.mkdir()
            agenda = self._agenda(root, [])
            package_id = "20260912154501-123456789"
            write_ready_package(mailbox, package_id, create_payload(package_id))
            command = mailbox_importer.ParsedCommand(
                kind="CREATE_EVENT",
                transport_id=package_id,
                transfer_id=package_id,
                title="Pending",
                description="",
                start="2026-09-13T09:00:00-07:00",
                reminder_offsets=(0,),
                attention_level="green",
                blinker_minutes_before=0,
            )
            with mock.patch.object(mailbox_importer, "parse_package", return_value=command), \
                 mock.patch.object(
                     mailbox_importer,
                     "apply_command",
                     side_effect=mailbox_importer.PendingSync("attachment bytes are still syncing"),
                 ):
                stats = mailbox_importer.process_mailbox_iteration(mailbox, root, agenda, max_packages=1)
            self.assertEqual(stats["pending"], 1)
            self.assertEqual(sorted(path.name for path in mailbox.iterdir()), sorted([
                f"{package_id}.event.json",
                f"{package_id}.ready",
            ]))

    def test_native_transport_id_requires_exact_shape_and_stem_ownership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = "20260912154532-482193775"
            invalid = (
                "..-abc", "2026-09-12-123", "abc-123", "20260912154532",
                "20260912154532-123", "20260912154532-123456789-extra",
            )
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer._validate_transport_id("../../abc", "transport_id")
            for value in invalid:
                (root / f"{value}.ready").write_text("ready", encoding="utf-8")
            (root / f"{valid}.ready").write_text("ready", encoding="utf-8")
            (root / f"{valid}.done.json").write_text(
                json.dumps(done_payload("20260912154533-482193775", "event-123")), encoding="utf-8"
            )
            (root / f"{valid}.attachment.pdf").write_bytes(b"pdf")
            candidates = mailbox_importer.discover_packages(root)
            self.assertEqual([candidate.transport_id for candidate in candidates], [valid])
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(candidates[0])

    def test_native_transport_id_duplicate_is_deduped_by_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agenda = self._agenda(root, [])
            transport_id = "20260912154532-482193775"
            command = mailbox_importer.ParsedCommand(
                kind="CREATE_EVENT", transport_id=transport_id, transfer_id=transport_id,
                title="Native", description="", start="2026-09-13T09:00:00-07:00",
                reminder_offsets=(0,), attention_level="green", blinker_minutes_before=0,
            )
            first = mailbox_importer.apply_command(command, agenda, root)
            second = mailbox_importer.apply_command(command, agenda, root)
            self.assertEqual(first["event_id"], second["event_id"])
            self.assertEqual(len(json.loads(agenda.read_text())["events"]), 1)

    def test_create_accepts_arbitrary_integer_reminders_and_blinker_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = "20260912194513-228316619"
            payload = create_payload(package_id)
            payload["reminder_intent"] = {"offsets_minutes_before": [17, 240, 3, 0, 17]}
            payload["blinker_intent"] = {"minutes_before": 240}
            write_ready_package(root, package_id, payload)
            parsed = mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])
            self.assertEqual(parsed.reminder_offsets, (240, 17, 3, 0))
            self.assertEqual(parsed.blinker_minutes_before, 240)

    def test_create_accepts_zero_blinker_and_empty_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = "20260912194754-657491603"
            payload = create_payload(package_id)
            payload["description"] = ""
            payload["reminder_intent"] = {"offsets_minutes_before": [3, 0]}
            payload["blinker_intent"] = {"minutes_before": 0}
            write_ready_package(root, package_id, payload)
            parsed = mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])
            self.assertEqual(parsed.reminder_offsets, (3, 0))
            self.assertEqual(parsed.blinker_minutes_before, 0)
            self.assertEqual(parsed.description, "")

    def test_create_rejects_invalid_minute_values_and_empty_title(self):
        invalid_values = [-1, 3.5, True, "3"]
        for field, values in (("reminder_intent", invalid_values), ("blinker_intent", invalid_values)):
            for value in values:
                with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    package_id = "20260912195000-123456789"
                    payload = create_payload(package_id)
                    if field == "reminder_intent":
                        payload[field] = {"offsets_minutes_before": [value]}
                    else:
                        payload[field] = {"minutes_before": value}
                    write_ready_package(root, package_id, payload)
                    with self.assertRaises(mailbox_importer.MalformedPackage):
                        mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = "20260912195001-123456789"
            payload = create_payload(package_id)
            payload["title"] = "   "
            write_ready_package(root, package_id, payload)
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_create_rejects_phone_owned_lifecycle_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = "20260912195002-123456789"
            payload = create_payload(package_id)
            payload["done"] = False
            payload["done_at"] = None
            payload["blinker_minutes_before"] = 3
            write_ready_package(root, package_id, payload)
            with self.assertRaises(mailbox_importer.MalformedPackage):
                mailbox_importer.parse_package(mailbox_importer.discover_packages(root)[0])

    def test_ready_missing_json_is_pending_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = str(uuid.uuid4())
            (root / f"{package_id}.ready").write_text("ready\n", encoding="utf-8")
            candidate = mailbox_importer.discover_packages(root)[0]
            with self.assertRaises(mailbox_importer.PendingSync):
                mailbox_importer.parse_package(candidate)

    def test_iCloud_resource_deadlock_while_reading_json_is_pending_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_id = "20260912214500-123456789"
            write_ready_package(root, package_id, create_payload(package_id))
            candidate = mailbox_importer.discover_packages(root)[0]
            with mock.patch.object(
                Path,
                "read_text",
                side_effect=OSError(errno.EDEADLK, "Resource deadlock avoided"),
            ):
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

    def test_done_apply_is_idempotent_and_uses_canonical_recurrence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event = {
                "id": "event-recurring",
                "title": "Weekly",
                "start": "2026-09-10T09:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
                "requires_done": True,
                "done": False,
                "done_at": None,
                "recurrence": {"mode": "weekly_fixed", "weekday": 4, "time": "09:00"},
            }
            agenda = self._agenda(root, [event])
            command_id = str(uuid.uuid4())
            candidate_root = root / "mailbox"
            candidate_root.mkdir()
            (candidate_root / f"{command_id}.done.json").write_text(
                json.dumps(done_payload(command_id, event["id"])), encoding="utf-8"
            )
            (candidate_root / f"{command_id}.ready").write_text("ready\n", encoding="utf-8")
            command = mailbox_importer.parse_package(mailbox_importer.discover_packages(candidate_root)[0])
            now = datetime(2026, 9, 12, 10, tzinfo=timezone.utc)
            first = mailbox_importer.apply_command(command, agenda, root, now=now)
            second = mailbox_importer.apply_command(command, agenda, root, now=now)
            document = json.loads(agenda.read_text(encoding="utf-8"))
            self.assertEqual(first["result"], "applied")
            self.assertEqual(second["result"], "applied")
            self.assertEqual(len(document["events"]), 2)
            self.assertEqual(sum(event.get("done") is True for event in document["events"]), 1)
            self.assertEqual(len(mailbox_importer.ProcessedLedger(root).records()), 1)

    def test_done_stale_is_successful_noop_and_busy_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agenda = self._agenda(root, [])
            command_id = str(uuid.uuid4())
            command = mailbox_importer.ParsedCommand(
                kind="DONE", transport_id=command_id, event_id="missing"
            )
            result = mailbox_importer.apply_command(command, agenda, root)
            self.assertEqual(result["result"], "stale_event")
            busy_command = mailbox_importer.ParsedCommand(
                kind="DONE", transport_id=str(uuid.uuid4()), event_id="missing"
            )
            lock = root / "agenda.lock"
            with mailbox_importer.agenda_lock(lock):
                busy = mailbox_importer.apply_command(busy_command, agenda, root, blocking=False)
            self.assertEqual(busy["result"], "busy")

    def test_done_from_different_command_against_done_event_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agenda = self._agenda(
                root,
                [{"id": "done", "title": "Done", "start": "2026-09-10T09:00:00-07:00", "done": True}],
            )
            command = mailbox_importer.ParsedCommand(
                kind="DONE", transport_id=str(uuid.uuid4()), event_id="done"
            )
            result = mailbox_importer.apply_command(command, agenda, root)
            self.assertEqual(result["result"], "noop_done")
            self.assertEqual(len(json.loads(agenda.read_text())["events"]), 1)

    def test_create_generates_mac_id_persists_provenance_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agenda = self._agenda(root, [{"id": "keep", "title": "Keep"}])
            mailbox = root / "mailbox"
            mailbox.mkdir()
            transfer_id = str(uuid.uuid4())
            write_ready_package(mailbox, transfer_id, create_payload(transfer_id, attachment=True), b"pdf")
            command = mailbox_importer.parse_package(mailbox_importer.discover_packages(mailbox)[0])
            result = mailbox_importer.apply_command(command, agenda, root)
            self.assertEqual(result["result"], "applied")
            event_id = result["event_id"]
            self.assertTrue(event_id.startswith("event-"))
            self.assertNotEqual(event_id, transfer_id)
            document = json.loads(agenda.read_text(encoding="utf-8"))
            created = next(event for event in document["events"] if event["id"] == event_id)
            self.assertEqual(created["mailbox_transfer_id"], transfer_id)
            self.assertTrue(created["enabled"])
            self.assertTrue(created["requires_done"])
            self.assertFalse(created["done"])
            self.assertIsNone(created["recurrence"])
            self.assertEqual(created["attachments"]["count"], 1)
            owner = root / "event_data" / "attachments" / event_id
            self.assertEqual([path.name for path in owner.iterdir()], ["contract.pdf"])
            duplicate = mailbox_importer.apply_command(command, agenda, root)
            self.assertEqual(duplicate["result"], "applied")
            self.assertEqual(len(json.loads(agenda.read_text())["events"]), 2)

    def test_create_commit_before_ledger_repairs_from_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agenda = self._agenda(root, [])
            transfer_id = str(uuid.uuid4())
            command = mailbox_importer.ParsedCommand(
                kind="CREATE_EVENT", transport_id=transfer_id, transfer_id=transfer_id,
                title="Recovered", description="", start="2026-09-13T09:00:00-07:00",
                reminder_offsets=(0,), attention_level="green", blinker_minutes_before=0,
            )
            first = mailbox_importer.apply_command(command, agenda, root, record_ledger=False)
            self.assertEqual(first["result"], "applied")
            self.assertFalse(mailbox_importer.ProcessedLedger(root).contains(transfer_id))
            second = mailbox_importer.apply_command(command, agenda, root)
            self.assertEqual(second["event_id"], first["event_id"])
            self.assertTrue(mailbox_importer.ProcessedLedger(root).contains(transfer_id))
            self.assertEqual(len(json.loads(agenda.read_text())["events"]), 1)

    def test_recover_pending_journal_cleans_orphan_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            transfer_id = str(uuid.uuid4())
            staging = root / "mailbox" / "journal" / "staging" / transfer_id
            staging.mkdir(parents=True)
            (staging / "file.pdf").write_bytes(b"orphan")
            mailbox_importer.JournalStore(root).write(
                transfer_id, {"phase": "attachment_staged", "kind": "CREATE_EVENT"}
            )
            mailbox_importer.recover_pending_transactions(root)
            self.assertFalse(staging.exists())

    def test_bounded_mailbox_iteration_applies_and_cleans_exact_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mailbox = root / "to_mac"
            mailbox.mkdir()
            agenda = self._agenda(root, [])
            transfer_id = str(uuid.uuid4())
            write_ready_package(mailbox, transfer_id, create_payload(transfer_id))
            stats = mailbox_importer.process_mailbox_iteration(mailbox, root, agenda, max_packages=1)
            self.assertEqual(stats["applied"], 1)
            self.assertEqual(list(mailbox.iterdir()), [])
