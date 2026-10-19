# Hermes custom-provider per-model metadata

Use this recipe when one named Hermes custom provider serves several model IDs with different context windows or capability metadata.

## Configuration shape

Store model-specific limits under the provider entry, not as a global model pin:

```yaml
model:
  provider: custom:gateway-name
  default: model-a
  # No model.context_length when model switches must resolve independently.

custom_providers:
  - name: gateway-name
    base_url: https://gateway.example/v1
    key_env: GATEWAY_API_KEY
    models:
      model-a:
        context_length: 131072
      model-b:
        context_length: 1048576
```

Literal model IDs may contain dots, slashes, colons, or hyphens; they remain ordinary YAML mapping keys.

## Resolution and evidence order

Hermes resolves context length in this order:

1. `model.context_length` global/current-route override.
2. `custom_providers[].models.<id>.context_length`.
3. Persistent discovered metadata.
4. Endpoint model metadata.
5. Provider registries such as Anthropic, OpenRouter, Nous, or models.dev.
6. Family/default fallback.

Therefore, remove `model.context_length` only when the intended contract is per-model switching and a global pin would mask the model map.

Before writing values:

1. Query the provider's `/models` endpoint with the configured credential, but print only matching model IDs and context-related fields. Never print the credential or the full live config.
2. If the endpoint lists models but omits window metadata, resolve each target through Hermes' own `agent.model_metadata.get_model_context_length(...)`, passing the actual provider, base URL, and compatible custom-provider list.
3. Preserve existing explicit per-model overrides unless the user asked to replace them or stronger endpoint evidence proves them stale.
4. Treat the configured value as Hermes' budgeting/compression contract. It does not enlarge the server's actual KV-cache or provider-enforced context window; Ollama/vLLM/proxies must be configured consistently server-side.

## Safe persistence

Use `hermes config set` for ordinary scalar dotted paths. Do **not** use a dotted path to address a mapping key whose literal model ID contains `.`: the CLI's nested-path setter interprets dots as nesting separators.

For a keyed `models:` map or a bulk nested update:

1. Create a timestamped backup of `config.yaml`.
2. Load the raw user configuration, not the defaults-expanded configuration.
3. Modify only the named provider's `models` mapping.
4. Persist through Hermes' official `hermes_cli.config.save_config(...)` path, which uses atomic YAML writing and managed-scope guards.
5. Do not echo API keys or serialize a redacted copy back over the real config.

## Verification

One sufficient verification is:

- parse the persisted YAML;
- assert every requested model has the exact integer `context_length`;
- assert `model.context_length` is absent when per-model selection is intended;
- optionally run Hermes' resolver for each model to prove the runtime sees the same value.

Named-provider session switches use:

```text
/model custom:<provider-name>:<model-id>
```

Global configuration applies to new sessions. Existing sessions must explicitly switch with `/model` or be restarted; do not claim a running session changed merely because the file changed.
