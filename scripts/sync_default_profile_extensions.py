#!/usr/bin/env python3
"""Mirror default-profile skills/plugins into every named profile.

The default profile is authoritative. Only changed nodes are copied and
target-only nodes are deleted, so one metadata change stays inexpensive.
No configuration, credentials, memory, sessions, or cron state are copied.
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import uuid
from pathlib import Path


HOME = Path(__file__).resolve().parent.parent
PROFILE_ROOT = HOME / "profiles"
SYNC_ROOTS = ("skills", "plugins")
IGNORED_DIRECTORY_NAMES = {".git"}


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def node_signature(path: Path) -> tuple[str, int, int] | tuple[str, str]:
    """Return stable metadata for a filesystem node."""
    if path.is_symlink():
        return ("L", os.readlink(path))
    if path.is_dir():
        return ("D", 0, 0)
    stat = path.stat()
    return ("F", stat.st_size, stat.st_mtime_ns)


def tree_manifest(root: Path) -> dict[str, tuple[str, int, int] | tuple[str, str]]:
    """Describe synchronized content while excluding repository metadata."""
    if not path_exists(root):
        return {}
    manifest = {".": node_signature(root)}
    if not root.is_dir() or root.is_symlink():
        return manifest
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories.sort(key=str.casefold)
        files.sort(key=str.casefold)
        directories[:] = [name for name in directories if name not in IGNORED_DIRECTORY_NAMES]
        current_path = Path(current)
        for name in [*directories, *files]:
            item = current_path / name
            manifest[item.relative_to(root).as_posix()] = node_signature(item)
    return manifest


def make_writable(path: Path) -> None:
    """Clear Windows' read-only bit without changing timestamps."""
    if path_exists(path) and not path.is_symlink():
        os.chmod(path, path.stat().st_mode | stat.S_IWRITE)


def remove_readonly(function, path: str, _exc_info: object) -> None:
    """Retry shutil removal after clearing a Git object's read-only bit."""
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    function(path)


def remove_path(path: Path) -> None:
    if not path_exists(path):
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, onerror=remove_readonly)
    else:
        try:
            path.unlink()
        except PermissionError:
            make_writable(path)
            path.unlink()


def ignored_directories(root: Path) -> list[Path]:
    """Find nested VCS metadata that is not deployable extension content."""
    ignored: list[Path] = []
    if not root.is_dir():
        return ignored
    for current, directories, _files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        matches = [name for name in directories if name in IGNORED_DIRECTORY_NAMES]
        ignored.extend(current_path / name for name in matches)
        directories[:] = [name for name in directories if name not in IGNORED_DIRECTORY_NAMES]
    return ignored


def topmost_paths(paths: set[str]) -> list[str]:
    """Remove descendants when an ancestor is already selected."""
    selected: list[str] = []
    for relative in sorted(paths, key=lambda item: (item.count("/"), item.casefold())):
        if not any(relative == parent or relative.startswith(f"{parent}/") for parent in selected):
            selected.append(relative)
    return selected


def copy_source_node(source: Path, target: Path) -> None:
    """Copy one non-directory node through a same-volume temporary path."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.sync-{uuid.uuid4().hex}"
    try:
        if source.is_symlink():
            os.symlink(os.readlink(source), temporary, target_is_directory=source.is_dir())
        else:
            shutil.copy2(source, temporary, follow_symlinks=False)
        make_writable(target)
        make_writable(temporary)
        os.replace(temporary, target)
    finally:
        remove_path(temporary)


def mirror_root(
    source: Path,
    source_manifest: dict[str, tuple[str, int, int] | tuple[str, str]],
    target_profile: Path,
) -> None:
    """Incrementally make one target root exactly match the source root."""
    target = target_profile / source.name
    for ignored in ignored_directories(target):
        remove_path(ignored)
    target_manifest = tree_manifest(target)
    source_keys = set(source_manifest) - {"."}
    target_keys = set(target_manifest) - {"."}
    common = source_keys & target_keys
    target_only = target_keys - source_keys
    type_mismatches = {
        relative
        for relative in common
        if source_manifest[relative][0] != target_manifest[relative][0]
    }
    removals = topmost_paths(target_only | type_mismatches)

    for relative in sorted(removals, key=lambda item: (item.count("/"), item.casefold()), reverse=True):
        remove_path(target / relative)

    target.mkdir(parents=True, exist_ok=True)
    for relative in sorted(source_keys, key=lambda item: (item.count("/"), item.casefold())):
        source_node = source / relative
        target_node = target / relative
        signature = source_manifest[relative]
        if signature[0] == "D":
            target_node.mkdir(parents=True, exist_ok=True)
        elif target_manifest.get(relative) != signature or relative in type_mismatches:
            copy_source_node(source_node, target_node)

    if tree_manifest(target) != source_manifest or ignored_directories(target):
        raise RuntimeError(f"post-mirror verification failed: {target}")


def target_profiles() -> list[Path]:
    if not PROFILE_ROOT.is_dir():
        return []
    return sorted(
        (item for item in PROFILE_ROOT.iterdir() if item.is_dir()),
        key=lambda item: item.name.casefold(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report drift without changing targets.")
    args = parser.parse_args()

    if not PROFILE_ROOT.is_dir():
        print(f"ERROR: profile root is missing: {PROFILE_ROOT}", file=sys.stderr)
        return 2

    sources: dict[str, tuple[Path, dict[str, tuple[str, int, int] | tuple[str, str]]]] = {}
    for root_name in SYNC_ROOTS:
        source = HOME / root_name
        if not source.is_dir():
            print(f"ERROR: source root is missing: {source}", file=sys.stderr)
            return 2
        sources[root_name] = (source, tree_manifest(source))

    profiles = target_profiles()
    counts = {"added": 0, "replaced": 0, "unchanged": 0}
    failures: list[str] = []

    for profile in profiles:
        actions: list[str] = []
        for root_name, (source, source_manifest) in sources.items():
            target = profile / root_name
            if tree_manifest(target) == source_manifest and not ignored_directories(target):
                counts["unchanged"] += 1
                actions.append(f"{root_name}=unchanged")
                continue

            action = "replaced" if path_exists(target) else "added"
            if not args.dry_run:
                try:
                    mirror_root(source, source_manifest, profile)
                    actions.append(f"{root_name}={action}")
                except Exception as exc:
                    failures.append(f"{profile.name}/{root_name}: {exc}")
                    actions.append(f"{root_name}=ERROR")
                    continue
            else:
                actions.append(f"{root_name}=would-{action}")
            counts[action] += 1
        print(f"{profile.name}: {'; '.join(actions)}")

    mode = "DRY-RUN" if args.dry_run else "SYNC"
    print(
        f"{mode} complete: profiles={len(profiles)} added={counts['added']} "
        f"replaced={counts['replaced']} unchanged={counts['unchanged']} failures={len(failures)}"
    )
    for failure in failures:
        print(f"ERROR: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())