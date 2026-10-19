r"""Qt QSettings INI array dialect parser.

ModOrganizer.ini [customExecutables] uses Qt's array serialization:
    [customExecutables]
    size=2
    1\title=xEdit
    1\binary=<PATH_TO_XEDIT>/xEdit.exe
    1\arguments=-fo4
    2\title=LOOT

configparser treats backslash keys poorly for this dialect and PyQt6.QSettings
is too heavy for broker-side unit tests. This parser walks the section line by
line and extracts the array fields directly.
"""

from __future__ import annotations

from pathlib import Path


_BOOL_KEYS = {"ownicon", "hide", "toolbar", "minimizeToSystemTray"}


def parse_custom_executables(ini_path: Path) -> list[dict]:
    """Parse Qt QSettings array entries under [customExecutables]."""

    if not ini_path.exists():
        return []

    lines = ini_path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_section = False
    section_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            if in_section:
                break
            if stripped == "[customExecutables]":
                in_section = True
            continue
        if in_section and stripped and "=" in stripped:
            section_lines.append(stripped)

    if not section_lines:
        return []

    flat: dict[str, str] = {}
    for line in section_lines:
        key, _, value = line.partition("=")
        flat[key.strip()] = value

    try:
        size = int(flat.get("size", "0"))
    except ValueError:
        size = 0

    if size == 0:
        return []

    entries: list[dict] = []
    for index in range(1, size + 1):
        index_prefix = f"{index}\\"
        entry: dict = {}
        for key, value in flat.items():
            if not key.startswith(index_prefix):
                continue
            sub_key = key[len(index_prefix) :]
            if sub_key in _BOOL_KEYS:
                entry[sub_key] = value.strip().lower() == "true"
            else:
                entry[sub_key] = value
        if entry.get("title"):
            entries.append(entry)

    return entries


def _strip_bytearray(value: str | None) -> str:
    """Remove Qt @ByteArray(...) / @QString(...) wrappers if present."""

    if not value:
        return value or ""
    value = value.strip()
    for prefix in ("@ByteArray(", "@QString("):
        if value.startswith(prefix) and value.endswith(")"):
            return value[len(prefix) : -1]
    return value


def _escape_backslash_key(key: str) -> str:
    """QSettings writes '1\\title' as the literal key text."""
    return key.replace("\\", "\\\\")


def _write_custom_executables_section(lines: list[str], entries: list[dict]) -> list[str]:
    """Rebuild the INI lines, replacing [customExecutables] with the new entries."""

    new_section_lines: list[str] = ["[customExecutables]", f"size={len(entries)}"]
    for index, entry in enumerate(entries, start=1):
        prefix = f"{index}\\"
        for sub_key in ("title", "binary", "arguments", "workingDirectory", "steamAppID", "ownicon", "hide", "toolbar", "minimizeToSystemTray"):
            value = entry.get(sub_key)
            if value is None:
                continue
            if sub_key in _BOOL_KEYS:
                value_str = "true" if bool(value) else "false"
            else:
                value_str = str(value)
            # Strip any stale @ByteArray wrapper from the value we are about to write.
            value_str = _strip_bytearray(value_str)
            new_section_lines.append(f"{prefix}{sub_key}={value_str}")

    output: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            if in_section:
                # End of the previous customExecutables section: insert replacement and continue.
                output.extend(new_section_lines)
                in_section = False
            if stripped == "[customExecutables]":
                in_section = True
                continue
        if in_section:
            continue
        output.append(line)

    if in_section:
        # Section was at EOF.
        output.extend(new_section_lines)

    return output


def upsert_custom_executable(ini_path: Path, entry: dict) -> dict:
    """Add or update a custom executable entry in ModOrganizer.ini by title.

    Returns the updated list of custom executables.
    """

    ini_path = Path(ini_path)
    lines = ini_path.read_text(encoding="utf-8", errors="replace").splitlines() if ini_path.exists() else []
    entries = parse_custom_executables(ini_path)

    title = entry.get("title")
    if not title:
        raise ValueError("executable entry must have a title")

    for existing in entries:
        if existing.get("title") == title:
            existing.update(entry)
            break
    else:
        entries.append(dict(entry))

    new_lines = _write_custom_executables_section(lines, entries)
    ini_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"executables": entries, "count": len(entries)}
