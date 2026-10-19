# Advisory side channels

A per-turn advisory reviewer is a different system from post-turn memory reconciliation: it watches
the live turn and tries to change the next action. Design the delivery channel against what the host
can actually do before writing a single prompt.

## Loop

```
turn deltas (text, tool intent, tool results) → reviewer agent (own model, own context, own tools)
  → structured note (text + severity) → emission guard → ledger → delivery channel
```

- The reviewer sees only the delta since its cursor, not the whole transcript. Reset the cursor when
  the host rewrites history (compaction, resume, branch) and seed it to the current length when the
  reviewer is enabled mid-session.
- Filter the reviewer's own injected advice out of the next delta or it reviews itself.
- Give it read-only investigation tools and a small per-update budget (2-3 calls). A reviewer that
  cannot check the workspace reviews prose instead of facts.

## Parameters that matter

| Parameter | Useful default | Why |
|---|---|---|
| review cadence | every turn; optional `agent-end` | interval review batches skipped deltas into the next one |
| notes per update | 4, blockers exempt | prevents a wall of nits; blockers must never be rate-limited |
| severity tiers | nit / concern / blocker | the tier selects the delivery channel, not just wording |
| dedupe key | NFKC, lowercase, strip punctuation | same note reworded is still the same note |
| delivered cache | bounded FIFO (a few thousand) | stops re-raising after the window slides |
| immune turns | 3 after an interrupt | the agent needs room to act before the next interruption |
| catch-up | off by default, bounded wait when on | an unbounded wait stalls the whole turn |

## Delivery channels

| Channel | Requires | Use |
|---|---|---|
| interrupt/steer | host API to abort in-flight work and insert a message | concern/blocker while the agent runs |
| boundary aside | a per-turn injection seam | nits, and anything after a terminal answer |
| visible card | host UI | advice that must stay readable without driving work |
| auto-continue | host continuation hook | blocker after the agent stopped early |

Hosts rarely have all four. Map each tier to the strongest channel the host actually exposes, and
state the loss explicitly in the design instead of pretending the weaker channel is equivalent.
For Hermes, the seam table is `hermes-plugin-development/references/hook-and-middleware-seams.md`:
injected user-message advice per provider attempt, optional tool denial, optional verify nudge; no
interrupt, no new turn.

## Content rules for the reviewer prompt

- Cite only the transcript or tool output it inspected; never restate an error the agent already saw.
- Silence is the default. A note needs a concrete technical risk or an execution failure visible in
  the delta.
- No advice on user intent, scope size, or ceremony; no unsolicited compatibility/deprecation work.
- Blocker requires a cheap check the reviewer actually performed, not a hunch.
- Advice is advice: the driver weighs it, the reviewer never claims authority.

## Recovering a prior-art design from a shipped agent

When the reference implementation is only available as an installed binary:

1. `--version` first. The version decides which upstream tag to read.
2. Search the binary for source-map comments (`// packages/<pkg>/src/...`) to learn the real module
   layout; string scan the surrounding region for config keys, log lines, and constants. These are
   not guesses about behavior, they are the shipped code.
3. Prompt files are usually embedded as opaque blobs (`B:/~BUN/root/<name>-<hash>.md` in Bun
   single-file builds) and are not recoverable as plain text. Do not burn time on the blob: fetch the
   upstream repo's raw files for that version and confirm a few distinctive strings against the
   binary to prove the version matches.
4. Mine the agent's own runtime session directory for reviewer transcripts. They show the exact
   delta format and the advice schema in use, which documentation usually omits.
5. Record which claims come from the shipped binary, which from upstream source, and which from
   runtime transcripts; a version skew between them is normal and belongs in the report.

## Pitfalls

- Injecting advice into the live message stream breaks the prompt prefix and costs cache hits; spend
  it on advice that changes the next action.
- Two reviewers (a post-turn dialectic pass and a per-turn adviser) will duplicate advice unless one
  consumes the other's candidates and the dedupe key is shared.
- A reviewer whose cost is untracked becomes an unbounded bill; meter its own model calls and cap the
  session budget.
- Advice that arrives after the final answer is not worthless: preserve it for the next turn instead
  of dropping it.
