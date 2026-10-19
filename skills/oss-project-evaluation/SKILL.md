---
name: oss-project-evaluation
description: "Use when reviewing an OSS project: usage, pros/cons, adopt."
version: 1.0.0
license: MIT
author: Hermes Agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [oss, evaluation, due-diligence, github, adoption, security-review]
    category: software-development
    related_skills: [github, codebase-onboarding]
---

# OSS project evaluation (用法 / 优劣 / adopt-or-not)

Review a third-party open-source project the way this user consumes it: how do I use it,
what is it actually good for, what are its verified risks — not a brochure summary.
The deliverable is the verdict, and every strength/weakness claim in it is something
you checked yourself.

## When to Use

- 用户发来一个 repo 或项目名，问「用法」「优劣」「怎么样」「值不值得用」「要不要用」。
- 用户先让搜索再跟进评估（"github 搜索 X" → 追问其中某个项目）。
- 用户带质量要求要替代品（"github 搜索 X，安全模型要好"）—— 交付的是对比短名单，
  不是单项目评估。
- 用户对已评估过的工具继续追问单一维度（跨平台兼容性、agent 交互适应性等）—— 交付
  同一短名单上的逐项对比矩阵，不重新做仓库发现。
- A candidate project needs an adoption verdict before the user invests time,
  credentials, or an agent integration in it.

## Workflow

1. Identify the repo. If only a name/topic was given, find it first — search breadth
   tips (multi-language queries, shortlist enrichment) live in the `github` skill's
   repo-discovery reference.
2. Metadata pass, no clone yet: license, stars, archived, last push, language; releases
   (cadence + which OS assets actually ship); contributors (bus factor); recent commit
   subjects. Commands: same github reference.
3. Shallow-clone into the Hermes scratch dir and read the README IN FULL — READMEs run
   past 15k chars; page with read_file offsets. Marketing tables, security claims and
   platform promises are the things step 4 will test.
   Clone pattern: `GIT_TERMINAL_PROMPT=0 git -c credential.helper='' clone --depth 1 <url> <dir>`
   with `workdir` set to the scratch dir (avoids MSYS path translation on Windows).
4. Claim verification in source — the core of the job. For each headline claim, read
   the code that implements it: crypto/KDF and key material, where secrets are stored,
   what the binary talks to on the network, permission handling, feature/platform
   gating. When claim and code disagree, the code wins — cite `path.rs:line`.
   Checklist: `references/claim-verification-checklist.md`.
5. Platform reality check against THIS machine (user is on Windows): does the installer
   branch for Windows at all, are permission hardenings `#[cfg(unix)]` no-ops, are
   agent-integration paths hardcoded to unix locations (`~/.hermes` vs the real
   `%LOCALAPPDATA%\hermes`, active profile `default` not `free`)? Report what actually
   works here, including the install path you would use on this OS.
6. Deliver in order: 用法 (concrete commands in first-use order) → 优势 (verified) →
   劣势/风险 (verified) → 结论 (worth using for X / not for Y; harder-model
   alternatives when the domain is secrets/credentials).
7. Criterion-driven alternative shortlist (user names a quality bar like "安全模型要好",
   usually after an earlier review): group the field by the MECHANISM that decides the
   criterion — for secrets, the KEK/trust boundary (OS keystore / passphrase+KDF /
   hardware / cloud vault; "self-made key" is its own group) — give one verified evidence
   line per candidate, list explicitly what you did NOT verify, and tie each group back to
   the weaknesses found in the earlier review. Search hits alone rank low-star newcomers:
   add known-name mature projects and say which candidates came from where. Domain depth
   for secrets/credential tooling (all three axes): `references/secrets-tool-evaluation.md`.
8. Axis drill-down rounds (跨平台兼容性, agent 交互适应性, …): answer each new axis as a
   one-row-per-tool matrix over the SAME shortlist — no re-discovery. Reuse the scratch
   reads dir (fetched READMEs, release asset lists, doc pages) so a new round only pays
   for its axis-specific fetches; every cell keeps the step-4 evidence standard. Per-axis
   procedures: `references/secrets-tool-evaluation.md`.

## Output contract

- Chinese, plain text — the CLI renders no markdown; no headers/bold/fences, layout via
  blank lines, dashes and indentation only.
- Evidence per non-obvious claim: `file.rs:line`, an exact `gh api` field, or command
  output. "README says X" alone is half a statement — pair it with what the code does.
- State openly when marketing is overstated (a "military-grade" guard that is only
  procedural, a "zero network" tool whose source greps out a page of provider API
  endpoints, an OS that is second-class behind the claim). No cheerleading, no
  two-sided hedging to avoid a verdict.
- Say what you did NOT do ("只做了源码审查，没安装") and offer the next concrete step.
- Project-specific findings (version numbers, star counts, contributor names, dates)
  belong in the answer only — never persisted into this skill.

## Pitfalls

- A README security table is a claim, not evidence. At minimum identify where each key
  comes from and whether every read path has a gate; the full trap list is in
  `references/claim-verification-checklist.md`.
- `#[cfg(unix)]` / `chmod`-style hardening is a no-op on Windows — never repeat it back
  as active protection.
- Commit count is not health; count distinct contributors first.
- Separate "it works" from "as marketed": a tool can be genuinely fine while specific
  claims about it are false, and the review must say both.
- "Agent-ready" inverts easily: an agent-connector that injects skill/rule text telling the
  agent to run a plaintext-read command when convenient has made its own guardrail
  procedural — read the injected skill text and the tool's own agent examples as part of
  the review.