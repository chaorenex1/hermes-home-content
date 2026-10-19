# Native, managed, and packaged artifacts

## Recorded Linux crashes

Use `inspect_recorded_crash` with an explicit Linux x86-64 ELF core path to
inspect historical thread registers, signals, raw notes and original file
ranges. It is independent of the active disassembler target. Source-bound
register values and note bytes are observations; missing notes, signal-thread
association and current executable/library identity remain unknown. PIDs are
historical metadata and never authorize live attach or control.

The optional `include_debugger_context` facet adds mapping candidates through
caller-supplied GDB/pwndbg in an owned core-only session. Display names do not
establish current file identity; zero reported flags leave permissions unknown.
Requested unavailable context fails with setup guidance. See
[recorded crashes](https://github.com/morluto/rea/blob/main/docs/recorded-crashes.md)
for exact upstream profiles, bounds and verification coverage.

## Offline ELF layout

Use `inspect_binary_layout` with an explicit local ELF path for file-backed
sections, symbols, relocations, linkage names, and static mitigation inferences
without opening a disassembler target. When that complete record is already
retained, call `inspect_analysis_view` for a summary, mitigations or linkage
facet, one section or symbol, or a stable page. Do not re-run the decoder to
read a single object.

## Native targets

After `open_binary`, use focused search, procedure, or function tools directly.
Use `binary_overview` when target metadata or inventory context helps answer the
question. Prefer literal search, names, decompilation, callers, callees, and
cross-references. Addresses and recovered pseudocode are analysis observations,
not original source. Provider unavailability and unsupported metadata remain
unknown rather than false.

To see which functions or Objective-C methods a Mach-O actually calls in one
run, use `observe_native_calls` with explicit breakpoints and a bounded
`duration_ms`/`max_events`. It launches a new process under LLDB, so the target
runs and may change files or use the network. Hardened-runtime targets need the
`get-task-allow` entitlement.

Use `binary_session` with no arguments to check the open target, selected
provider, and alignment. Its default `result.tool_availability` includes the
complete tool inventory with availability reasons and remediation. When choosing
a tool, use its entry in that result; `tools/list` retains the complete catalog
when the target or provider state changes.

## DOS MZ with Ghidra

For an admitted DOS MZ target, use `inspect_native_load_image` to check measured
loaded bytes, file mappings, relocations and the entry against the immutable
snapshot. Keep `mismatch` and `unsupported` explicit. Verified import covers the
reported static image, not runtime DOS or PC-98 hardware behavior.

Use `read_bytes` for initialized analysis memory and `address_to_file_offset` to
anchor one observed address to original file bytes. Loader fixups can change a
word; a source offset does not imply byte equality. Complete function body ranges
use inclusive ends and can contain gaps. Do not treat the enclosing span as code.
For packed targets, retain the original and separately derived artifact identities;
decompiling an unpacking stub does not recover the unpacked program.

## Managed PE/CLI

Start with `inspect_managed_artifact`. REA's canonical managed inspection is
execution-free: do not claim it loaded, reflected, executed, or resolved the
assembly. Keep managed/native boundaries and unavailable reconstruction facts
explicit. A bring-your-own reconstruction oracle is separate from the canonical
parser and must not become an implicit setup dependency.

### .NET NativeAOT

NativeAOT binaries contain native machine code, so ordinary CIL decompilers
cannot recover the original method bodies. When managed metadata/CIL is absent,
classify that as a native-analysis route rather than claiming source recovery.
Open the native image with the selected deep provider and inspect functions,
strings, calls, and references; describe decompiler output as pseudocode and
inference.

NativeAOT images can be PE/COFF, ELF, or Mach-O executables and shared
libraries. Use file bytes and loader metadata rather than suffixes to identify
them. For packaged apps, inventory/extract with REA's artifact tools and retain
the exact contained image identity. PDB, ELF debug, or dSYM sidecars are
additional evidence only when the provider accepts and matches them.

For deeper type recovery, the optional third-party
[Ghidra NativeAOT analyzer](https://github.com/Washi1337/ghidra-nativeaot)
rehydrates ReadyToRun metadata and can recover method tables, type relationships,
frozen objects, and strings. This is a Ghidra extension with its own install and
interactive workflow; it is not currently part of REA's managed parser or
headless Ghidra bridge. Treat its annotations as analysis evidence, retain the
binary identity, and do not present recovered types as original source. Header
discovery may require a symbol or analyst identification of the ReadyToRun
header, depending on the binary and analyzer version.

## Packages and extraction

Use `inspect_artifact` for application bundles, archives, ZIP/APK/IPA/MSIX/AppX,
ASAR, or DMG inputs when the artifact graph and findings help answer the
question. It returns the complete artifact graph inline. Cite graph manifest
IDs when using them.

For an IPA or a macOS `.app`, ZIP, or DMG, pass the inventory Evidence to
`project_apple_application_graph`. It reports application roots and nested
bundles by path convention: app extensions, XPC services, frameworks, login
items, system and driver extensions, and plug-ins. It also lists privileged
helpers, launchd plists, symlinks, and each bundle's `info_plist_path` and
executable candidates. Roles are path conventions, not parsed plists; read the
listed plists with `inspect_plist`.

After `open_binary` on a `.app` or Mach-O, use `trace_dylib_resolution` to see
which file each `@rpath`, `@loader_path` and `@executable_path` load reaches for
every executable in the bundle. It also lists missing or weak loads and earlier
`@rpath` candidates that are absent. Narrow large bundles with `roots` or
`architecture`. System paths stay undetermined because the dyld shared cache
provides them.

Use `extract_artifact` when materialized files are needed. It takes no arguments
and materializes all regular files into a fresh temporary directory chosen by
REA. Symlinks and encrypted entries are inventory facts, not extractable files.
The result reports the materialized directory; callers do not choose the
destination. No separate permission grant is needed.

Native DMG traversal automatically uses a read-only mount on supported macOS
hosts, with an owned temporary mount directory and cleanup. It needs no approval
flag. Unsupported hosts or mount failures remain explicit limitations; do not
claim child inventory when only root identity is available. Extraction is a
separate filesystem-writing operation.

For headerless DOS COM, explicitly open with `format: "dos-com"` (CLI
`--target-format dos-com`). Inspect the load image before trusting function
analysis: the entry is `0x10100`, file offset zero, with imposed real-mode segment
context. PSP/stack/device state remains unmodeled. See [DOS guide](https://github.com/morluto/rea/blob/main/docs/ghidra-dos.md).

### Function annotations in Ghidra

Use `annotate_native_function` for one function name and/or entry comments, with at least one explicit change. Review its annotation readback and refreshed dossier inline. Changes are atomic and session-scoped; empty comments clear them, omitted fields preserve them. Later MCP calls observe edits until close. CLI `annotate-native-function` returns the updated analysis before discarding the session. Original executable bytes are unchanged; edits invalidate immutable snapshots. Windows P0 does not admit database mutations.

## PE DLL on Windows: headless Ghidra and PDB symbols

REA's Windows Ghidra P0 rejects shared libraries by target role. Analyze the DLL
with Ghidra directly:

1. Create the project directory first. `analyzeHeadless` does not create it and
exits with `FileNotFoundException` when it is missing.
2. Import and analyze once, with a script that decompiles named functions:
   `analyzeHeadless <projdir> <projname> -import <dll> -scriptPath <scripts>
   -postScript DumpDecomp.java <names...> -analysisTimeoutPerFile 900`.
   A ~0.8 MB C++ plugin takes about 3 minutes and yields ~2000 functions.
3. Reuse the saved project for every later query:
   `-process <program> -noanalysis -postScript ...` returns in seconds. `-save`
   is an import-mode parameter; `-process` rejects it, and anything after
   `-postScript` is consumed as script arguments.
4. Ghidra compiles scripts on first use with deprecation warnings treated as
errors, so one deprecated call fails the whole script with
`ClassNotFoundException`. Call `DemanglerUtil.demangle(program, mangled, addr)`
(the two-argument overload is deprecated). `GhidraScript` has no
`setFunctionName(Function, String, SourceType)`; rename with
`function.setName(name, SourceType.IMPORTED)`. `Function` has no `getFullName()`;
match namespaced symbols with `f.getSymbol().getName(true)`.

PDB symbols: Ghidra does not read PDB files. `llvm-pdbutil dump -publics <pdb>`
lists `S_PUB32` records (functions and data); the Windows LLVM release is one
large archive, so extract only `bin/llvm-pdbutil.exe`. `pdbparse` from PyPI
crashes on current MSVC PDBs (`'NoneType' object has no attribute 'name'`);
install it from the moyix/pdbparse git master instead. Map each record as
`section[segment-1].VirtualAddress + offset`, and validate one known export
against the PE export table before trusting thousands of RVAs.

Backfill inside a Ghidra script: for each RVA take the existing function at
`ImageBase + rva` (public symbols include data, so skip addresses with no
function), then `DemanglerUtil.demangle(program, mangled, addr)` and
`applyTo(program, addr, new DemanglerOptions(), monitor)`. That restores
namespaces and signatures, not just names: confirm by re-decompiling a known
export and checking parameters moved from `undefined8` to real types.
