import { describe, it, expect } from "vitest";
import { makeMockAdapter } from "../fixtures/daemon-mock.js";
import { mkdtempSync, writeFileSync, rmSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("daemon adapter (mock contract)", () => {
  it("returns the raw native ok envelope for a known command", async () => {
    const adapter = makeMockAdapter({
      "system.describe": () => ({ gameMode: "Fallout4", dataPath: "C:/x" }),
    });
    const res = await adapter.call({ command: "system.describe", args: {} });
    expect(res.ok).toBe(true);
    if (!res.ok) throw new Error("expected ok");
    expect((res.result as { gameMode: string }).gameMode).toBe("Fallout4");
  });

  it("returns a native error envelope for an unknown command", async () => {
    const adapter = makeMockAdapter({});
    const res = await adapter.call({ command: "nope.nope", args: {} });
    expect(res.ok).toBe(false);
    if (res.ok) throw new Error("expected error");
    expect(res.error.code).toBe("unknown_command");
  });

  describe("createPowershellAdapter validation", () => {
    it("throws on non-positive timeoutSeconds at construction time", async () => {
      const { createPowershellAdapter } = await import("../../src/daemon-adapter.js");
      expect(() =>
        createPowershellAdapter({
          clientScript: "x",
          pid: 1,
          timeoutSeconds: 0,
        }),
      ).toThrow(/Invalid timeoutSeconds/);
      expect(() =>
        createPowershellAdapter({
          clientScript: "x",
          pid: 1,
          timeoutSeconds: -5,
        }),
      ).toThrow(/Invalid timeoutSeconds/);
      expect(() =>
        createPowershellAdapter({
          clientScript: "x",
          pid: 1,
          timeoutSeconds: Number.POSITIVE_INFINITY,
        }),
      ).toThrow(/Invalid timeoutSeconds/);
    });

    it("accepts a valid timeoutSeconds and omitted default", async () => {
      const { createPowershellAdapter } = await import("../../src/daemon-adapter.js");
      expect(() => createPowershellAdapter({ clientScript: "x", pid: 1 })).not.toThrow();
      expect(() =>
        createPowershellAdapter({
          clientScript: "x",
          pid: 1,
          timeoutSeconds: 60,
        }),
      ).not.toThrow();
    });

    it("forwards --game-mode to xedit-client automation call when configured", async () => {
      const { createPowershellAdapter } = await import("../../src/daemon-adapter.js");

      const sandbox = mkdtempSync(join(tmpdir(), "xedit-mcp-daemon-adapter-"));
      const reqResDir = join(sandbox, "rr");
      mkdirSync(reqResDir, { recursive: true });

      const fakeClient = join(sandbox, "fake-client.ps1");
      writeFileSync(
        fakeClient,
        [
          "$gmIdx = [Array]::IndexOf($args, '--game-mode')",
          "if($gmIdx -lt 0 -or ($gmIdx + 1) -ge $args.Count){ exit 2 }",
          "if($args[$gmIdx + 1] -ne 'SkyrimSE'){ exit 3 }",
          "$idx = [Array]::IndexOf($args, '--response-file')",
          "if($idx -lt 0 -or ($idx + 1) -ge $args.Count){ exit 1 }",
          "$resp = $args[$idx + 1]",
          "$payload = @{ ok = $true; command = 'system.describe'; result = @{ gameMode = 'SkyrimSE' } } | ConvertTo-Json -Depth 5",
          "Set-Content -Path $resp -Value $payload -Encoding UTF8",
          "exit 0",
        ].join("\n"),
        "utf8",
      );

      const adapter = createPowershellAdapter({
        clientScript: fakeClient,
        pid: 42,
        gameMode: "SkyrimSE",
        scratchDir: reqResDir,
      });

      const res = await adapter.call({ command: "system.describe", args: {} });
      expect(res.ok).toBe(true);

      const leftovers = existsSync(reqResDir)
        ? readdirSync(reqResDir).filter((n) => n.endsWith(".req.json"))
        : [];
      expect(leftovers.length).toBe(0);

      rmSync(sandbox, { recursive: true, force: true });
    });
  });
});
