# Nested Profile Configuration Migration

## Regression sequence

1. Save custom values in two nested sections.
2. Save a partial update to each section.
3. Assert the earlier custom sibling values remain unchanged.
4. Reload and assert equality with the saved effective object.

This proves deep-section merge semantics; a simple new-profile save/load test does not.

## Existing-profile normalization

If a new validator rejects an existing profile:

1. Identify the minimal incompatible key/value without dumping unrelated configuration.
2. Apply the smallest authorized compatibility repair needed for the loader to run.
3. Call the application's atomic configuration writer with an empty or explicit update so it persists the canonical full shape, defaults, alias synchronization, and deprecated-key removal.
4. Reload and assert the resulting effective configuration is identical to the written form.

## Safety switches

For settings that could remove review, optimistic version checks, or persistent audit/loop state:

- Prefer validation rejection unless a specific bounded policy has been approved.
- Test rejected values directly.
- Keep the safety check at the shared configuration boundary so every caller receives the same enforcement.
