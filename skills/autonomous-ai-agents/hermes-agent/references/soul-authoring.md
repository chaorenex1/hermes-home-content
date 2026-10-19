# Authoring SOUL.md (identity prompt)

Use when the user wants to write, revise, or review Hermes' identity and
behavior prompt: `SOUL.md` itself, or a design draft that will become it.
Treat it as a prompt contract, not prose. The rules below come from how the
host loads the file and from how this user iterates on the draft.

## How it is loaded

- `$HERMES_HOME/SOUL.md` (default `~/.hermes/SOUL.md`), stable tier,
  replaces `DEFAULT_AGENT_IDENTITY`. It must be self-contained: anything
  the default identity used to supply has to be written out again.
- Loaded by main sessions, gateway, cron, and runs that pass
  `load_soul_identity=True` (adviser / reviewer `agent_loop`).
- **Not loaded by `delegate_task` children.** A rule that only a worker
  could obey is dead text. Write it as a parent obligation ("put X in the
  child prompt") or move it to the project `AGENTS.md`.
- A clean read is not proof of injection. Verify with the host loader under
  the hermes-agent venv: `scripts/soul_load_probe.py` for a candidate file,
  `scripts/soul_deploy_check.py` for the live home. The loader surfaces
  truncation and injection warnings; neither script writes to the live file.
- Loading and behavior are separate claims. The loader proves the body is
  injected whole; only a real sub-run proves a rule changes behavior. Report
  each with its own evidence and leave the untested one unverified.

## Editing a SOUL design draft

The user keeps one at `doc/hermes-soul-draft.md` in the minir-memory repo.

1. Read the whole draft before touching it: chapter index, per-chapter
   bullets, writing constraints, open items. The constraints section is
   binding (this draft: Chinese body, English final, capability-level
   wording such as "when exposed", no `HERMES_HOME` / profile paths /
   ports / project names, no numeric defaults that drift with config).
2. Fetch the authoritative docs page for the chapter before writing: the
   draft is written against live host behavior and drifts out of date.
3. Rewrite the chapter in place as terse bullets, grouped by phase when it
   helps (slice / run / collect), one rule per bullet. Replace the old
   bullets; never append a second copy of an existing rule.
4. Keep the document coherent: update that chapter's row in the chapter
   index (purpose + sources) and add any unresolved question to the open
   items.
5. Report the source facts, the changed bullets, and anything left
   unverified, with the path.

## Writing the final English body

1. Write it to a sibling file (`doc/hermes-soul.md`), one `#` chapter per
   heading, in the draft's order. Do not overwrite the live `SOUL.md` in the
   same step.
2. Drop what the host already injects (tool-use enforcement, execution
   discipline, the Kanban protocol, the skills index) and the draft's own
   meta commentary.
3. Keep identity self-contained: SOUL replaces the default identity, so the
   honesty, evidence, and length rules have to appear in the body.
4. Merge a constraint that now appears twice in two chapters.
5. Probe with `scripts/soul_load_probe.py`: heading count matches the draft,
   no truncation marker, no injection warning, no legacy Bot Mode block.
6. Record the measured word count in the draft's constraints section.
7. Installing is its own confirmed step; see `## Deploying it`.

## Deploying it

`scripts/soul_deploy_check.py <candidate>` does the sequence below and prints
the evidence; `--recover OUT.md` rebuilds the previous body from a dump.

1. Hash candidate and live file first. Equal means the deployment already
   happened: there is nothing to snapshot, and any backup taken now holds the
   new body.
2. Snapshot the live file to `SOUL.md.bak-<timestamp>`, then hash the
   snapshot. If it equals the candidate, stop; that snapshot is not a rollback
   point.
3. Copy the candidate over live, re-hash both, and load the live home through
   the host loader (same venv interpreter, `home_override=$HERMES_HOME`, no
   temp copy). Expect the counts from verification.
4. Report the deployed hash and counts. The next session picks the file up;
   the running session keeps the prompt it started with, so no gateway restart
   is needed and none should be forced mid-session.

Recovering the previous body: the newest
`$HERMES_HOME/sessions/request_dump_*.json` contains the prompt actually sent.
Slice from the first `# Role` to the host paragraph starting "You run on
Hermes Agent" (fallback: `\n# Finishing the job`), then check the chapter and
word counts before trusting it.

## Rechecking a deployed body

The live recheck is one command, not a hand-written probe:
`python scripts/soul_deploy_check.py doc/hermes-soul.md`. Equal hashes mean
nothing is copied and the script loads the live home and prints the counts,
which is the recheck.

- Pass `--home` for a named profile; set `HERMES_SRC` when the source tree
  is not beside `$HERMES_HOME`.
- Read the evidence, not the character count alone: `truncated: false`, the
  expected heading count, first line `# Role`, and no loader warnings. A scan
  hit or a `[...truncated` marker fails the check even when the size matches.
- The live session's own system prompt showing the body corroborates the
  load; it is not the proof. The loader read is.
- Feed the result back into the draft's next-step item with the measured
  counts and what the check covered. Items the loader cannot cover (adviser
  role yielding, the review/clean loop, the diagram rule) stay listed as
  unverified rather than implied passed.
- When the user points at "the verification" in a draft, they mean that
  next-step block: re-run the load check, re-check the host-source claims it
  rests on, record the evidence, and name what remains. Pick the item from
  the draft instead of asking which one.

## Pitfalls

- **Follow the draft's own tool policy while editing it:** read with
  `read_file`, search with `search_files`, and keep file operations out of
  the terminal. This user's SOUL allows a terminal fallback only after a
  dedicated tool fails three times.
- **Attribute host behavior to the code path that owns it.** The SOUL
  decision is `load_soul_identity or not skip_context_files` in
  `agent/system_prompt._identity_parts`, so the caller's flags decide identity.
  Both `delegate_task` children and the adviser `agent_loop` pass
  `skip_context_files=True`; the adviser also passes
  `load_soul_identity=True` and therefore loads SOUL, while a child gets
  `DEFAULT_AGENT_IDENTITY`. Children still receive the `AGENTS.md` chain
  because `tools/delegate_tool_progress._build_child_system_prompt` re-adds it
  with `build_context_files_prompt(..., skip_soul=True)`. Read the caller
  before writing "the host does X".
- **Do not encode child-only behavior in SOUL.** Children never see the
  file; parent-side phrasing is the only correct form.
- **Budget:** the ceiling is soft; the user raises it when rules grow. This
  draft's cap is 2,200 English words, 2,061 measured. Never delete a rule to
  fit a ceiling; only merge the same constraint written twice, keeping the
  rule body. Write the raised ceiling back into the constraints section
  before continuing.
- **Calibrate before estimating:** 6,016 Chinese characters rendered to
  2,061 English words here, about 2.9 chars per word. A 3.8 ratio undershot
  by a third, so measure with the host loader instead of converting.
- **Count words mechanically** (a script) once a load-bearing chunk is
  added; Chinese character counts do not translate 1:1 into English words,
  so an eyeball estimate misleads in both directions.
- **No tension left behind:** when two bullets imply different defaults
  (e.g. "children cannot re-delegate" next to an orchestrator option),
  resolve them in the same edit instead of shipping the contradiction.
- **A backup you did not hash is a hope.** A same-second copy can land on the
  already-written file: one deploy run produced a `SOUL.md.bak-<ts>`
  byte-identical to the new body, useless as a rollback. Hash the snapshot,
  and when it matches the candidate rebuild the old body from a request dump
  instead of claiming a rollback point exists.
- **Deployment is verified, not announced.** `cp` returning success proves
  nothing; the proof is live hash == candidate hash plus a live-loader read
  with the expected word and heading counts.
