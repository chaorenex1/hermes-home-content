# MSW + jsdom multipart XHR hangs

## Symptom

- Vitest with jsdom and MSW
- Upload uses `XMLHttpRequest` plus `FormData` containing a `File`
- `request:start`, `request:match`, and `request:end` fire; `response:mocked` and the XHR `load` event never fire
- The upload promise never settles and the UI stays in a pending state

## Cause

In this environment, MSW's XHR interceptor matches the multipart request but does not deliver the mocked response to jsdom's XHR.

## Test-only fix

If the uploader has a fetch fallback, force that path in the affected spec:

```ts
beforeAll(() => {
  vi.stubGlobal("XMLHttpRequest", undefined)
})
```

Restore globals in `afterAll` with `vi.unstubAllGlobals()`.

## Rules

- Keep the production XHR path; verify it once in a real browser.
- Do not rewrite production code to fetch-only just to satisfy jsdom unless fetch-only is the intended behavior.
- This applies to any XHR upload helper that already has a fetch fallback.
