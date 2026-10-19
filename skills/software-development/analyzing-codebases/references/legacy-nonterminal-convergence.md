# Legacy Nonterminal Checkpoint and Loop Convergence

Use this reference when a durable SQLite-backed provider has old `pending`, `planning`, `executing`, `judging`, `running`, or `retryable` rows after crashes, timeouts, migrations, or callback loss.

## Core rule

A persisted status is not proof that work can resume. Resume only when the runtime can reconstruct the exact authorized operation from durable payload and artifacts. A plan name, action enum, snapshot hash, or retry flag alone is insufficient when the real executor was an in-process closure.

Never convert abandoned work to success. Convergence may produce `failed_terminal`, `blocked`, `cancelled`, `stale`, or a fresh bounded attempt; it must not synthesize `completed`.

## Investigation sequence

1. Open the canonical SQLite database with URI `mode=ro`; record UTC snapshot time and database mtime.
2. Check `quick_check`, foreign keys, schema version, and per-table status distributions.
3. Trace startup order before judging residue: filesystem transaction recovery, SQL reconciliation, then worker startup.
4. For each nonterminal entity, inspect deadline/lease, owner identity, registry/config digest, current attempt, persisted payload, referenced artifacts, and append-only events.
5. Map child state to its parent owner: checkpoint → turn job, plan → run, materialization → intent, source transaction → upstream candidate/evidence payload.
6. Take a final compact snapshot because live workers may mutate counts during the audit.

## Resumability proof

Preserve or resume work only if all applicable checks pass:

- deadline remains valid and a lease/owner can be proven inactive or transferred safely;
- current registry/config/template digests match the frozen request;
- complete redacted input payload is durable, not merely hashed;
- all cited files, staged bodies, backups, or candidate versions exist and match hashes;
- an executor/resolver can be reconstructed without process-local closures or cached return values;
- idempotency key includes a fresh recovery generation when a new attempt is intended;
- attempt and wall-clock caps remain;
- the transition can append an audit event atomically with the status update.

If any required proof is missing, terminalize. A valid parent payload may justify a **new** attempt after the underlying defect is fixed, but does not make the abandoned child attempt resumable.

## Common state-domain decisions

| Domain | Safe startup treatment |
|---|---|
| Filesystem transaction `pending` | Roll back with fences, mark failed, preserve newer/manual files. Do not infer commit from metadata. |
| Loop past deadline | `failed_terminal`; terminalize related plan/round rows and append a recovery event. |
| Loop with no persisted executor payload | Terminalize even when `plan_json` exists. |
| Turn/extraction job `running` | Requeue only if persisted redacted payload, evidence refs, template hash, prompt version, and retry budget validate. |
| Checkpoint whose parent job is failed/absent | Terminalize as orphaned; preserve referenced candidate IDs but do not promote them. |
| Dialectical/reasoning job with only snapshot hashes | Fail closed; hashes cannot reconstruct transcript or working state. |
| Retrieval intent after restart | Mark stale if superseded; otherwise fail when deadline or continuation owner is gone. Request-scoped outputs should not be delivered to a guessed recipient. |
| Already failed source transaction with no staged/backup artifacts | Keep failed. Retry only by constructing a new transaction from authoritative upstream payload. |

## Deterministic reconciler

Run after source-file recovery and before workers start:

```text
quiesce provider / capture cutoff
→ recover file transactions
→ classify pre-cutoff nonterminal rows
→ CAS status + append audit event
→ verify postconditions
→ start eligible workers
```

Use a stable decision function over `(entity kind, state digest, algorithm version)`. Guard updates with the observed status/version or serialized checkpoint value. Append events only when a transition wins. A second pass over unchanged state must produce zero writes and zero events.

A useful append-only event carries:

- reconciliation ID and algorithm version;
- entity kind/ID;
- before and after status;
- decision and closed reason code;
- before-state digest;
- bounded artifact summary (counts/hashes, never bodies);
- timestamp.

Deduplicate on entity, algorithm version, before-state digest, and decision—not merely startup ID.

## Stop conditions

- no pre-cutoff loop remains nonterminal unless a valid recovery lease and payload proof exist;
- no pending checkpoint has a failed, completed, or missing parent;
- no running job from the quiesced process remains;
- no pending source transaction remains;
- no expired pending/running retrieval intent remains;
- a second reconciler pass is a no-op;
- accepted documents, promoted candidates, committed transactions, and success counts do not increase because of terminalization.

## Windows newline/hash diagnostic

A common false conflict is hashing raw CRLF text, writing it, then verifying with `Path.read_text()` or another universal-newline reader that returns LF-normalized text. Compare the persisted expected hash with both raw and LF-normalized UTF-8 input. If raw matches and normalized does not, use one byte contract end to end: encode once, atomically write bytes, and verify with `read_bytes()`. Do not repair old failed transactions by declaring them committed; fix the byte contract and create a fresh bounded upstream attempt when its payload still exists.

## Required tests

- planning/retryable/executing/judging expiry matrix;
- plan JSON present but executor payload absent;
- resumable payload proof versus missing artifact;
- orphan checkpoint and terminal-checkpoint no-reopen behavior;
- valid running-job requeue versus template/payload drift failure;
- fresh recovery generation avoiding old idempotency collisions;
- dialectical hash-only failure and retrieval owner/deadline failure;
- pending file-transaction rollback and CRLF byte-hash regression;
- CAS race, append-only event dedupe, second-pass no-op;
- no synthetic success or canonical-content mutation;
- full startup order: file recovery → reconciliation → worker dispatch.
