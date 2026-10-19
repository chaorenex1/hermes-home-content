# Read-Only Index-Stage Conflict Resolution (Rebase Replay Analysis)

Use when a delegated task asks for **semantic conflict resolutions as an artifact** — per-hunk merge recommendations, duplicate hazards, targeted test commands — with explicit **no-edit / no-stage / no-mutate** constraints during an in-flight interactive rebase. Typical trigger: an ultrawork/delegated subagent task saying "Produce exact semantic resolutions for every conflict hunk in <files>... Read-only only: do not edit/stage/mutate."

## Workflow

### 1. Establish the stage model first

`git ls-files -u` gives the authoritative conflict inventory. Stage semantics during a rebase replay:

- **stage 1** = merge base (common ancestor of the two sides),
- **stage 2** = current rebased history (`HEAD`, i.e. upstream + previously replayed commits — "ours"),
- **stage 3** = the commit currently being replayed ("theirs").

Do not trust the working-tree conflict markers alone to tell you what changed — the markers show overlap regions, not intent. Extract all three blobs per file:

```bash
mkdir -p /tmp/conf
git show :1:path > /tmp/conf/f_base.py
git show :2:path > /tmp/conf/f_upstream.py
git show :3:path > /tmp/conf/f_local.py
diff /tmp/conf/f_base.py /tmp/conf/f_upstream.py   # what upstream did
diff /tmp/conf/f_base.py /tmp/conf/f_local.py      # what the replayed commit did
```

The base→local diff tells you the replayed commit's *intent*; the base→upstream diff tells you which contracts upstream has since established. Cross-check the replayed commit's own view with `git show <sha>:<path>` and `git show <sha>^:<path>` when stage blobs are ambiguous.

### 2. Classify each hunk before recommending

Each conflict hunk is one of:

- **Pure upstream addition the replayed commit never touched** → keep upstream side entirely; verify nothing in the replayed commit's diff depends on its absence.
- **Pure replayed-commit addition** → keep theirs, but re-validate against current upstream APIs (signatures drift).
- **Both sides changed the same contract** → splice: take upstream's contract shape (call-site conventions, return types, unpack arities), inject the replayed commit's behavioral delta into it. Never take a whole side when the other side's contract is load-bearing elsewhere.
- **Replayed commit deletes something upstream already deleted or superseded** → honor the deletion; keeping HEAD's copy reintroduces dead API.

### 3. Prove contract authority with call sites, not commit messages

Before recommending an unpack shape, signature, or helper, enumerate *every* consumer in the current tree:

```bash
grep -n 'target_function\|target_symbol' <file> | head -40   # all call sites
git show :2:<file> | sed -n 'A,Bp'                            # upstream's side in context
git show :3:<file> | sed -n 'A,Bp'                            # replayed side in context
```

Worked example (this session): replayed commit changed a middleware call to a 2-tuple unpack; upstream's version used a 4-tuple `_managed_values(...)` unpack with `_execution_blocked`. Nine other call sites in the same file (found via grep) used the 4-tuple form, and downstream lines consumed `_execution_blocked` — so upstream's shape was contract-authoritative, and the replayed commit's delta (extra `**plugin_agent_tool_call_kwargs()` inside the `_execute` closure) was spliced in. Taking either side wholesale would have broken the other invariant.

**Mutually-exclusive-looking single lines are usually union splices, not pick-a-winner.** When HEAD adds kwarg A and the replayed commit adds kwarg B at the same position of the same call (or HEAD adds a module-level constant where theirs adds a module-level function, HEAD adds an idempotence guard where theirs adds a boundary-event publish, HEAD leaves a comment where theirs wires a `PluginAgent`), git presents them as an either/or conflict, but the correct resolution is almost always *both lines* — the conflict exists only because both sides edited adjacent context. The authority check is the callee's **current** signature, not the conflict sides:

```bash
git show <upstream-tip>:<callee-file> | sed -n '/^def <callee>/,/^)/p'   # does it accept both kwargs?
```

