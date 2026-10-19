"""gopass CLI plumbing shared by the plugin's two secret sources.

One place owns binary discovery, the allowlisted child environment, the
invocation shape, exit-code classification and the one-shot legacy-flag
fallback, so both sources behave identically.

Behavior verified against gopass 1.17.3 on Windows (upstream's exit-code table
is declared stable; observed behavior wins where they differ):

- ``show --password`` prints the password field (first line) and no trailing
  newline; ``show <entry> <key>`` prints one structured key's value.
- A missing entry or missing key exits 11 with "not in the password store" /
  "key not found" on stderr (the docs table says 10).
- An uninitialized store exits 6; ``ls --flat <missing>`` exits 10.
- An unknown flag exits 1 with "Incorrect Usage: flag provided but not defined".
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from agent.secret_sources.base import ErrorKind, run_secret_cli

__all__ = [
    "DEFAULT_COMMAND_TIMEOUT_SECONDS",
    "GopassCli",
    "Outcome",
    "classify_failure",
    "find_gopass",
    "missing_binary_error",
]

DEFAULT_COMMAND_TIMEOUT_SECONDS = 30.0

# Passed to the gopass child on top of run_secret_cli()'s base allowlist
# (PATH/HOME/locales/...). Location and behavior knobs only — decryption goes
# through the user's GPG agent, so no secret value travels in any of these.
_CHILD_ENV_ALLOWLIST: tuple[str, ...] = (
    "GNUPGHOME",          # non-default GnuPG home
    "GOPASS_CONFIG",      # explicit gopass config file
    "GOPASS_HOMEDIR",     # directory containing gopass's .config tree
    "GOPASS_GPG_BINARY",  # non-default gpg binary
    "GOPASS_GPG_OPTS",    # extra gpg flags
    "GOPASS_SSH_DIR",
    "APPDATA",            # Windows: default config location
    "LOCALAPPDATA",       # Windows: default data location
    "GIT_SSH_COMMAND", "GIT_SSH", "SSH_AUTH_SOCK",  # remote sync only
)

# Forced on every invocation: no desktop notifications, no reminder banners,
# no update-check network calls. run_secret_cli already sets NO_COLOR=1.
_FORCED_ENV = {
    "GOPASS_NO_NOTIFY": "1",
    "GOPASS_NO_REMINDER": "1",
    "CHECKPOINT_DISABLE": "1",
}

# With sync allowed, a git subprocess must fail fast instead of opening a
# credential dialog: startup runs in non-TTY contexts.
_SYNC_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}

_USAGE_ERROR_MARKERS = (
    "flag provided but not defined",
    "unknown flag",
    "unknown shorthand",
    "incorrect usage",
)
_NOT_FOUND_MARKERS = ("not found", "not in the password store")
_DECRYPT_MARKERS = ("could not be decrypted", "decryption failed", "no secret key")


def find_gopass(binary_path: str = "") -> Optional[Path]:
    """Resolve a usable gopass binary, or None.

    A pinned ``binary_path`` is used verbatim — pinned-but-missing returns None
    rather than silently falling back to PATH. Elsewhere PATH is searched
    (``shutil.which`` resolves ``gopass.exe`` via PATHEXT on Windows).
    """
    if binary_path:
        pinned = Path(binary_path)
        return pinned if pinned.is_file() else None
    found = shutil.which("gopass")
    return Path(found) if found else None


def missing_binary_error(binary_path: str, section: str) -> str:
    """Actionable message for a missing/pinned-wrong gopass binary."""
    if binary_path:
        return f"secrets.{section}.binary_path ({binary_path!r}) is not an executable gopass binary."
    return (f"secrets.{section}.enabled is true but the gopass CLI was not found on PATH.  "
            "Install gopass (https://www.gopass.pw/) or set "
            f"secrets.{section}.binary_path to its absolute location.")


def classify_failure(code: int, stderr: str, subject: str) -> tuple[ErrorKind, str]:
    """Map a non-zero gopass exit onto the ErrorKind taxonomy.

    ``subject`` names the entry/folder in the message. gopass failure text
    never contains secret values; run_secret_cli has already ANSI-scrubbed it.
    """
    low = (stderr or "").lower()
    detail = (stderr or "").strip()[:180]
    if code == 6 or "not initialized" in low:
        return (ErrorKind.NOT_CONFIGURED,
                f"gopass password store is not initialized (exit {code}); run `gopass setup` "
                "or point config_path at the right gopass config")
    if any(marker in low for marker in _USAGE_ERROR_MARKERS):
        return (ErrorKind.INTERNAL,
                f"gopass rejected the invocation (exit {code}): {detail or 'usage error'}")
    if any(marker in low for marker in _NOT_FOUND_MARKERS):
        return (ErrorKind.REF_INVALID, f"{subject!r} is not in the password store (exit {code})")
    if any(marker in low for marker in _DECRYPT_MARKERS):
        return (ErrorKind.AUTH_FAILED,
                f"gopass could not decrypt {subject!r} (exit {code}): {detail or 'decryption failed'}")
    if code == 10:
        return (ErrorKind.REF_INVALID, f"{subject!r} not found (exit 10)")
    if code == 11:
        return (ErrorKind.AUTH_FAILED,
                f"gopass failed to retrieve or decrypt {subject!r} (exit 11): {detail or 'no stderr'}")
    if code == 13:
        return (ErrorKind.INTERNAL, f"gopass could not list the store (exit 13): {detail or 'list failed'}")
    if code == 7:
        return (ErrorKind.NETWORK, f"gopass git operation failed (exit 7): {detail or 'git error'}")
    return (ErrorKind.INTERNAL, f"gopass exited {code} for {subject!r}: {detail or 'no stderr'}")


@dataclass
class Outcome:
    """One gopass invocation's result. ``kind`` is set iff the call failed."""

    stdout: str = ""
    code: int = 0
    stderr: str = ""
    kind: Optional[ErrorKind] = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.kind is None


