# Ralph Review Composer: attachments and dictation

Use when extending a Desktop `clarify.request` with `kind` `ralph_review` or `ralph_next_round`.

## Boundary

- Desktop owns request-scoped draft, attachment UI, upload progress, and microphone controls.
- Gateway remains authoritative for pending-request ownership, validation, resolution, and Ralph lifecycle transition.
- Preserve the existing string `answer` consumed by `ralph.handle_review()` / `ralph.handle_next_round_input()`; attach structured client data only as an optional RPC field, then normalize it server-side into the answer string.

## Safe response flow

1. Key Desktop review draft/attachments by **`sessionId + requestId`**, never by the main Composer store or session alone.
2. Stage file/image attachments in the owning gateway session before `clarify.respond`:
   - reuse `uploadComposerAttachment()`;
   - remote files use `file.attach` with byte upload;
   - remote images use `image.attach_bytes`.
3. Send `clarify.respond({request_id, answer, attachments})` only after every attachment succeeds.
4. Gateway must accept attachments only when `_pending_prompt_payloads[request_id]` identifies a pending Ralph clarify request; reject malformed entries without setting the pending event.
5. Validate kind, duplicate IDs, control characters, workspace-relative references, and http(s) URLs. Do not echo gateway/client absolute image paths into Ralph feedback.
6. On `clarify.resolved`, clear only the matching request-scoped Desktop draft/attachments and the matching attention state.

## Voice

Use `useVoiceRecorder`, not the full `useComposerVoice` workflow. Voice must transcribe into the review draft and return focus to the review input; it must never auto-submit a review, create a normal prompt, start TTS, or change Ralph state before explicit user confirmation.

## Tests

Cover:

- normal Clarify remains text-only and compatible;
- valid Ralph attachment manifest appends normalized evidence exactly once;
- invalid/non-Ralph attachment manifest does not wake the pending request;
- cross-session drafts cannot leak;
- `clarify.resolved` clears only the matching request;
- Enter/Shift+Enter and IME composition behavior;
- STT inserts editable text without auto-submission.