Worked example: upstream added `detail=next_args.get("detail", "adaptive")` and the replayed commit added `profile=next_args.get("profile")` at the same spot of a `_session_search(...)` call; upstream's `session_search` signature listed both `profile: str = None` (pre-existing) and `detail: str = "adaptive"` (newly appended "to preserve positional compatibility"), so the resolution was both lines in signature order. Same pattern for a docstring-body conflict where HEAD added a `_memory_provider_shutdown` guard and theirs added a `_publish_memory_boundary_event(...)` call before identical trailing code — keep both, theirs first if it must observe pre-guard state, guard otherwise dominating. Never pick a winner between two additive contributions without proving the other side's callee/API no longer accepts or needs it.

**Signature-and-body feature union (the multi-hunk variant).** The same either/or illusion scales up to a whole method: upstream adds params `watermark, watermark_ceiling` + a SQL tail-clone block to `publish_compression_child`, while the replayed commit adds params `parent_tail_messages, boundary_event_id, boundary_payload, timing` + a parent-persist block, a timing write, and an outbox-event insert to the SAME method — git presents signature, docstring, and 3-4 body regions as separate pick-a-winner conflicts, but the correct resolution is a full union of both feature sets because they write disjoint rows (clone into child vs. insert into parent/outbox) and read disjoint inputs. Evidence checklist before recommending union: (1) both param sets are keyword-optional with None defaults (no caller breakage); (2) body blocks don't UPDATE/INSERT the same table rows — trace each block's writes; (3) every call site in the tree (grep the method name) passes the union already or passes only one side's kwargs (defaults cover the other); (4) ordering constraints between blocks (e.g. a `message_high_watermark` SELECT must run after the parent-tail insert but before the outbox insert that consumes it) are satisfiable by interleaving. Then emit the merged signature + block order explicitly in the recommendation, per hunk. Duplicate hazard to flag: if both features can carry the SAME logical message (a tail the summary absorbed AND a watermark clone would copy), call out that callers must pass one mechanism per message, never both, and name the dedupe test that proves it.

### 4. Test-file hunks: check for upstream prune commits

A replayed commit re-adding a test that upstream *deleted* is not automatically a duplicate hazard. Distinguish:

```bash
git log --all --oneline -S 'test_name_here' -- <test-file>
```

- If the deletion commit is a **suite-wide prune** (e.g. "prune low-value tests, N→M functions") and the replayed version has **materially different assertions** (new fixtures, spies on rollback/cleanup paths, new failure modes), keep the replayed version — it pins a contract the pruned test did not.
- If the replayed version is byte-equivalent in behavior to what was pruned, defer to the prune and drop it.
- Also check whether another surviving test already exercises the same path (e.g. a `test_prefetch_merges_results` that implicitly covers `test_builtin_plus_external`) — if so, note the overlap but only act on it when the conflicting block actually contains the duplicated test.

### 5. Deliverable shape for read-only analysis tasks

Per scoped file, per hunk:

1. **Resolution** — exact merged content (code block), not a description of it.
2. **Justification** — which side's contract is authoritative, with call-site or log evidence; why the other side's delta is kept/dropped/spliced.
3. **Duplicate hazards** — explicit "none" or the overlap and why it's safe.
4. **Targeted test commands** — focused `pytest <file>::<class>::<test>` invocations that would exercise each merged hunk, not the whole suite.
5. **Unresolved risks** — forward-looking hazards (e.g. runtime-import circularity, providers with strict `**kwargs` signatures that would reject a newly forwarded kwarg).

## Pitfalls

