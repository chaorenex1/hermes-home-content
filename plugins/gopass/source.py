"""``gopass`` secret source — mapped, explicit ``ENV_VAR -> entry`` bindings.

Users bind env-var names to gopass entries in ``secrets.gopass.env``,
optionally selecting a structured key with ``#``::

    secrets:
      gopass:
        enabled: true
        env:
          OPENAI_API_KEY: hermes/openai         # password field (first line)
          SMTP_USER: gopass://email/smtp#user   # key "user" of a YAML entry

One ``gopass show`` per binding through the user's local gopass CLI. Hermes
never authenticates on the user's behalf: the GPG agent must already be able
to decrypt (cached passphrase or passphrase-less key), because startup runs
without a TTY and the fetch must never prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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

__all__ = ["GopassSource", "Reference", "parse_reference", "validate_env_map"]

_SCHEME = "gopass://"


@dataclass(frozen=True)
class Reference:
    """One parsed binding: a gopass entry path plus an optional structured key."""

    path: str
    key: str = ""

    def __str__(self) -> str:
        return f"{self.path}#{self.key}" if self.key else self.path


def parse_reference(raw: object) -> Optional[Reference]:
    """Parse ``path``, ``path#key`` or ``gopass://path[#key]`` into a Reference.

    Returns None for anything unusable: wrong type, empty, more than one ``#``,
    control characters, backslashes, a leading ``/``, or ``..`` path segments.
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if text.lower().startswith(_SCHEME):
        text = text[len(_SCHEME):].strip()
    path, sep, key = text.partition("#")
    path, key = path.strip(), key.strip()
    if not path or (sep and "#" in key):
        return None
    if any(ch in "\x00\r\n" for ch in path + key) or "\\" in path:
        return None
    if path.startswith("/") or ".." in path.split("/"):
        return None
    return Reference(path=path, key=key)


def validate_env_map(env_map: object) -> tuple[dict[str, Reference], list[str]]:
    """``(valid bindings, warnings)`` — invalid names/references are skipped
    with a warning, valid ones survive as name -> :class:`Reference`."""
    valid: dict[str, Reference] = {}
    warnings: list[str] = []
    for name, raw in env_map.items() if isinstance(env_map, dict) else []:
        if not isinstance(name, str) or not is_valid_env_name(name):
            warnings.append(f"Skipping {name!r}: not a valid env-var name")
            continue
        ref = parse_reference(raw)
        if ref is None:
            warnings.append(
                f"Skipping {name}: {raw!r} is not a usable gopass reference "
                "(expected path, path#key, or gopass://path[#key])")
            continue
        valid[name] = ref
    return valid, warnings


class GopassSource(SecretSource):
    """gopass as a registered **mapped** source: explicit per-var bindings, so
    its claims outrank bulk sources on contested vars (like 1Password's)."""

    name = "gopass"
    label = "gopass"
    shape = "mapped"
    scheme = "gopass"
    # An explicit VAR -> entry binding is the strongest user intent; a stale
    # .env line must not silently defeat a rotated vault value.
    override_existing_default = True
    remediation_hints = {
        ErrorKind.NOT_CONFIGURED: "Add ENV_VAR: entry-path bindings under "
                                  "secrets.gopass.env (config.yaml), then restart Hermes.",
        ErrorKind.BINARY_MISSING: "Install the gopass CLI (https://www.gopass.pw/) or set "
                                  "secrets.gopass.binary_path to its absolute location.",
        ErrorKind.AUTH_FAILED: "gopass could not decrypt — unlock the GPG key in your agent "
                               "(run `gopass show <entry>` once in a terminal), or re-check the "
                               "entry's recipients with `gopass recipients`.",
        ErrorKind.REF_INVALID: "Fix the secrets.gopass.env bindings — `gopass ls --flat` shows "
                               "what exists in the store.",
    }

    def config_schema(self) -> dict:
        return {
            "enabled": {"description": "Master switch", "default": False},
            "env": {"description": "Map of ENV_VAR -> gopass reference "
                                   "(entry path, path#key, or gopass://path[#key])",
                    "default": {}},
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
        """Resolve every configured binding. Per-ref failures become warnings;
        an all-failed fetch becomes an error carrying the first failure's kind."""
        cfg = cfg if isinstance(cfg, dict) else {}
        result = FetchResult()

        refs, warnings = validate_env_map(cfg.get("env"))
        result.warnings.extend(warnings)
        if not refs:
            if warnings:
                return result.fail(
                    "secrets.gopass.env has no usable binding (see the warnings above).",
                    ErrorKind.REF_INVALID)
            return result.fail(
                "secrets.gopass.enabled is true but secrets.gopass.env is empty.  "
                "Add ENV_VAR: entry-path bindings in config.yaml.",
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

        failures: list[tuple[ErrorKind, str]] = []
        for name in sorted(refs):
            ref = refs[name]
            outcome = cli.show(ref.path, ref.key)
            if not outcome.ok:
                failures.append((outcome.kind or ErrorKind.INTERNAL, outcome.message))
                result.warnings.append(f"{name}: {outcome.message}")
                continue
            value = outcome.stdout.rstrip("\r\n")
            if not value.strip():
                result.warnings.append(
                    f"{name}: gopass returned an empty value for {ref} — not applied "
                    "(an empty value must not replace a working credential).")
                continue
            result.secrets[name] = value

        if failures and not result.secrets:
            return result.fail(
                f"every gopass reference failed ({len(failures)}); "
                f"first error — {failures[0][1]}",
                failures[0][0])
        return result
