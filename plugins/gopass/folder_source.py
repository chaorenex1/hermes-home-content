"""``gopass_folder`` secret source — bulk injection of one store folder.

Every entry under ``secrets.gopass_folder.folder`` becomes an env var named by
the entry's basename, so a store folder ``hermes/`` holding
``hermes/OPENAI_API_KEY`` injects ``OPENAI_API_KEY``::

    secrets:
      gopass_folder:
        enabled: true
        folder: hermes

Bulk shape: explicit mapped sources (``gopass``, 1Password, ...) outrank it on
contested vars regardless of configuration order. One ``ls`` plus one
``show`` per entry; entry values come from the password field (first line).
"""

from __future__ import annotations

from pathlib import Path

from agent.secret_sources.base import (
    ErrorKind,
    FetchResult,
    SecretSource,
    coerce_float,
    is_valid_env_name,
)

from .cli import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    GopassCli,
    find_gopass,
    missing_binary_error,
)

__all__ = ["GopassFolderSource", "entries_from_listing", "valid_folder"]


def valid_folder(folder: str) -> bool:
    """A relative gopass folder path: no leading slash, no backslashes, no
    empty or dot segments (gopass paths are POSIX-shaped)."""
    if not folder or "\\" in folder or folder.startswith("/"):
        return False
    return all(segment not in ("", ".", "..") for segment in folder.split("/"))


def entries_from_listing(stdout: str, folder: str) -> tuple[dict[str, str], list[str]]:
    """``(env-name -> entry path, warnings)`` from ``gopass ls --flat`` output.

    Only paths under ``folder/`` count; the basename is the env-var name.
    Processing is deterministic (sorted paths) and the first path wins a
    basename collision.

    gopass on Windows renders the *requested prefix's* separators as
    backslashes in ``--flat`` output (``ls --flat hermes/live`` lists
    ``hermes\\live/PLAIN``), so every line is normalized to forward slashes
    before matching and before being used as a reference.
    """
    entries: dict[str, str] = {}
    warnings: list[str] = []
    prefix = folder + "/"
    lines = {line.strip().replace("\\", "/")
             for line in stdout.replace("\r\n", "\n").split("\n") if line.strip()}
    for path in sorted(lines):
        if not path.startswith(prefix):
            continue
        name = path[len(prefix):].rsplit("/", 1)[-1]
        if not is_valid_env_name(name):
            warnings.append(f"Skipping {path!r}: basename {name!r} is not a valid env-var name")
            continue
        if name in entries:
            warnings.append(f"Skipping {path!r}: env var {name} is already supplied by "
                            f"{entries[name]!r} (first path wins)")
            continue
        entries[name] = path
    return entries, warnings


class GopassFolderSource(SecretSource):
    """gopass as a registered **bulk** source: one folder of entries, every
    basename an env-var name."""

    name = "gopass_folder"
    label = "gopass folder"
    shape = "bulk"
    override_existing_default = True
    remediation_hints = {
        ErrorKind.NOT_CONFIGURED: "Set secrets.gopass_folder.folder to an existing gopass folder "
                                  "(e.g. hermes) — `gopass ls` shows your store's layout.",
        ErrorKind.BINARY_MISSING: "Install the gopass CLI (https://www.gopass.pw/) or set "
                                  "secrets.gopass_folder.binary_path to its absolute location.",
        ErrorKind.AUTH_FAILED: "gopass could not decrypt — unlock the GPG key in your agent "
                               "(run `gopass show <entry>` once in a terminal).",
        ErrorKind.REF_INVALID: "The configured folder was not found — check "
                               "secrets.gopass_folder.folder against `gopass ls`.",
    }

    def config_schema(self) -> dict:
        return {
            "enabled": {"description": "Master switch", "default": False},
            "folder": {"description": "gopass folder whose entry basenames become env-var names",
                       "default": ""},
            "binary_path": {"description": "Pin the gopass binary (empty = resolve via PATH)",
                            "default": ""},
            "config_path": {"description": "Pin GOPASS_CONFIG for the child "
                                           "(empty = gopass default)",
                            "default": ""},
            "sync": {"description": "Allow gopass git auto-sync during reads "
                                    "(default false: --nosync keeps startup offline)",
                     "default": False},
            "command_timeout_seconds": {"description": "Timeout for one gopass invocation",
                                        "default": DEFAULT_COMMAND_TIMEOUT_SECONDS},
            "override_existing": {"description": "Resolved values overwrite .env/shell values",
                                  "default": True},
        }

    def fetch(self, cfg: dict, home_path: Path) -> FetchResult:
        """List the folder, then read each entry. Per-entry failures become
        warnings; an all-failed fetch becomes an error carrying the first
        failure's kind."""
        cfg = cfg if isinstance(cfg, dict) else {}
        result = FetchResult()

        folder = str(cfg.get("folder") or "").strip().strip("/")
        if not folder:
            return result.fail(
                "secrets.gopass_folder.enabled is true but secrets.gopass_folder.folder is empty.  "
                "Set it to a gopass folder (e.g. hermes).",
                ErrorKind.NOT_CONFIGURED)
        if not valid_folder(folder):
            return result.fail(
                f"secrets.gopass_folder.folder {str(cfg.get('folder'))!r} is not a valid "
                "gopass folder path.",
                ErrorKind.NOT_CONFIGURED)

        binary_path = str(cfg.get("binary_path") or "")
        binary = find_gopass(binary_path)
        result.binary_path = binary
        if binary is None:
            return result.fail(missing_binary_error(binary_path, self.name),
                               ErrorKind.BINARY_MISSING)

        cli = GopassCli(binary=binary,
                        sync=bool(cfg.get("sync", False)),
                        timeout=coerce_float(cfg.get("command_timeout_seconds"),
                                             DEFAULT_COMMAND_TIMEOUT_SECONDS),
                        config_path=str(cfg.get("config_path") or ""))

        listing = cli.list_flat(folder)
        if not listing.ok:
            return result.fail(f"could not list gopass folder {folder!r}: {listing.message}",
                               listing.kind)

        entries, warnings = entries_from_listing(listing.stdout, folder)
        result.warnings.extend(warnings)
        if not entries:
            result.warnings.append(
                f"no usable entries under gopass folder {folder!r}; nothing to apply")
            return result

        failures: list[tuple[ErrorKind, str]] = []
        for name in sorted(entries):
            path = entries[name]
            outcome = cli.show(path)
            if not outcome.ok:
                failures.append((outcome.kind or ErrorKind.INTERNAL, outcome.message))
                result.warnings.append(f"{name}: {outcome.message}")
                continue
            value = outcome.stdout.rstrip("\r\n")
            if not value.strip():
                result.warnings.append(
                    f"{name}: gopass returned an empty value for {path!r} — not applied "
                    "(an empty value must not replace a working credential).")
                continue
            result.secrets[name] = value

        if failures and not result.secrets:
            return result.fail(
                f"every entry under gopass folder {folder!r} failed ({len(failures)}); "
                f"first error — {failures[0][1]}",
                failures[0][0])
        return result
