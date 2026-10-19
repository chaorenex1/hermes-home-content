---
name: apple-app-automation
description: "Automate Apple apps and personal data on macOS."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [apple, macos, notes, reminders, find-my, imessage]
---

# Apple App Automation

## Overview

Class-level guide for automating Apple personal-information apps on macOS. Select the app-specific reference, verify local permissions and command availability, make the narrowest requested change, and read back the resulting state.

## App Branches

- **Notes:** use `references/apple-notes.md` for creating, searching, reading, moving, and deleting notes.
- **Reminders:** use `references/apple-reminders.md` for lists, tasks, due dates, completion, and deletion.
- **Find My:** use `references/findmy.md` for device/person location and status workflows.
- **Messages:** use `references/imessage.md` for reading or sending iMessage/SMS through the local Messages account.

## Shared Safety Contract

1. Confirm the requested app, account/list/contact/device, and whether the action is read-only or mutating.
2. Check macOS Automation, Accessibility, Contacts, and Full Disk Access permissions required by the chosen workflow.
3. Resolve ambiguous human names before sending, deleting, moving, completing, or sharing anything.
4. Prefer stable identifiers after discovery; do not infer an identity from the first fuzzy match.
5. For mutations, execute only the requested scope and read the affected object back.
6. Report permission or synchronization uncertainty explicitly; local acceptance does not always prove cloud delivery.

## Verification

- [ ] Correct Apple app and account scope selected.
- [ ] Required macOS permissions available.
- [ ] Ambiguous recipients/items resolved before mutation.
- [ ] Mutation read back from the authoritative app where possible.
- [ ] Delivery/sync status distinguished from local command success.
