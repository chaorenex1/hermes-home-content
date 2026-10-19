import { dirname, resolve } from "node:path";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * Walk upward from the calling module's directory until a package.json is
 * found, then return that directory as the plugin root.
 *
 * This is depth-adaptive: it handles both the canonical dist layout
 * (dist/discovery/ → 2 levels up to the package root) and any deeper nesting
 * produced by bundlers, monorepo tooling, or future directory restructuring.
 */
export function resolvePluginRoot(moduleUrl: string): string {
  let dir = dirname(fileURLToPath(moduleUrl));
  for (let i = 0; i < 8; i++) {
    if (existsSync(resolve(dir, "package.json"))) {
      return dir;
    }
    dir = resolve(dir, "..");
  }
  // Fallback: return the original 2-level-up convention so callers get a
  // stable directory even when package.json is truly absent.
  return resolve(dirname(fileURLToPath(moduleUrl)), "..", "..");
}

export function defaultCacheRoot(): string {
  // Unified with xtl/bgs-translator and other agent-side tooling: the cache
  // root is ~/.bgs-modding-superpowers/kb/packs on every platform. The legacy
  // paths (%LOCALAPPDATA%\bgs-modding-superpowers\kb on Windows; $XDG_CACHE_HOME
  // or ~/.cache on Linux/macOS) are no longer used. Users with a legacy install
  // can move ~/.cache/bgs-modding-superpowers/kb or
  // %LOCALAPPDATA%/bgs-modding-superpowers/kb to the new location, or expose
  // the old roots via $env:BGS_KB_USER_PACKS as additional read-only roots.
  const home = process.env.HOME || process.env.USERPROFILE || ".";
  return resolve(home, ".bgs-modding-superpowers", "kb", "packs");
}

export function parseUserPackRoots(envValue: string | undefined): string[] {
  if (!envValue) return [];
  return envValue
    .split(";")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}
