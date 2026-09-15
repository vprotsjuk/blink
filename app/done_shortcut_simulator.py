"""Pure simulation of the three-block Blink DONE phone Shortcut."""

from dataclasses import dataclass
import json
import re


TRANSPORT_ID_RE = re.compile(r"^[0-9]{14}-[0-9]{9}$")
DONE_INPUT_RE = re.compile(r"^blink-done-v1\|(.+)$")


@dataclass(frozen=True)
class DoneSimulation:
    accepted: bool
    errors: tuple[str, ...]
    payload: dict | None
    output_names: tuple[str, ...]
    event_id: str | None
    trace: tuple[str, ...] = ()


def simulate_done(value: str, *, command_id: str = "20260101000000-100000000") -> DoneSimulation:
    trace = ["Receive Shortcut Input"]
    match = DONE_INPUT_RE.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        return DoneSimulation(False, ("input must be blink-done-v1|<event-id>",), None, (), None, tuple(trace))
    event_id = match.group(1)
    if not event_id or "|" in event_id:
        return DoneSimulation(False, ("event_id is malformed",), None, (), None, tuple(trace))
    trace.append("Validate literal blink-done-v1|<event-id>")
    if not TRANSPORT_ID_RE.fullmatch(command_id):
        return DoneSimulation(False, ("command_id must be yyyyMMddHHmmss-<9-digit-random>",), None, (), event_id, tuple(trace))
    trace.append("Current Date -> Format -> Random -> command_id")
    payload = {
        "version": 1,
        "type": "DONE",
        "command_id": command_id,
        "event_id": event_id,
    }
    trace.append("JSON Text -> Save .done.json -> Save .ready last")
    return DoneSimulation(
        True, (), json.loads(json.dumps(payload)),
        (f"{command_id}.done.json", f"{command_id}.ready"), event_id, tuple(trace),
    )
