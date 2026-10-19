# MO2 Local Category IDs

MO2 stores local category assignments in `meta.ini` as `category=<id>` under
`[General]`. The ID-to-name mapping lives in `<mo2Root>/categories.dat`.

## Key Categories (Skyrim SE)

| ID | Category Name |
|----|---------------|
| 23 | Followers & Companions - Creatures |
| 43 | Followers & Companions |
| 70 | NPC |
| 96 | (Nexus category ID — different system) |

## Pitfalls

- **`category` (local) ≠ `nexuscategory` (Nexus)**: MO2 has TWO category systems.
  `category` uses the local `categories.dat` IDs. `nexuscategory` uses Nexus
  website category IDs. Both must be set for MO2 to display the category
  correctly. Example for "Followers & Companions":
  - `category=43` (from categories.dat)
  - `nexuscategory=96` (from nexusmods.com for Skyrim SE "Followers & Companions")
- **Categories.dat is the ground truth**: always read `categories.dat` before
  setting `category` — the IDs differ per game and per MO2 instance.
- **Wrong ID silently fails**: MO2 won't complain if you set `category=70`.
  The mod just won't show the category icon/filter. Verify with
  `mo2_mod_info` after editing.
