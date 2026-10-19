# AGENTS.md — BGS-Nexus-automation

This is a Hermes Agent skill. The governing AGENTS.md contract lives at the repository root.

## Skill Identity

- **Name**: BGS-Nexus-automation
- **Version**: 2.0.0
- **Author**: Hermes Agent (Nous Research)
- **Category**: browser-automation

## Operating Contract

This skill operates under the top-level [AGENTS.md](../../../AGENTS.md) authority. When loaded by
Hermes Agent, [SKILL.md](SKILL.md) provides the full operational specification; this file is only a pointer.

## Role

Operate Nexus Mods through the Hermes built-in browser tools for any game selected by `game_domain`:
search and list mods, read mod details/files/posts/bugs, track/endorse/vote, download, and read the
MO2 API key. No CDP, no Node scripts.

## Quick Reference

- **Full spec**: [SKILL.md](SKILL.md)
- **Console expressions**: [references/browser-console-snippets.md](references/browser-console-snippets.md) (S1–S17)
- **Pitfalls**: [references/browser-tool-pitfalls.md](references/browser-tool-pitfalls.md)
- **Safety**: never create API keys, never save credentials, confirm every write operation

## Execution

```text
browser_navigate(url) -> S2 wait -> browser_console(S<n>) -> snapshot + browser_click for writes
```

See [README.md](README.md) for the feature table and [SKILL.md](SKILL.md) for the procedures.
