# Robust CSS selector generation for dynamic SPAs

Use this when a page exposes generated CSS-in-JS classes (for example `sc-*` plus a short hash) and the task needs a reusable selector rather than a session-local lookup.

## Generation rule

1. Attach to the exact requested tab and preserve its stable tab ID.
2. Identify the intended node from current DOM evidence.
3. Treat generated class tokens as volatile. They may be used to confirm the current target, but not as the durable anchor.
4. Find stable structural or semantic anchors: application root IDs, landmark tags, direct-child relationships, ARIA/state attributes, and repeated content-unit attributes.
5. Generate the narrowest selector whose result set contains the intended node exactly once.
6. Verify both `count === 1` and object identity with the known target; uniqueness alone can select the wrong element.
7. If the selector is intended to survive different content shapes, test it on at least two representative routes or queries.
8. If a temporary tab is used, close only that run-owned tab and restore the original active tab.

## Structural container pattern

A useful SPA pattern is a direct child of a landmark that contains one or more semantic content units:

```css
#app-root main > div:has(section[tabindex="0"])
```

Build and verify the selector rather than assuming it:

```js
function generateContainerSelector(doc = document) {
  const base = '#app-root main > div';
  const candidates = [...doc.querySelectorAll(base)]
    .filter(el => el.querySelector('section[tabindex="0"]'));

  if (candidates.length !== 1) {
    throw new Error(`Expected one result container, found ${candidates.length}`);
  }

  const selector = `${base}:has(section[tabindex="0"])`;
  const matches = [...doc.querySelectorAll(selector)];
  if (matches.length !== 1 || matches[0] !== candidates[0]) {
    throw new Error('Generated selector failed identity verification');
  }
  return selector;
}
```

When `:has()` is unavailable, keep the structural filtering in JavaScript instead of falling back to generated classes:

```js
const unit = document.querySelector('#app-root section[tabindex="0"]');
const landmark = unit?.closest('main');
const container = landmark
  ? [...landmark.children].find(el =>
      el.matches('div') && el.querySelector('section[tabindex="0"]'))
  : null;
```

## WolframAlpha verified example

For the complete results region, the durable structural selector was:

```css
#__next main main > div:has(section[tabindex="0"])
```

It matched exactly once on both a simple arithmetic query and an indefinite-integral query, despite different result-pod counts. The contemporaneous generated selector also matched once but is only a session-local fallback:

```css
.sc-3dbb5229-3.eFtOHM
```

For individual pods, positional selectors such as `section[tabindex="0"]:nth-of-type(2)` are content-shape dependent. CSS cannot select a heading by text; use DOM filtering or an automation framework's semantic text locator when the pod meaning matters.

## Pitfalls

- Do not infer durability from a generated selector being unique today.
- Do not accept a selector solely because it returns one node; verify it is the intended node.
- Do not use `nth-of-type()` as a semantic contract unless ordering itself is documented and tested.
- Do not claim cross-page robustness after testing only one query shape.
- Do not leave a temporary validation tab active or open.