# NIF Binary Analysis — Agent Patterns

When xEdit / MO2 cannot answer an asset question and the NIF internals matter
(lighting shader flags, skeleton NiNode counts, collision bhk blocks, texture
references), the agent has two tiers:

## Tier 1: File-level conflict detection (MO2 VFS)

`mo2_assets_conflicts` + `mo2_assets_resolve` identify WHICH mod wins for a NIF
path. This answers "whose mesh loads?" — always start here.

## Tier 2: Internal NIF structure (block types, textures, lighting)

### pyffi — broken on Python ≥3.12

`pyffi` (2.2.3) requires `distutils` (removed in 3.12) and `time.clock()` (removed
in 3.8). Patching `distutils` → `setuptools._distutils` and `time.clock()` →
`time.perf_counter()` makes it import, but the bundled `nif.xml` predates Skyrim
SE's `BSTriShape` block type. Replacing with NifSkope's nif.xml fails because
pyffi's Python classes are generated from the XML at build time.

**Verdict: do not use pyffi for Skyrim SE NIFs. Use binary scanning.**

### Binary block-type scanning (works without any library)

NIF files store block type strings as length-prefixed ASCII in the header. A
simple `data.count(b"BlockName")` scan gives reliable block-type counts without
full parsing:

```python
known_blocks = [
    'NiNode', 'BSTriShape', 'BSLightingShaderProperty', 'BSShaderTextureSet',
    'bhkCollisionObject', 'bhkRigidBody', 'NiSkinInstance', 'NiSkinData',
    'BSDismemberSkinInstance', 'BSEffectShaderProperty', 'NiAlphaProperty',
]

with open(path, 'rb') as f:
    data = f.read()
    for block in known_blocks:
        count = data.count(block.encode('ascii'))
        if count > 0:
            print(f"{block}: {count}")
```

This is **not a full parser** — it counts occurrences of block type name strings
in the file binary. It works reliably for Skyrim SE NIFs because block type
names are unique enough not to appear in vertex/tangent data. False positives are
possible in files containing ASCII name collisions but have not been observed in
practice.

### Texture path extraction

Texture paths are null-terminated strings in the NIF string table. Search for
`textures/` followed by `.dds`:

```python
import re
textures = set()
for m in re.finditer(b'textures/[^\x00]+\\.dds', data):
    textures.add(m.group(0).decode('ascii', errors='replace'))
```

### NifSkope (GUI)

Path on this host: `K:\game\SkyrimSE\NifSkope_2_0_2020-07-09-x64\NifSkope.exe`

NifSkope is GUI-only. No CLI export. The `--port` flag is for IPC, not batch
processing. Use for manual inspection, not automated analysis.

### NIF file sizes as conflict signal

When block types are identical and file sizes differ by <5%, the difference is
likely tangent-space recalculation (BodySlide, ParallaxGen). Identical block
counts + same texture references + <2% size delta = structurally equivalent NIF.

## Tier 3: Full structural parse (not available)

Collision mesh inspection, NiNode hierarchy traversal, vertex data comparison,
and shader flag decoding require a true NIF parser. Options not yet implemented:

- **nifly**: Python wrapper for NifSkope's core; not on PyPI
- **cpatcher/nifxml**: Rust NIF parser; requires compilation
- **NifSkope XML export**: Not supported in headless mode

For collision-specific audits, focus on architecture/furniture/dungeon meshes
(where bhk blocks are present), not armor/body/weapon meshes (which lack them).
