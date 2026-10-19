# Hermes user memory-provider CLI registration

For a standalone memory provider installed at `$HERMES_HOME/plugins/<name>/`:

- Do not patch `hermes_cli/main.py` for a provider-specific command.
- Hermes discovers CLI commands only for the active memory provider (`memory.provider: <name>`).
- Add `register_cli(subparser)` in the provider's `cli.py`. Its argument is the already-created `argparse.ArgumentParser` for `hermes <name>`; add nested verbs with `subparser.add_subparsers(...)`.
- Expose `<name>_command(args)` separately. Hermes discovers that function and assigns it as the parser handler after `register_cli` returns; `register_cli` should only build the nested argument tree.
- Never call `PluginContext.register_command()`, `register_cli_command()`, or a custom registry method from `register_cli`. Those are different extension surfaces and the passed argparse object does not implement them.
- The handler must derive the profile home from `hermes_constants.get_hermes_home()`, not require a separate path flag.
- Keep a direct module CLI, if needed, as a separate wrapper for diagnostics.

Minimal contract regression:

```python
parser = argparse.ArgumentParser()
providers = parser.add_subparsers(dest="provider", required=True)
provider_parser = providers.add_parser("example")
register_cli(provider_parser)
assert parser.parse_args(["example", "status"]).command == "status"
```

Verification after a temp-home or live deployment:

1. Ensure `memory.provider` selects the provider.
2. Run `hermes <name> --help` and assert the expected nested verbs are present. A top-level parser that exists but rejects every verb is a failed registration.
3. Run `hermes <name> status`, then `hermes <name> verify`.
4. Before any gateway stop/restart, inspect provider status for nonterminal durable jobs. Wait for bounded quiescence or block the restart rather than interrupting a running phase.
5. Restart the gateway only after quiescence, then verify gateway health, plugin enabled state, provider status, and provider integrity again. Treat a newly failed durable job as a deployment side effect, not as a healthy restart.

This uses Hermes' generic memory-provider CLI discovery and preserves the standalone-plugin/core boundary.
