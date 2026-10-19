# Dashboard session-token and auth modes

Use this reference when a user asks where the Dashboard token lives, Desktop requests a remote token, or REST/WebSocket access returns 401.

## Identify the auth mode first

| Mode | Credential source | Where to inspect |
|---|---|---|
| Local loopback Dashboard | Ephemeral token generated per server process | Browser DevTools console: `window.__HERMES_SESSION_TOKEN__` |
| Desktop-spawned local backend | Desktop mints the token and passes `HERMES_DASHBOARD_SESSION_TOKEN` to the child process | Process-local only; do not expect it in config or `.env` |
| Self-hosted static-token backend | Operator sets `HERMES_DASHBOARD_SESSION_TOKEN` | Active `$HERMES_HOME/.env` if deliberately configured |
| OAuth/password-gated public bind | Login session cookie / WebSocket ticket | `window.__HERMES_SESSION_TOKEN__` is intentionally absent; use browser sign-in |

The normal `hermes dashboard` path creates a fresh URL-safe token at each server start and injects it into the served SPA HTML. It is not a durable config value and rotates on restart.

## Bounded diagnostic recipe

1. Check whether a server exists with `hermes dashboard --status`.
2. Resolve the active secrets file with `hermes config env-path`; never assume the default profile path.
3. Check only whether `HERMES_DASHBOARD_SESSION_TOKEN` is configured—do not print its value into model-visible output or logs.
4. For a running local Dashboard, have the user open DevTools → Console and evaluate `window.__HERMES_SESSION_TOKEN__` themselves.
5. If the expression is absent, determine whether the bind is OAuth/password gated before treating it as an error.
6. For API scripting, send the token in `X-Hermes-Session-Token`; legacy Bearer support may exist, while WebSocket/query-token behavior is endpoint-specific.

## Pitfalls

- Do not tell users the ephemeral token is stored in `config.yaml` or persisted automatically in `.env`.
- Do not confuse Dashboard authentication tokens with model context/token-usage statistics.
- Do not expose or copy the token on the user's behalf; provide the local retrieval method.
- A token found before restart is stale after restart.
- Public/non-loopback deployments may reject the legacy session-token path entirely when the auth gate is active.
