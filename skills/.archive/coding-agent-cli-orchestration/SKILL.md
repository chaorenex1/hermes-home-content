---
name: coding-agent-cli-orchestration
description: "Use when delegating code work to coding-agent CLIs."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [coding-agents, cli, delegation, worktrees, pty, verification]
---

# Coding Agent CLI Orchestration

## Overview

Class-level workflow for delegating implementation, refactoring, testing, and review to autonomous coding CLIs such as Claude Code, OpenAI Codex, and OpenCode. Provider-specific flags change; the orchestration contract does not: bind scope, choose bounded one-shot versus interactive mode, isolate concurrent writers, monitor real execution, and independently verify the resulting repository state.

## Provider Selection

- Use the provider explicitly requested by the user when available.
- Otherwise choose based on installed/authenticated CLI, required model/provider, sandbox behavior, and whether the task needs one-shot or interactive continuation.
- Do not infer missing auth from one absent environment variable; each CLI may have OAuth or provider-local credential storage.
- Read `references/claude-code.md`, `references/codex.md`, or `references/opencode.md` before invoking that provider.

## Shared Workflow

1. Confirm repository/workdir, task boundaries, Git state, CLI version, and authentication readiness.
2. Create a bounded prompt with acceptance criteria, allowed write scope, tests, and forbidden operations.
3. Prefer the provider's non-interactive one-shot command. Use `pty=true` only when required.
4. For long bounded work, launch with `background=true` and monitor through `process`; never shell-background.
5. Use a separate worktree/workdir for every concurrent writer.
6. Answer agent prompts only within the user's authority and task scope.
7. Wait for completion, then inspect Git state, diff, and test output yourself; agent prose is not verification.
8. Run targeted and required broader checks; report actual changes, outcomes, and residual risks.
9. Clean up PTY/tmux/process sessions and temporary worktrees when safe.

## Safety and Permission Modes

Use the narrowest capabilities that can finish the task. Dangerous bypass modes require explicit justification, a constrained workdir, clean Git evidence, diff review, and no unrequested push/deploy. Never let an external coding agent commit, push, or alter unrelated files unless authorized.

## One-Shot vs Interactive

| Task shape | Mode |
|---|---|
| Clear single fix/refactor/review | one-shot/print/run/exec |
| Multi-turn design and implementation | interactive PTY or resumable session |
| Long bounded task | background process with monitoring |
| Parallel independent tasks | isolated worktrees and one process each |

## Verification Checklist

- [ ] CLI/version/auth and repository scope checked.
- [ ] Prompt defined write boundaries, acceptance, and tests.
- [ ] Parallel writers used isolated worktrees.
- [ ] No orphan process/session remains.
- [ ] Final diff independently reviewed.
- [ ] Relevant tests ran with real output.
- [ ] No unrequested commit, push, deploy, or destructive action occurred.

## Provider References

- `references/claude-code.md` — print mode, tmux, permissions, sessions, hooks, and flags.
- `references/codex.md` — exec, PTY/sandbox caveats, gateway behavior, reviews, and worktrees.
- `references/opencode.md` — run, TUI lifecycle, provider selection, sessions, and verification.
