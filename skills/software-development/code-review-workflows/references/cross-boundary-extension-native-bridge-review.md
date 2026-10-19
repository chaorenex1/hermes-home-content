# Reviewing browser-extension / native-messaging takeover implementations

Condensed checklist for reviewing a Chromium MV3 extension + native-messaging host + local
bridge/registry stack that lets an agent claim tabs in the user's real browser window after a
human gesture. Emerged from reviewing a "current-window takeover" feature (extension action
click → 60s window authorization → claim claimable tabs → task-scoped ownership → release on
cleanup).

## The core desync pattern: two ownership authorities with different lifetimes

These stacks always have TWO ownership authorities, and they fail differently:

- **Extension-side state** (`owners`, `attached sessions`, `revoked tabs`, pending
  authorization) lives in the MV3 **service worker**, which Chromium kills aggressively on
  idle. All of it is wiped on worker restart.
- **Bridge/host-side state** (route registry, task→target bindings, canceled-target set) lives
  in the long-lived host process.

Review by enumerating what each side loses on restart and whether the loss is fail-closed:

- Pending authorization wiped on worker restart → fail-closed (user must click again). Good.
- `owners` map wiped while host registry retains claims → **fail-open into desync**: every op
  on a claimed tab now fails one side or the other, and the recovery path (re-claim) mints
  fresh bindings extension-side that conflict with stale host-side bindings. Both sides end up
  "owning" the tab with different logical IDs/generations → permanently bricked until process
  restart. Look for: re-claim path treating same-task/same-target re-claim with a fresh
  generation as a conflict instead of a generation bump; extension state not rehydrated from
  `chrome.storage.local` on worker startup.

## Authorization token atomicity across awaits

A one-shot authorization (gesture token, pending claim, nonce) must be **consumed before the
first `await`**, not after. If the handler reads the token, then awaits (tabs.query,
getTargets, per-tab target resolution), then nulls the token at the end, two concurrent
requests on the same native port both pass the check — last writer wins in the extension while
first claimer wins in the host registry. Same bricked-desync outcome. Consuming early turns
all later validation failures into fail-closed "click again" errors, which is the safe
direction even when it burns the gesture on a benign failure.

## Fire-and-forget signals over reconnectable transports

Native messaging ports disconnect and reconnect. Any event sent with "postMessage if port
non-null, else drop" semantics (consent refresh, detach notification, revocation) is lost if
the port is down at send time, and the two authorities silently diverge — e.g. user re-consents
extension-side but the host's canceled-target set is never cleared, so attach stays denied
despite the fresh gesture. Check: is the event queued until reconnect, or re-derivable on the
next denied operation? If neither, flag it.

## Acceptance-criteria probes that actually catch things

- Gesture scope: is the authorization bound to the window/tab where the click happened, TTL'd,
  and cleared when that window closes? Is it global mutable state a later click silently
  overwrites?
- Cross-task theft: denied at BOTH layers (extension owner check AND host registry claim
  conflict), not just one — a single-layer check desyncs under restart/race.
- Lifecycle: borrowed (user-owned) tabs released, never closed, on session cleanup; but check
  the single-tab close path too — it often closes the user's real tab while cleanup releases.
  Asymmetry is usually a finding.
- Stale targets: missing borrowed targets must force fresh authorization, not silent re-claim
  or recreation. Verify the "manifest reset → claim path" actually requires a new gesture.
- Limit cliffs: `maxTabs` enforced as a hard whole-window failure ("too many tabs") means users
  over the limit can never claim at all — flag as UX/design cliff.
- Test gaps to expect: worker-restart desync, gesture→consent-restore round-trip, concurrent
  double-claim, failed-claim authorization consumption. These live at the extension/host
  boundary and are rarely covered by Python-only suites.
