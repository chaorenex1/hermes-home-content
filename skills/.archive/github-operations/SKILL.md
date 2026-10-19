---
name: github-operations
description: "Use for GitHub auth, issues, PRs, reviews, CI, releases."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, git, authentication, repositories, issues, pull-requests, review, ci, releases]
    related_skills: [requesting-code-review]
---

# GitHub Operations

## Overview

Use one class-level workflow for routine GitHub work: establish authentication, resolve the repository identity, then operate on repositories, issues, pull requests, reviews, CI, or releases. Prefer `gh` when authenticated; otherwise use `git` for local operations and the GitHub REST API for remote state.

## When to Use

- Configure GitHub authentication or Git identity.
- Clone, create, fork, configure, or release a repository.
- Create, triage, label, assign, comment on, close, or reopen issues.
- Create, inspect, review, monitor, merge, or repair a pull request.
- Inspect or rerun GitHub Actions.

For pre-commit verification of your own local changes, use `requesting-code-review`; this skill owns GitHub-hosted lifecycle operations.

## Shared Preflight

1. Confirm `git --version`, `gh --version`, and `gh auth status` without printing credentials.
2. Prefer `gh` when authenticated. Otherwise use HTTPS/SSH for Git and an environment-provided token for API calls; never embed a token in logs, responses, or remote URLs.
3. Inside a repository, derive `owner/repo` from `git remote get-url origin` and verify the default/base branch rather than assuming `main`.
4. Check the current branch, worktree status, and remotes before mutating anything.
5. For API writes, verify the returned object number/URL/state after the call.

The reusable environment helper is `scripts/gh-env.sh`. The REST endpoint map is `references/github-api-cheatsheet.md`.

## Authentication

- Existing authenticated `gh` is preferred; `gh auth setup-git` connects Git credentials.
- For interactive setup, use `gh auth login`; never type or request secrets through an agent tool.
- Git-only users may use an OS credential helper or SSH key. Avoid plaintext credential stores and token-bearing remote URLs.
- Verify with `gh auth status`, `git ls-remote`, and configured commit identity. Do not expose credential file contents.

## Repository and Release Operations

Use `gh repo clone/create/fork/view/edit`, `gh secret`, `gh workflow`, and `gh release` when available. With REST, use the matching endpoints from the cheatsheet. Preserve existing remotes and branch protection unless explicitly requested. For releases, verify tag, URL, assets, and draft/published state.

## Issue Lifecycle

1. Read the issue and current labels/assignees before changing it.
2. Create issues from `templates/bug-report.md` or `templates/feature-request.md` when applicable.
3. For triage, classify before applying labels, priority, or assignment.
4. Link work through `Closes #N` / `Fixes #N` only when merge should close the issue.
5. Read back the issue after writes, especially bulk operations.

## Pull Request Lifecycle

1. Start from a current base branch and a purpose-named feature branch.
2. Make and verify changes, commit only authorized paths, and push the branch.
3. Create the PR using `templates/pr-body-feature.md` or `templates/pr-body-bugfix.md`; record the returned PR number and URL.
4. Inspect checks with `gh pr checks` or Actions/check-run APIs. For failures, read exact logs, fix root cause, push, and recheck with bounded attempts. See `references/ci-troubleshooting.md`.
5. Merge only after required checks/reviews pass and the merge strategy is clear. Verify merged state and branch cleanup.
6. Follow `references/conventional-commits.md` when the repository has no stricter convention.

## Hosted Code Review

1. Gather PR metadata, base/head SHAs, changed-file list, checks, and full diff.
2. Check out or fetch the PR when local tests and full-file context are needed.
3. Review correctness, security, tests, performance, compatibility, and docs. Findings cite exact file and line with severity and rationale.
4. Use `references/review-output-template.md`; submit inline comments against valid diff lines and choose `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` by blocking severity.
5. Never submit a review from a diff summary alone; inspect surrounding source and run relevant tests when possible.

## Verification Checklist

- [ ] Authentication method is known without exposing secrets.
- [ ] Repository owner/name and base branch are verified.
- [ ] Local worktree state was inspected before mutation.
- [ ] Every remote write was read back by number, URL, or state.
- [ ] PR checks and review evidence are current for the reviewed SHA.
- [ ] Merge/release actions were verified after completion.

## Pitfalls

- GitHub's `/issues` endpoint also returns pull requests; filter `pull_request`.
- Inline review comments require the current PR head SHA and valid diff-side lines.
- REST combined status and check-runs are separate CI surfaces.
- Do not assume default branch names or organization permissions.
- Never print tokens or parse credential-store contents into output.
