"""gopass secret sources for Hermes Agent.

Two sources share one gopass CLI integration:

- ``gopass`` (mapped) — ``secrets.gopass.env`` binds ``ENV_VAR -> entry[#key]``.
- ``gopass_folder`` (bulk) — ``secrets.gopass_folder.folder`` injects every
  entry under a folder, basename as the env-var name.

Both are disabled by default (``secrets.<name>.enabled: true`` opts in), fetch
at process startup after ``.env`` loads, and never prompt; see README.md.

Also bundled: the ``gopass-source-manage`` skill (``skills/``, registered as
``gopass:gopass-source-manage``) — setup/init, operations guide, and the
gopass <-> Hermes contract.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .cli import GopassCli, find_gopass
from .folder_source import GopassFolderSource
from .source import GopassSource, parse_reference

logger = logging.getLogger(__name__)

__all__ = [
    "GopassCli",
    "GopassFolderSource",
    "GopassSource",
    "find_gopass",
    "parse_reference",
    "register",
]


def register(ctx) -> None:
    """Plugin entry point: register both gopass secret sources + bundled skill."""
    ctx.register_secret_source(GopassSource())
    ctx.register_secret_source(GopassFolderSource())
    _register_skills(ctx)


def _register_skills(ctx) -> None:
    """Register bundled skills as ``gopass:<name>`` (best effort; an older
    Hermes without plugin skills logs and skips)."""
    register_skill = getattr(ctx, "register_skill", None)
    if register_skill is None:
        logger.warning("gopass: ctx.register_skill unavailable; bundled skills not registered")
        return
    skills_dir = Path(__file__).parent / "skills"
    if not skills_dir.is_dir():
        return
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if not (child.is_dir() and skill_md.exists()):
            continue
        description, frontmatter = _skill_metadata(skill_md)
        try:
            register_skill(child.name, skill_md, description=description,
                           frontmatter=frontmatter)
            logger.info("gopass: registered skill %s", child.name)
        except Exception as exc:  # noqa: BLE001 — never let a skill kill the plugin
            logger.warning("gopass: registering skill %s failed: %s", child.name, exc)


def _skill_metadata(skill_md: Path) -> tuple[str, dict]:
    """``(description, frontmatter)`` from a bundled SKILL.md.

    Hermes builds a plugin skill's listing row from what ``register_skill``
    receives (the on-disk frontmatter is not re-read for that row), so the
    description must be parsed here — dependency-free subset.
    """
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("gopass: cannot read %s: %s", skill_md, exc)
        return "", {}
    frontmatter = _parse_frontmatter(text)
    description = str(frontmatter.get("description") or "").strip()
    return description, frontmatter


def _parse_frontmatter(text: str) -> dict:
    """Parse the leading YAML frontmatter block: ``key: value`` pairs (quotes
    stripped) plus ``key: |`` / ``key: >`` block scalars — the shapes bundled
    skills use. Deliberately avoids importing a YAML dependency."""
    lines = text.removeprefix("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict = {}
    index = 1
    while index < len(lines):
        line = lines[index]
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            index += 1
            continue
        key = key.strip()
        value = value.strip()
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            block: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index].strip()
                                          or lines[index].startswith((" ", "\t"))):
                block.append(lines[index].strip())
                index += 1
            if value.startswith(">"):
                fields[key] = " ".join(part for part in block if part)
            else:
                while block and not block[-1]:
                    block.pop()
                fields[key] = "\n".join(block)
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value
        index += 1
    return fields
