# Local TUN / Proxy Routing for a New Hostname

Use after a Worker deploy when the host browser or a normal `curl` gets a TLS handshake failure or connection reset, but `curl --resolve <host>:443:<edge-ip>` returns the app. The deployment is healthy; the host resolver is returning a TUN fake IP and the local proxy rule set is sending the new hostname to the wrong route.

## Confirm the split

```bash
nslookup <fqdn>        # 198.18.x.x is a TUN fake IP, not a Cloudflare answer
curl --resolve <fqdn>:443:<cloudflare-edge-ip> -sS -m 20 \
  -H 'User-Agent: Mozilla/5.0' -o NUL -w '%{http_code}\n' https://<fqdn>/
curl -sS -m 20 -H 'User-Agent: Mozilla/5.0' \
  -o NUL -w 'http:%{http_code} tls:%{ssl_verify_result}\n' https://<fqdn>/
```

A 200 through `--resolve` plus a failed normal request means local routing, not Cloudflare. On Windows, `-o /dev/null` can produce a spurious `curl: (23)` write error with schannel; use `-o NUL` or a temp file and trust the printed status.

## Find the rules source of truth (Clash Verge)

The generated runtime config under `AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml` is not the place to make the durable edit. It is regenerated on app restart. Find the active profile and its rules profile:

```bash
CFG="$APPDATA/io.github.clash-verge-rev.clash-verge-rev"
sed -n '1,5p' "$CFG/profiles.yaml"                 # current: <uid>
rg -n "rule:|rules:" "$CFG/profiles.yaml"          # option.rules: <rules-uid>
rg -n "DOMAIN-KEYWORD,<apex>,DIRECT" "$CFG/profiles"
```

The rules file has a `prepend:` list. Add an exact hostname rule above the broad keyword rule and keep the broad rule intact for every other subdomain:

```yaml
prepend:
  - 'DOMAIN,<fqdn>,<proxy-group>'
  - 'DOMAIN-KEYWORD,<apex>,DIRECT'
```

`<proxy-group>` must be an existing group that actually reaches the host (for example a general foreign-traffic group). Use the name verbatim from `proxy-groups`, including any emoji. Do not replace a broad `DIRECT` rule globally unless every subdomain under that apex should be proxied.

## Apply and verify

Restart the Clash Verge app so it regenerates the runtime config from the profile. Do not rely on the external controller over `127.0.0.1`; Clash Verge may expose only a Windows named pipe. After restart:

```bash
rg -n "DOMAIN,<fqdn>" "$CFG/clash-verge.yaml" "$CFG/profiles/<rules-uid>.yaml"
curl -sS -m 20 -H 'User-Agent: Mozilla/5.0' \
  -o NUL -w 'http:%{http_code} tls:%{ssl_verify_result}\n' https://<fqdn>/
```

The generated config must show the exact rule before the broad rule. The live request must return 200 with TLS verification 0. Refresh or reopen the browser tab; a tab that already cached the TLS failure may need a hard reload.

## Notes

- The same principle applies to other Clash/Mihomo clients: edit the app's rule profile, put the exact hostname above any broad `DOMAIN-KEYWORD` or `DOMAIN-SUFFIX` rule, then reload the app. Never leave the only fix in a generated runtime file.
- A subscription update can replace the rules profile. Re-check the exact rule after updates.
- For a containerized browser, a temporary `/etc/hosts` entry to a real edge IP is the equivalent workaround; see the `browser-qa` skill's `local-dev-containerized-browser` reference. That workaround does not fix the host browser.
