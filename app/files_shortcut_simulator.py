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


@dataclass(frozen=True)
class GetFileBoundarySimulation:
    accepted: bool
    resolved_path: str
    object_type: str | None
    contents_type: str | None
    choose_input: tuple[str, ...] | None


def simulate_get_file_boundary(
    *,
    base_path: str,
    package_id: str,
    package_files: tuple[str, ...],
    path_binding: str,
) -> GetFileBoundarySimulation:
    """Model the typed boundary before the Files chooser.

    This deliberately separates path construction from the later chooser logic.
    A Magic Variable and a literal full package path both resolve to a Folder;
    an unresolved ``PackageID`` text token remains a non-existent path.
    """
    if path_binding == "literal-full-package-path":
        resolved_path = f"{base_path}/{package_id}/"
    elif path_binding == "magic-variable":
        resolved_path = f"{base_path}/{package_id}/"
    elif path_binding == "literal-packageid-token":
        resolved_path = f"{base_path}/PackageID/"
    else:
        raise ValueError(f"unsupported path binding: {path_binding}")

    expected_path = f"{base_path}/{package_id}/"
    if resolved_path != expected_path:
        return GetFileBoundarySimulation(False, resolved_path, None, None, None)
    files = tuple(package_files)
    return GetFileBoundarySimulation(True, resolved_path, "Folder", "List[File]", files)


def simulate_files(value: str, *, view_files: tuple[str, ...], selected: str | None = None) -> FilesSimulation:
    trace = [
        "Receive Apps and 18 more from Nowhere (Continue if no input)",
        "Get text from Shortcut Input",
        "Comment (build marker)",
    ]
    prefix = "blink-files-v1|"
    if not isinstance(value, str) or not value.startswith(prefix):
        return FilesSimulation(False, ("input must be blink-files-v1|<package-id>",), None, (), None, tuple(trace))
    package_id = value[len(prefix):]
    if PACKAGE_RE.fullmatch(package_id) is None:
        return FilesSimulation(False, ("PackageID is malformed",), None, (), None, tuple(trace))
    trace.extend([
        "Match blink-files-v1|<32-hex-package-id>",
        "If match is empty -> Stop this shortcut",
        "Split Text by |",
        "Get Item at Index 2",
        "Set PackageID",
        "Get file from Shortcuts at Blink_Acceptance/ToPhoneView/<PackageID>/",
        "Get contents of File",
        "Set AllFiles to Folder Contents",
    ])
    visible = tuple(sorted(
        name for name in view_files
        if name not in {".ready"} and not name.endswith(".manifest.json")
        and name not in {".", ".."} and "/" not in name and "\\" not in name
    ))
    if not visible:
        return FilesSimulation(False, ("package contains no viewable files",), None, (), None, tuple(trace))
    trace.append("Choose from AllFiles")
    chosen = selected if selected is not None else (visible[0] if len(visible) == 1 else None)
    if chosen not in visible:
        return FilesSimulation(False, ("selected file is not in this package view",), None, visible, None, tuple(trace))
    trace.extend([
        "Show Selected Item in Quick Look",
        "Stop and output Quick Look",
    ])
    return FilesSimulation(True, (), {"package_id": package_id, "selected": chosen}, visible, chosen, tuple(trace))