@dataclass
class GopassCli:
    """A gopass binary bound to one fetch's invocation policy.

    ``sync``: allow gopass's own git auto-sync (default False — Hermes passes
    ``--nosync`` so startup never waits on a remote). ``config_path``: pins the
    child's ``GOPASS_CONFIG``. ``optional_flags``: learned once per fetch — an
    older gopass that rejects ``--nofuzzysearch``/``--nosync`` flips the flag
    off after the first usage error instead of failing every reference.
    """

    binary: Path
    sync: bool = False
    timeout: float = DEFAULT_COMMAND_TIMEOUT_SECONDS
    config_path: str = ""
    optional_flags: bool = True

    def show(self, ref: str, key: str = "") -> Outcome:
        """Read one entry: its password field, or ``key`` of a structured entry."""
        return self._show_with_fallback(ref, key, allow_retry=self.optional_flags)

    def list_flat(self, folder: str) -> Outcome:
        """List entry paths under ``folder`` (does not decrypt anything)."""
        return self._execute([str(self.binary), "ls", "--flat", "--", folder])

    def extra_env(self) -> dict[str, str]:
        env = dict(_FORCED_ENV)
        if self.sync:
            env.update(_SYNC_ENV)
        if self.config_path:
            env["GOPASS_CONFIG"] = self.config_path
        return env

    def _show_with_fallback(self, ref: str, key: str, *, allow_retry: bool) -> Outcome:
        outcome = self._execute(self._show_argv(ref, key))
        if outcome.ok or not allow_retry or not self._is_usage_error(outcome):
            return outcome
        # Older gopass versions reject --nofuzzysearch/--nosync as unknown
        # flags; drop both once and remember it for the rest of this fetch.
        self.optional_flags = False
        return self._show_with_fallback(ref, key, allow_retry=False)

    def _show_argv(self, ref: str, key: str) -> list[str]:
        argv = [str(self.binary), "show"]
        if not key:
            argv.append("-o")  # password field only (first line)
        argv.extend(self._optional_flags())
        argv += ["--", ref]
        if key:
            argv.append(key)
        return argv

    def _optional_flags(self) -> list[str]:
        if not self.optional_flags:
            return []
        flags = ["--nofuzzysearch"]  # never enter the interactive fuzzy finder
        if not self.sync:
            flags.append("--nosync")  # never wait on a git remote at startup
        return flags

    def _is_usage_error(self, outcome: Outcome) -> bool:
        return outcome.code in (1, 2) and any(
            marker in outcome.stderr.lower() for marker in _USAGE_ERROR_MARKERS)

    def _execute(self, argv: Sequence[str]) -> Outcome:
        """Spawn once; never raises. Failures come back classified."""
        try:
            proc = run_secret_cli(argv, allow_env=_CHILD_ENV_ALLOWLIST,
                                  extra_env=self.extra_env(), timeout=self.timeout)
        except RuntimeError as exc:  # spawn failure or timeout, from run_cli
            text = str(exc)
            kind = ErrorKind.TIMEOUT if "timed out" in text else ErrorKind.BINARY_MISSING
            return Outcome(kind=kind, message=text)
        stderr = proc.stderr or ""
        if proc.returncode == 0:
            return Outcome(stdout=proc.stdout or "")
        subject = argv[argv.index("--") + 1] if "--" in argv else str(argv[-1])
        kind, message = classify_failure(proc.returncode, stderr, subject)
        return Outcome(code=proc.returncode, stderr=stderr, kind=kind, message=message)