- **No conflict markers in the worktree ≠ resolved.** During a long-running rebase another worker (or an earlier pass) may have already drafted resolutions into the working tree without staging them. Symptom: `grep -n '<<<<<<<' <file>` finds nothing but `git status --short` still shows `UU` and `git ls-files -u` still lists stage 1/2/3 entries. Do not conclude "no conflicts" and do not trust the worktree content as authoritative — diff the worktree against all three stage blobs (`git show :1/:2/:3:<path>`) to determine whether the existing worktree draft matches your own intended resolution, and report it as a pre-existing draft, not as your edit, when operating read-only.
- **Adjacent-hunk paren ownership.** When an upstream statement (e.g. `monkeypatch.setattr(..., value` — open call, closing paren on a later line) sits directly above a theirs-side block that ends with its own `)`, the conflict marker can end *before* the shared `)`, leaving one bare `)` outside the markers. The correct splice keeps upstream's statement AND theirs' block with exactly one closing `)` after theirs' last argument; blindly keeping both sides yields `))` (syntax error) and dropping the stray yields an unclosed call. After splicing, run a syntax check (`python -m py_compile <file>`) on the merged region.
- **Facade-property conflicts: keep both, don't pick a winner.** When HEAD adds lazy property A (e.g. `subagent_lifecycle`) and the replayed commit adds lazy property B (e.g. `agent`) to the same class `__init__`/property block, the resolution is almost always union — separate instance attributes, separate properties, no shared state. Confirm both backing modules exist in the current tree (e.g. `ls agent/plugin_agent.py agent/subagent_lifecycle.py`) and each has its own test file; that proves neither side supersedes the other.
- **Same import added on both sides with different neighbors.** When HEAD adds `import atexit` and theirs adds `import inspect` to the same import block, the resolution is union sorted with the block — do not drop theirs' import even if the worktree later shows it present via a clean-apply elsewhere; verify usage with `grep -n 'inspect\.' <file>` before concluding it's redundant.
- **Don't edit to "verify".** Read-only means read-only: stage blobs, `git show`, `grep`, and `diff` are sufficient evidence. Running tests against a half-conflicted tree proves nothing about the resolution.
- **Conflict-marker line numbers ≠ hunk boundaries of intent.** A marker pair may cover only part of a logical change; always diff the full stage blobs to catch replayed-commit edits that applied cleanly but interact with the conflicted region (e.g. a changed call-site arity elsewhere in the same function).
- **Whole-side selection is the failure mode.** Even when one side looks "obviously right", verify the other side contributes nothing by reading its base→side diff in full.
- **Runtime (in-function) imports hide circularity.** When splicing an import from the replayed side into an upstream closure, prefer the replayed commit's own placement (often a local import inside the closure) and note residual circular-import risk in the report rather than hoisting it to module top.
- **Windows/MSYS note:** `git show :N:path` stage extraction works fine in git-bash; write temp blobs to `/tmp/...` and read them back with `read_file` when terminal output truncates.
- **`:N:path` fails for non-conflicted files.** `git show :2:path` errors with "path is in the index, but not at stage 2" for any path that isn't itself conflicted (clean stages collapse to stage 0). To inspect the *callee's* current contract (tool signature, helper arity), query the upstream tip commit directly instead: `git show <onto-sha>:<path>` or `git show bceda18df:tools/foo.py`. Don't conclude the file is missing — it just has no stage entries.
- **Terminal truncation hides signatures.** Long `git show ... | sed -n` output gets head+tail truncated exactly where the parameter list lives. Redirect to a temp file (`> /tmp/sig.txt`) and `read_file` it, or read the auto-saved full-output log path that the truncated terminal result prints — never reconstruct a signature from a truncated window.
- **Worktree state can shift under a read-only analyst.** Between your first `git status` and your last inspection, the parent agent (or a sibling worker) may stage resolutions and advance the rebase: `git ls-files -u` goes empty, markers vanish, `:2:`/`:3:` blob reads start failing with "path is in the index, but not at stage N". This is NOT a blocker and NOT a reason to redo the analysis — treat it as a state transition: (1) note the transition explicitly in the deliverable; (2) reconstruct intent from the REBASE_HEAD diff you saved at session start (`git diff <onto> REBASE_HEAD -- <path>`) instead of stage blobs; (3) verify the post-resolution worktree against your recommendations hunk-by-hunk (grep the merged signatures/bodies) and report match or divergence; (4) still emit the per-hunk recommendations — they remain the requested artifact and now double as an audit of whatever was actually staged. Never run mutating commands to "get back" the conflicted state.
- **Rebase state in a linked worktree: `.git` is a file, not a directory.** `ls .git/rebase-merge` fails with "Not a directory" even mid-rebase; the real state lives at `$(git rev-parse --git-dir)/rebase-merge/`. Use `git status` ("interactive rebase in progress") as the authoritative rebase check, never directory listing.
- **Save the REBASE_HEAD diff before anything else.** First minute of analysis: `git diff <onto-sha> REBASE_HEAD -- <scoped-file> > /tmp/<file>.diff` for every scoped file. Stage blobs disappear when the rebase advances, but this diff still shows exactly what the replayed commit intended (surviving deltas AND superseded ones), and it is the only intent evidence that survives the state shift above. Copy it out of `/tmp` if you need it across `execute_code` sandboxes (they don't share MSYS `/tmp`).
