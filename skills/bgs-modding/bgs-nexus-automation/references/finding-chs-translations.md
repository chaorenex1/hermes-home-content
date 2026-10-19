# Finding 和光 (With Light) CHS Translations for FDE Mods

Methodology for locating and verifying Simplified Chinese translations that use the
和光 (With Light) terminology standard for Follower Dialogue Expansion (FDE) mods by anbeegod.

## Three-Layer Search Strategy

### Layer 1: Broad tag search
Search Nexus with the mod series name + `tag=Chinese`:
```
nexus-automation.js search "Follower Dialogue Expansion" tag=Chinese count=50
```
This returns CHS translations that have the Chinese tag set. Results are often
incomplete — many translations exist in the mod's Translations accordion section
but are not tagged.

### Layer 2: Mod page Translations section (MOST RELIABLE)
For each target mod, use `nexus-automation.js description <modId>` and inspect
the `accordion.translations` table. The Translations accordion on Nexus lists
ALL registered translations including Mandarin ones. This is the authoritative
source — if a translation isn't listed here, it doesn't exist as a Nexus
dependency link.

Key fields in each translation table row:
- `modName`: language (e.g., "Mandarin")
- `modId`: the translation mod's Nexus ID
- `modUrl`: direct link to the translation mod
- The display name string (after the object) often contains the mod name with
  "With Light" or "CHS" marker

### Layer 3: Verify 和光 status
For each candidate translation, run `nexus-automation.js description <chsModId>`
and check the raw description for these keywords:
- `和光` / `和光汉化` / `和光名词`
- `With Light` / `With LIght` (note: sometimes misspelled)

A valid 和光 translation will explicitly state it in the description body OR
in the requirements section (depending on "Unofficial Chinese Translation for
Skyrim Special Edition By With Light" as a prerequisite).

## Known 和光 Translators (high confidence)

These authors consistently produce 和光-based translations:

| Author | Pattern | Example IDs |
|--------|---------|-------------|
| Kamiki Yui / KamikiYui | "CHS (With Light)" suffix | 183181 (Senna), 182340 (Aranea), 180222 (Ralof), 168151 (Elisif) |
| qwelovo | "Chinese With Light" suffix | 177800 (Lisette), 174751 (Marcurio), 172586 (Olfina), 170700 (Saadia) |
| LOYINuts | "LOYI CHS" / "和光汉化" in description | 165540 (Faralda) |
| EBanana | Provides both ANK and 和光 versions | 175366 (Illia) |
| ajsks | "和光版本" in description | 166063 (Fura Bloodmouth) |

## Verification Checklist

For each candidate CHS translation:
1. [ ] Mod name contains "CHS", "Chinese", or "简体中文"
2. [ ] Description explicitly mentions "和光" or "With Light"
3. [ ] Requirements list "Unofficial Chinese Translation for Skyrim Special Edition By With Light" (mod 139134) when applicable
4. [ ] Author is a known 和光 translator (see table above)

## Common Pitfalls

- **Non-和光 translations exist for most FDE mods** — Kanie17, MisakaToffee,
  WhisperThief, tyr4nt123, alwantai (ANK) produce quality translations but
  are NOT 和光-based. Always verify.
- **"CHS" in the name ≠ 和光** — many translations are named "CHS" but use
  ANK or custom terminology. Must read the description.
- **tag=Chinese search may miss mods** — the Chinese tag on Nexus is optional
  and many translators don't set it. The Translations section on the base mod
  page is the ground truth.
- **Translation may be attached to base mod via Nexus dependency, not tagged** —
  these appear in the Translations accordion but not in search results.
