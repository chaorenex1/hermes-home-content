# NIF Asset Conflict Analysis

Extends the xEdit plugin-record conflict audit to the asset layer: NIF mesh
files (.nif) in Bethesda games. Covers file-level conflict detection,
block-structure comparison, texture-reference extraction, and toolchain setup.

## When to use

- A mesh looks wrong in-game and you need to find which mod's NIF is loading
- Two mods ship different versions of the same .nif and you need to compare them
- You need to verify that a PBR/ParallaxGen pass didn't change the skeleton or
  collision data
- You need to check whether texture paths in conflicting NIFs diverge

## File-level conflict detection

Use the MO2 MCP asset tools — no xEdit daemon needed:

```js
// List all mesh conflicts (truncated at 10k — use path_prefix to narrow)
mo2_assets_conflicts({ profile, path_prefix: "meshes" })

// Resolve a specific virtual path to its winner + loser chain
mo2_assets_resolve({ profile, virtual_path: "meshes/actors/character/..." })
```

Output gives:
- `winner.mod` / `winner.source_type` (loose or archive)
- `losers[]` — each with `.mod` and `.source_type`
- `is_conflict` — true when multiple sources provide the same path

Find the actual file paths via `mo2_machine_contract` → `archive_search_roots`.

## Block structure comparison (binary scan)

Parse NIF block types without full library support by scanning the binary for
known block-type strings. This works for comparison purposes — identical block
type counts mean the structural skeleton is the same.

```python
KNOWN_BLOCKS = [
    'NiNode', 'BSTriShape', 'BSLightingShaderProperty', 'BSShaderTextureSet',
    'NiSkinInstance', 'NiSkinData', 'NiSkinPartition', 'BSDismemberSkinInstance',
    'bhkCollisionObject', 'bhkRigidBody', 'bhkBoxShape', 'bhkCapsuleShape',
    'bhkSphereShape', 'bhkConvexVerticesShape', 'bhkCompressedMeshShape',
    'BSEffectShaderProperty', 'NiAlphaProperty', 'BSSubIndexTriShape',
    'NiTriShape', 'BSDynamicTriShape', 'BSXFlags', 'BSBound',
]

def nif_block_summary(path):
    with open(path, 'rb') as f:
        data = f.read()
    found = {}
    for block in KNOWN_BLOCKS:
        count = data.count(block.encode('ascii'))
        if count > 0:
            found[block] = count
    return found
```

**Interpretation**:
- Same block type counts → structurally equivalent (differences are in vertex/tangent data)
- Different counts → missing or added features (e.g., one has collision, other doesn't)
- Missing `bhk*` blocks → no collision data (normal for equipment/body NIFs)
- Missing `NiSkinInstance` → unskinned mesh (static prop vs rigged armor)

## Texture reference extraction

NIF files store texture paths in a string table. Extract by scanning for `.dds`
patterns bounded by null bytes:

```python
def extract_textures(path):
    with open(path, 'rb') as f:
        data = f.read()
    textures = set()
    pos = 0
    while True:
        idx = data.find(b'.dds', pos)
        if idx == -1: break
        start = idx
        while start > 0 and data[start-1] != 0:
            start -= 1
        end = idx + 4
        while end < len(data) and data[end] != 0:
            end += 1
        tex = data[start:end].decode('ascii', errors='replace')
        if len(tex) > 10:
            textures.add(tex)
        pos = idx + 1
    return sorted(textures)
```

**Common patterns**:
- `_n.dds` → normal map (vanilla)
- `_rmaos.dds` → roughness/metallic/AO packed (PBR upgrade)
- `_p.dds` → parallax/height map (PBR)
- `_em.dds` → emissive/glow map (may be dropped in PBR conversions)
- `_sk.dds` → subsurface/skin map

## pyffi setup (Python 3.12+)

pyffi 2.2.3 requires three patches for Python 3.12+:

1. **distutils shim** — pyffi imports `distutils.cmd.Command` which was removed in Python 3.12:
```python
# Create site-packages/distutils/__init__.py:
from setuptools._distutils import *
# Create site-packages/distutils/cmd.py:
from setuptools._distutils.cmd import *
```

2. **time.clock()** — removed in Python 3.8, pyffi still uses it:
```bash
sed -i 's/time\.clock()/time.perf_counter()/g' \
  site-packages/pyffi/object_models/xml/__init__.py \
  site-packages/pyffi/object_models/xsd/__init__.py
```

3. **NifSkope's nif.xml is INCOMPATIBLE** with pyffi — do not replace pyffi's
   bundled nif.xml with NifSkope's version. pyffi generates Python classes from
   the XML at build time; replacing the XML won't add missing block types
   (BSTriShape) because the corresponding Python code doesn't exist.

Even after patching, pyffi 2.2.3 does NOT support Skyrim SE's `BSTriShape` block
type. For SE NIFs, use the binary-scan approach above or install nifly from
source.

## Collision (bhk*) analysis

Collision blocks are only present in:
- Static architecture meshes (`meshes/architecture/`)
- Furniture (`meshes/furniture/`)
- Dungeon pieces (`meshes/dungeons/`)
- Clutter with physics (`meshes/clutter/`)

Equipment, body, hair, and prop NIFs normally do NOT contain collision blocks.
If a collision-related bug is suspected, filter to these directories:

```js
mo2_assets_conflicts({ profile, path_prefix: "meshes/architecture" })
mo2_assets_conflicts({ profile, path_prefix: "meshes/furniture" })
```

## PBR vs vanilla texture conflicts

ParallaxGen_Output is a common NIF conflict winner. Its role is to:
1. Re-save NIFs with recomputed tangent data (causes ~1% size change)
2. Replace vanilla texture paths with PBR equivalents (`_rmaos.dds`, `_p.dds`)
3. Drop emissive maps (`_em.dds`) — expected in PBR workflow

When comparing ParallaxGen winner vs another mod's loser:
- Same block structure + same texture set → tangent-only change, safe
- Same block structure + PBR textures → material upgrade, safe
- Different block structure → inspect for missing skeleton/collision

## Complete workflow

```
1. mo2_assets_conflicts({ path_prefix })  → find conflicting NIFs
2. mo2_assets_resolve({ virtual_path })   → identify winner/loser mods
3. mo2_machine_contract()                 → get file paths
4. nif_block_summary(winner_path)         → compare block structure
5. extract_textures(winner_path)          → compare texture references
6. Report: verdict per conflict pair
```
