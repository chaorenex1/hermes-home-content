# Orientation Workflow — Worked Example

## The 4-Batch Sequence

### Batch 1: Manifest + Structure + Docs (parallel)

```bash
# Terminal: full file listing
ls -la

# read_file: package.json (or pyproject.toml / Cargo.toml / go.mod)
# → name, description, version, scripts, dependencies, engines

# read_file: .env.example
# → every config knob, grouped by section, with comments = architecture in disguise

# read_file: README.md
# → architecture diagram, pipeline description, quick-start, directory structure

# search_files: AGENTS.md / CLAUDE.md / .cursorrules (may be in parent dir)
# → coding conventions, autonomy directives, commit protocols
```

**Signal from this batch:** tech stack, what the project does, how to run it, config surface, subsystem discovery (subdirectories with their own package.json).

### Batch 2: Schema + Compose + Git log (parallel)

```bash
# read_file: mysql-schema.sql / migrations/
# → every CREATE TABLE = a domain entity. Column names tell the story:
#   - status VARCHAR(32) + is_active TINYINT + in_use TINYINT + locked_at + locked_by = state machine
#   - UNIQUE KEY constraints = identity rules
#   - idx_* indexes = query patterns (what's filtered/sorted)

# read_file: Dockerfile
# → base image (playwright:v1.59.1-noble = headless browser automation)
# → installed packages (python3 + curl_cffi = protocol-level HTTP client)
# → runtime dirs (product_files, debug_screenshots = output artifacts)

# read_file: docker-compose.*.yml
# → multi-role topology (activation / registration / sales)
# → shared external state (remote MySQL IP)
# → volume mounts (what persists vs what's ephemeral)

# terminal: git log --oneline -20 && git branch -a
# → recent commits = current pain points. "feat(phone-reg): ..." × 10 = phone-reg is the active area
```

**Signal from this batch:** domain model, deployment topology, active development area.

### Batch 3: Complexity Centers + Entry Points (parallel)

```bash
# terminal: wc -l on all major source files, sorted ascending
wc -l server.js index.js product_activator.js mysql-store.js register_openai.js oauth_login.js | sort -n
# → server.js=8962, mysql-store.js=8389, index.js=4047, product_activator.js=3421
# → 4 files = 70% of all code. Those are your complexity centers.

# terminal: head -80 of the entry point (server.js)
# → require() graph = module dependencies
# → config constants = retry limits, timeouts, key URLs, API endpoints

# terminal: grep -n "require(" server.js | head -40
# → internal module graph: what depends on what
```

**Signal from this batch:** where to look for any specific feature (file → responsibility mapping), retry/error-handling strategy, external service dependencies.

### Batch 4: Subsystem Deep-Dive (serial, only if asked)

When the user asks "how does flow X work" and X spans a subsystem:

```
1. ls the subsystem dir → its own package.json, server, worker, protocol/, public/
2. read_file subsystem/package.json → its own deps (better-sqlite3 = local SQLite, not shared MySQL)
3. read_file subsystem/server.js (head 60) → its own port, its own DB, its own routes
4. read_file subsystem/worker.js → the orchestrator: spawn child processes, parse stdout markers
5. read_file subsystem/protocol/*.py → the actual business logic (8-step registration flow)
6. read_file the main project's worker that bridges to the subsystem (phone-reg-worker.js)
   → how parent and child communicate: spawn Python, env vars in, stdout markers out
```

**Key pattern: stdout markers.** Subprocess communication via `===RESULT_BEGIN===\n{json}\n===RESULT_END===` is common in these projects. The parent spawns, collects stdout, regex-parses the marker, and proceeds. Understanding this pattern is essential to tracing flow across process boundaries.

## Output: The Architecture Summary

After the 4 batches, synthesize into:

1. **One-sentence positioning** — "ChatGPT Plus batch auto-activation tool"
2. **Tech stack table** — runtime/framework/storage/automation/deployment
3. **Architecture diagram** — ASCII boxes showing module boundaries + data flow arrows
4. **Core modules table** — file → LOC → responsibility
5. **Data model** — key tables and what state machines they encode
6. **Key design patterns** — the non-obvious decisions (asset pool locking, dual-proxy zone gating, error classification retry, subprocess marker protocol)
7. **Risk observations** — giant files, duplicated registration paths, fragile anti-bot dependencies

## Trace a Specific Flow (follow-up question)

When the user asks "how does step X work", produce:

```
| Step | File | Function | API/Action |
|------|------|----------|------------|
| ① Register | register_phone.py | register_phone_via_protocol() | POST /api/accounts/user/register |
| ② Bind email | finalize_phone.py | finalize_phone_via_protocol() | POST /api/accounts/add-email/send |
| ... | ... | ... | ... |
```

Then a numbered step sequence with the actual HTTP calls / DB writes / state transitions.

This table → sequence format is the fastest way for the user to verify you actually traced the code, not guessed.
