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


def simulate_flat_root_files(
    value: str,
    *,
    root_files: tuple[str, ...],
    selected: str | None = None,
) -> FilesSimulation:
    """Simulate the preserved Stage2 WORK flat-root Shortcut tree.

    This mirrors its physical action groups: acquire the shared ``ToPhone``
    folder, require one ready marker and manifest, filter attachment files by
    the package transport prefix, then use the chooser/Quick Look pair.
    """
    trace = [
        "Receive Apps and 18 more from Nowhere (Continue if no input)",
        "Get text from Shortcut Input",
        "Match blink-files-v1|<32-hex-package-id>",
        "If match is empty -> Stop this shortcut",
    ]
    prefix = "blink-files-v1|"
    if not isinstance(value, str) or not value.startswith(prefix):
        return FilesSimulation(False, ("input must be blink-files-v1|<package-id>",), None, (), None, tuple(trace))
    package_id = value[len(prefix):]
    if PACKAGE_RE.fullmatch(package_id) is None:
        return FilesSimulation(False, ("PackageID is malformed",), None, (), None, tuple(trace))
    trace.extend([
        "Split Shortcut Input by |",
        "Get Item at Index 2",
        "Set PackageID",
        "Get file from Shortcuts at Blink_Acceptance/ToPhone",
        "Get contents of File",
        "Set AllFiles to Folder Contents",
        "Filter AllFiles where Name is PackageID.ready",
    ])
    ready = tuple(name for name in root_files if name == f"{package_id}.ready")
    if len(ready) != 1:
        return FilesSimulation(False, ("package must have exactly one ready marker",), None, (), None, tuple(trace))
    trace.append("Filter AllFiles where Name is PackageID.manifest.json")
    manifests = tuple(name for name in root_files if name == f"{package_id}.manifest.json")
    if len(manifests) != 1:
        return FilesSimulation(False, ("package must have exactly one manifest",), None, (), None, tuple(trace))
    attachment_prefix = f"{package_id}__"
    trace.extend([
        "Filter AllFiles where Name begins with PackageID__",
        "Set Attachments to Files",
        "Count Items in Attachments",
        "Set AttachmentCount to Count",
    ])
    visible = tuple(sorted(
        (name for name in root_files if name.startswith(attachment_prefix)),
        key=str.casefold,
    ))
    if not visible:
        return FilesSimulation(False, ("package contains no attachments",), None, (), None, tuple(trace))
    trace.extend([
        "If AttachmentCount is 0 -> Stop this shortcut",
        "Choose from Attachments",
        "Show Selected Item in Quick Look",
    ])
    chosen = selected if selected is not None else (visible[0] if len(visible) == 1 else None)
    if chosen not in visible:
        return FilesSimulation(False, ("selected file is not in this package",), None, visible, None, tuple(trace))
    return FilesSimulation(True, (), {"package_id": package_id, "selected": chosen}, visible, chosen, tuple(trace))
