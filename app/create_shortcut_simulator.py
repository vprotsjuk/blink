"""Pure simulation of the logical Blink CREATE Shortcut contract.

This module deliberately has no iCloud, Shortcuts, watcher, or filesystem side
effects. It is a fast oracle for validation, payload shape, and transport names;
Apple-specific behavior remains a real Shortcut acceptance concern.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import re


TRANSPORT_ID_RE = re.compile(r"^[0-9]{14}-[0-9]{9}$")
INTEGER_RE = re.compile(r"^[0-9]+$")


@dataclass(frozen=True)
class AttachmentInput:
    original_filename: str
    is_folder: bool = False


@dataclass(frozen=True)
class CreateInput:
    title: str
    description: str
    start: str
    reminders: str
    blinker: str
    attention_level: str
    transport_id: str
    created_at: str
    attachments: tuple[AttachmentInput, ...] = ()


@dataclass(frozen=True)
class CreateSimulation:
    accepted: bool
    errors: tuple[str, ...]
    payload: dict | None
    output_names: tuple[str, ...]
    trace: tuple[str, ...] = ()


def _non_negative_integer(value: str, label: str) -> tuple[int | None, str | None]:
    if not isinstance(value, str) or not INTEGER_RE.fullmatch(value.strip()):
        return None, f"{label} must contain non-negative integer minutes"
    return int(value.strip()), None


def _native_blinker_number(value: str) -> tuple[int | None, str | None]:
    """Model Ask for Number followed by Round-to-Integer equality and >= 0."""
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None, "blinker must be a number"
    if not number.is_finite() or number != number.to_integral_value() or number < 0:
        return None, "blinker must be a non-negative integer minute value"
    return int(number), None


def _reminder_values(value: str) -> tuple[list[int] | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "reminders must contain at least one integer minute value"
    values = []
    for item in value.split(","):
        parsed, error = _non_negative_integer(item, "reminder")
        if error:
            return None, error
        values.append(parsed)
    return values, None


def simulate_create(request: CreateInput) -> CreateSimulation:
    errors: list[str] = []
    trace = ["Receive Shortcut Input"]

    if not isinstance(request.title, str) or not re.search(r"\S", request.title):
        errors.append("title is required and must not be blank")

    try:
        start = datetime.fromisoformat(request.start)
        if start.tzinfo is None or start.utcoffset() is None:
            errors.append("start must include an explicit UTC offset")
    except (TypeError, ValueError):
        errors.append("start must be an ISO-8601 date/time with an explicit UTC offset")

    if request.attention_level not in {"green", "yellow", "red"}:
        errors.append("attention_level must be green, yellow, or red")

    reminder_values, reminder_error = _reminder_values(request.reminders)
    if reminder_error:
        errors.append(reminder_error)

    blinker_value, blinker_error = _native_blinker_number(request.blinker)
    if blinker_error:
        errors.append(blinker_error)

    if not TRANSPORT_ID_RE.fullmatch(request.transport_id):
        errors.append("transport_id must be yyyyMMddHHmmss-<9-digit-random>")

    try:
        created_at = datetime.fromisoformat(request.created_at)
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            errors.append("created_at must include an explicit UTC offset")
    except (TypeError, ValueError):
        errors.append("created_at must be an ISO-8601 date/time with an explicit UTC offset")

    if len(request.attachments) > 1:
        errors.append("Blink accepts at most one attachment")
    if request.attachments and request.attachments[0].is_folder:
        errors.append("a folder is not an attachment")
    if request.attachments and not request.attachments[0].original_filename:
        errors.append("attachment must have a filename")

    if errors:
        return CreateSimulation(False, tuple(errors), None, (), tuple(trace))

    transfer_id = request.transport_id
    payload = {
        "version": 1,
        "type": "CREATE_EVENT",
        "transfer_id": transfer_id,
        "title": request.title,
        "description": request.description,
        "start": request.start,
        "reminder_intent": {"offsets_minutes_before": reminder_values},
        "attention_level": request.attention_level,
        "blinker_intent": {"minutes_before": blinker_value},
        "created_at": request.created_at,
    }
    output_names = [f"{transfer_id}.event.json"]
    if request.attachments:
        original = request.attachments[0].original_filename
        suffix = original.rsplit(".", 1)[-1].lower() if "." in original else ""
        basename = f"{transfer_id}.attachment.{suffix}" if suffix else f"{transfer_id}.attachment"
        payload["attachment"] = {
            "basename": basename,
            "original_filename": original,
        }
        output_names.append(basename)
    output_names.append(f"{transfer_id}.ready")
    trace.extend([
        "Title: Ask for Text -> Match \\S -> Stop on empty",
        "Description: Ask for optional Text -> Set variable",
        "Start: Ask for Date and Time -> Set variable",
        "Importance: Choose from Menu -> Menu Result",
        "Reminders: Split -> Repeat -> Match -> Get Numbers -> >= 0 -> Add",
        "Blinker: Ask for Number -> native integer validation",
        "Transport: Current Date -> Format -> Random -> TransferID",
        "Serialization: JSON Text -> Save event.json -> optional attachment -> Save .ready last",
    ])
    return CreateSimulation(
        True, (), json.loads(json.dumps(payload, ensure_ascii=False)),
        tuple(output_names), tuple(trace),
    )
