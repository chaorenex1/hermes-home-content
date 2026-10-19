# qt_ini.py backslash-escaping bug (ModOrganizer.ini corruption)

## Session context

- Date: 2026-07-02
- Environment: tri-split MO2, instance INI at `<USER_HOME>\AppData\Local\ModOrganizer\mod make\ModOrganizer.ini`

## Symptom

After `mo2_agent_control.py` calls `_ensure_mo2_executable` →
`upsert_custom_executable` in `qt_ini.py`, the `[customExecutables]` section
of `ModOrganizer.ini` is corrupted:

1. New entries use `1\\title=` (double backslash) instead of `1\title=` (single).
2. The `binary` path loses all backslashes: `H:ueLun V5od Organizer 2oolsíitíit.exe`
   instead of `<PATH_TO_MO2_INSTALL>\Tools\xEdit\xEdit.exe`.
3. Existing entries may be overwritten or displaced.
4. MO2 CLI `-e <title>` silently fails to find the executable, so xEdit never
   starts.

## Root cause

`qt_ini.py` `_write_custom_executables_section` line 100:

```python
prefix = f"{index}\\\\\\\\"  # produces 4 backslash chars → '1\\\\'
```

Qt QSettings INI array format uses **one** backslash as the separator between
index and key (`1\title=...`). In the raw INI file, this appears as `1\title`
(one literal backslash character, byte `0x5c`).

The f-string `f"{index}\\\\\\\\"` produces **two** backslash characters in the
output string, which when written to the file yields `1\\title=` — a key that
Qt cannot parse, and that `parse_custom_executables` (which correctly uses
`f"{index}\\"` = one backslash char) will not match.

Worse, the existing entries in the INI already use `1\\` (two backslashes in
the raw file), which is the Qt QSettings escaped form of `1\`. So the parser
matches them with `f"{index}\\"` (one backslash char in Python = `\\` in the
file). But the writer produces `f"{index}\\\\"` (two backslash chars in
Python = `\\\\` in the file), which is **four** backslashes in the raw file —
a double-escaped form that neither Qt nor the parser can read.

Additionally, `upsert_custom_executable` calls `ini_path.read_text()` and
`ini_path.write_text()`, which round-trips through Python's universal newline
handler. The binary path `<PATH_TO_MO2_INSTALL>\Tools\xEdit\xEdit.exe`
loses its backslashes during the write because the f-string prefix bug causes
the value to be written under a malformed key that Qt's parser cannot recover.

## Fix

Change the prefix to use **one** backslash character (matching the existing
INI format):

```python
# Before (BROKEN — produces 2 backslash chars):
prefix = f"{index}\\\\\\\\"

# After (FIXED — produces 1 backslash char):
prefix = f"{index}\\\\"
```

In Python source code, `"\\"` is one backslash character, so
`f"{index}\\"` produces `1\` in the output string, which writes `1\title=`
to the file — the correct Qt QSettings format.

## Files to patch

| File | Location |
|---|---|
| `<moRoot>/plugins/qt_ini.py` | MO2 plugin directory (runtime copy) |
| `<hermes_skills>/bgs-modding/tools/mo2-control-plane/live-bridge/qt_ini.py` | Global skills source |

## INI recovery after corruption

If the INI is already corrupted:

1. Kill MO2 (`taskkill //PID <pid> //F`).
2. Open the instance INI (for tri-split:
   `<USER_HOME>\AppData\Local\ModOrganizer\<instance>\ModOrganizer.ini`).
3. Find the `[customExecutables]` section.
4. Remove all entries with `\\` (double backslash) prefix that were added by
   the buggy `upsert_custom_executable`.
5. Verify the remaining entries use `\` (single backslash) prefix.
6. Check `size=N` matches the actual number of entries.
7. Verify `binary` paths are intact (contain full `H:\...` paths).
8. Restart MO2. MO2 may re-normalize the INI on startup.

### Verification

```python
p = r'<USER_HOME>\AppData\Local\ModOrganizer\mod make\ModOrganizer.ini'
with open(p, 'rb') as f:
    raw = f.read()
idx = raw.find(b'[customExecutables]')
# Check: keys should be like b'1\\title=' (0x31 0x5c 0x74)
# NOT b'1\\\\title=' (0x31 0x5c 0x5c 0x74)
section = raw[idx:idx+200]
print(section.hex())
# 315c7469746c653d = '1\title=' ← CORRECT (1 backslash)
# 315c5c7469746c653d = '1\\title=' ← WRONG (2 backslashes)
```

## Pitfall: MO2 re-normalizes INI on restart

When MO2 starts, it reads and rewrites `ModOrganizer.ini` using Qt's own
QSettings serializer. This can:
- Fix malformed entries (Qt silently drops ones it can't parse).
- Change `size=` to reflect the entries Qt actually understood.
- Add back default entries that were deleted.
- Normalize path separators (mixed `/` and `\` → Qt's preferred form).

So after restarting MO2, the INI may look different from what was manually
edited. Always re-read the INI after MO2 restart to verify the current state.
