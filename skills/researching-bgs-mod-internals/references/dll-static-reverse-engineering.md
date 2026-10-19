# Closed-source SKSE plugin: binary to design

Use when a mod ships only a DLL (no repository, no source spoiler) and the question is how it works or how to reimplement it. The binary is the authority; the Nexus description is only a claim to check against it.

## 0. Toolchain

- The sandboxed code runner and the shell may resolve to different interpreters. Probe before writing analysis code: `python -c "import capstone, pefile; print('ok')"`. If the code runner lacks them, write a script file and run it through the shell instead.
- Never name a helper script `dis.py`, `types.py`, or `code.py`. It shadows a stdlib module that capstone imports and the failure reads like a broken install (circular import inside `capstone/__init__.py`).
- Write disassembly to files and read them with the file reader. Terminal output is truncated in the middle of wide tables, which silently drops the rows you need.

## 1. Provenance first

- `strings`-style scan of the DLL yields, without any disassembly: the embedded PDB path (`\<Name>\src\*.cpp`), third-party source paths (e.g. `CommonLibSSE-NG\extern\CommonLibSSE\src\SKSE\Logger.cpp`), and MSVC function-signature strings (`bool __cdecl <Namespace>::<Class>::Install(void)`) that name the install entry points.
- The export table confirms `SKSEPlugin_Query` / `SKSEPlugin_Load` and gives their RVAs.
- Record the archive hash and DLL size; they are the identity you cite later.

## 2. Function boundaries, then disassembly

- `pe.DIRECTORY_ENTRY_EXCEPTION` is the `.pdata` table: exact `(BeginAddress, EndAddress)` per function. Disassemble each range separately.
- Linear `.text` disassembly desyncs on jump tables and data islands. After a desync every later instruction is garbage, and references into `.data` stop being found at all, which looks like "the global is never written".
- capstone: set `md.skipdata = True`, then guard operand access because skipdata pseudo-instructions raise `CS_ERR_SKIPDATA`:

```python
try:
    ops = ins.operands
except Exception:
    ops = []
```

## 3. String to function

- Build a table of ASCII (and UTF-16 for Win32 API names) strings with their virtual addresses.
- Scan each function for RIP-relative memory operands and code immediates that resolve to those addresses; take the enclosing `.pdata` entry. That is the function that logs the message or names the feature.
- Start from install/failure messages: they sit in the same function as the hook setup and the version checks.

## 4. Annotate before reading

Print, for every RIP-relative memory operand: target VA, section name, printable string at that VA, and the initial 8 bytes. That turns raw disassembly into something close to source.

- One `mov rX, [rip+disp]` gives the address of an address-library slot; a second load gives its value. Cached pointers, cached IDs, and vtable bases all look identical until you resolve which one you have.
- ID-like immediates stored to the stack before a call identify the resolver; those immediates are the IDs to map. A tight sequence of `mov [rbp+X], <id>` / `call <resolver>` / `mov [global], rax` is a per-version constant table.

## 5. Map IDs onto CommonLibSSE-NG

- `git clone --depth 1 https://github.com/alandtse/CommonLibSSE-NG` and pin the commit.
- `grep -rn "<id>" include/RE` finds named relocations; `Offsets_VTABLE.h` gives `VTABLE_*` variant IDs; class headers give member offsets as `// 0xNN` comments plus `static_assert(offsetof(...))` you can trust.
- `REL::Module::Runtime` is a bitmask: `AE = 1`, `SE = 2`, `VR = 4`. Read the compares in the dispatch before assigning a branch to a game version.
- Distinguish three ID kinds: code relocations, data/vtable relocations, and raw module-base offsets (used where the runtime's address library lacks an entry, typically VR).

## 6. Cross-check against an open-source mod

- Clone a large open-source plugin that touches the same engine area (Community Shaders is the best-covered renderer reference).
- `grep` the same relocation ID or vtable index. Their `write_thunk_call<T>(REL::RelocationID(a, b).address() + offset)` and `write_vfunc<0xNN, T>(...)` give both the function identity and the call-site role for free.
- A second implementation of the same fix is also a free statement of intent: if one project calls the region "shadow maps" and the other restores a per-object mask, the layer boundary is already visible.

## 7. Arithmetic worth memorizing

- call target: `target = site + 5 + int32(site + 1)`; `Trampoline::write_call<5>` returns the old target, so you rarely compute it by hand.
- vtable slot from a byte offset: `index = offset / 8` on x64.
- version-shifted member: VR `ShadowSceneNode` = flat `+0x28` on each member.

## 8. Reporting

- Deliver a table of `(runtime, relocation ID, site offset, expected callee/vfunc, key struct offsets)` rather than prose, then the per-frame pipeline.
- Label engine function names you could not verify as inference; the ID plus offset is the citable fact.
