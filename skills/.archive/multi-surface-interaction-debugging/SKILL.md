---
name: multi-surface-interaction-debugging
description: Diagnose duplicate, stale, or unresponsive interactive prompts across frontend, gateway, and persisted workflow state.
version: 1.0.0
author: Masía
created_by: agent
---

# Multi-Surface Interaction Debugging

Use when a user reports duplicated interactive cards, prompts that require repeated completion, stale UI after submission, or a mismatch between Desktop and a gateway-backed workflow.

## Evidence-first rule

Do not conclude from JSX/component searches alone. A UI symptom can arise from two renderer mounts, two gateway request lifecycles, or one request whose resolution was not applied.

## Procedure

1. **Identify the exact session.** Inspect the original session state and logs before relying on session history summaries.
2. **Build a request trace.** Correlate `session_id`, request ID, workflow/interaction ID, event type, user response, state-transition result, and retry reason.
3. **Classify the duplicate.**
   - Same request ID + two visible controls: renderer ownership/mount or state-clearing defect.
   - Different request IDs: backend retry/re-emission or duplicate event delivery.
   - One request ID, response accepted, UI remains: client resolution/event-order/state-scope defect.
4. **Inspect terminal state carefully.** A final success record often omits an earlier failed/retried request. Look for request-boundary logs or add temporary structured diagnostics before claiming a retry path caused the issue.
5. **Check static ownership after tracing.** Search all renderer mount points and verify the active runtime revision only after the event trace narrows the suspect boundary.
6. **Add a regression at the responsible seam.** Assert request cardinality and response-to-clear behavior, not merely rendered text.

## Gateway instrumentation contract

For workflow clarify prompts, log or emit these fields together:

```text
session_id, workflow_id, interaction_id, request_id,
event, response_status, transition_status, retry_reason
```

Do not serialize raw machine request payloads into user-facing transcript text. Use a concise lifecycle message and keep request metadata structured.

## Pitfalls

- Treating raw lifecycle text as proof of a duplicate interactive request.
- Treating one final `done` state as proof no earlier retry occurred.
- Concluding a source tree has one mount and therefore runtime cannot show duplicates without checking renderer revision and request IDs.
- Repairing the renderer before knowing whether the server emitted a second request.

## Verification

A diagnosis is complete only when one trace establishes which of these happened: duplicated mount, duplicated request, or unresolved request. A fix must prove a single visible owner per pending request and one user response reaches one terminal or explicitly retried transition.
