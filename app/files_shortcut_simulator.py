"""Pure simulation of the final Blink Files phone Shortcut."""

from dataclasses import dataclass
import re


PACKAGE_RE = re.compile(r"^blink-files-v1-([0-9a-f]{32})$")


@dataclass(frozen=True)
class FilesSimulation:
    accepted: bool
    errors: tuple[str, ...]
    payload: dict | None
    visible_files: tuple[str, ...]
    selected: str | None
    trace: tuple[str, ...] = ()


def simulate_files(value: str, *, view_files: tuple[str, ...], selected: str | None = None) -> FilesSimulation:
    trace = ["Receive Shortcut Input"]
    prefix = "blink-files-v1|"
    if not isinstance(value, str) or not value.startswith(prefix):
        return FilesSimulation(False, ("input must be blink-files-v1|<package-id>",), None, (), None, tuple(trace))
    package_id = value[len(prefix):]
    if PACKAGE_RE.fullmatch(package_id) is None:
        return FilesSimulation(False, ("PackageID is malformed",), None, (), None, tuple(trace))
    trace.extend(["Validate PackageID", "Dynamic path ToPhoneView/<PackageID>", "Get Contents of Folder"])
    visible = tuple(sorted(
        name for name in view_files
        if name not in {".ready"} and not name.endswith(".manifest.json")
        and name not in {".", ".."} and "/" not in name and "\\" not in name
    ))
    if not visible:
        return FilesSimulation(False, ("package contains no viewable files",), None, (), None, tuple(trace))
    trace.append("Choose from List")
    chosen = selected if selected is not None else (visible[0] if len(visible) == 1 else None)
    if chosen not in visible:
        return FilesSimulation(False, ("selected file is not in this package view",), None, visible, None, tuple(trace))
    trace.append("Quick Look selected item")
    return FilesSimulation(True, (), {"package_id": package_id, "selected": chosen}, visible, chosen, tuple(trace))
