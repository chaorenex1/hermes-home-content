# Hermes Skill Directory Layout

When editing a skill that exists in both the profile-specific and global
(shared) trees, apply changes to BOTH locations.

## Two tiers

| Tier | Path | Scope |
|------|------|-------|
| Profile-specific | `%LOCALAPPDATA%/hermes/profiles/<profile>/skills/` | Only the active profile sees these |
| Global / shared | `%LOCALAPPDATA%/hermes/skills/` | All profiles on this machine share these |

`%LOCALAPPDATA%` resolves to `C:\Users\<user>\AppData\Local\` on Windows.

## Concrete example (this plugin)

- Profile `bgs-modding`:
  `C:\Users\<user>\AppData\Local\hermes\profiles\bgs-modding\skills\bgs-modding\setting-up-bgs-modding-environment-hermes\SKILL.md`

- Global shared:
  `C:\Users\<user>\AppData\Local\hermes\skills\bgs-modding\setting-up-bgs-modding-environment-hermes\SKILL.md`

## Sync workflow

1. Edit the profile version first (the one in play).
2. Verify the change works.
3. Apply the same patches to the global version under `%LOCALAPPDATA%/hermes/skills/`.
4. Verify both files match on the changed sections.

## Pitfall: `~/.hermes/skills/` does NOT exist

Do NOT assume a `~/.hermes/skills/` Unix-style path. On Windows the real
Hermes data directory is under `%LOCALAPPDATA%/hermes/`, not `~/.hermes/`.
The `~/.hermes/` directory may exist for legacy reasons (config.yaml, some
profile data) but does NOT contain a `skills/` tree.
