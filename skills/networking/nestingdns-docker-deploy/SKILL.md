---
name: nestingdns-docker-deploy
description: Use when deploying/debugging NestingDNS in Docker.
---

# NestingDNS Docker deployment & debugging

Repo `217heidai/NestingDNS`. Image `217heidai/nestingdns` (Docker Hub). Three-layer DNS:
AdGuardHome entry :4053 (web :3000) -> MosDNS :5053 -> SmartDNS groups :7053 mainland / :8053 gfw / :6053 overseas (web :4000, disabled by default).
Container self-initializes `$HOME/nestingdns/{etc,work,log}` from baked-in `/nestingdns/default` on first start; entrypoint monitors the three daemons and exits the container if any dies.
Env: `TZ`, `SCHEDULE` (cron line for `update.sh` rule refresh, e.g. `"0  4  *  *  *"`). Default web creds root/password — change them.

## README command pitfall (the #1 copy-paste failure)
The README's `docker run` blocks contain `# comments` AFTER the trailing `\` line-continuation characters.
A backslash must be the last char on the line; `-v ...:... \    # 注释` terminates the command at the comment and docker then fails (usually "requires at least 1 argument" because the image name line is also lost in truncated pastes).
Rule: strip every inline comment (or move comments to their own lines) and ALWAYS end with the image `217heidai/nestingdns`.

## Mode selection
- Linux host: `--network host` (README recommended):
```
docker run -d \
    --restart unless-stopped \
    --name nestingdns \
    --network host \
    -v $HOME/nestingdns/etc:/nestingdns/etc \
    -v $HOME/nestingdns/work:/nestingdns/work \
    -v $HOME/nestingdns/log:/nestingdns/log \
    -e TZ=Asia/Shanghai \
    -e SCHEDULE="0  4  *  *  *" \
    217heidai/nestingdns
```
- Docker Desktop (Windows/macOS): `--network host` does NOT bridge container ports to the host OS (verified on Docker Desktop 4.93/Win11: container healthy, but no Windows listener and DNS unreachable). Use the port-mapping mode. In git-bash, convert volume sources with `cygpath -w` (docker.exe cannot take `/c/...` paths):
```
docker run -d \
    --restart unless-stopped \
    --name nestingdns \
    -p 3000:3000 \
    -p 4053:4053 -p 4053:4053/udp \
    -p 5053:5053 -p 5053:5053/udp \
    -p 4000:4000 \
    -p 6053:6053 -p 6053:6053/udp \
    -p 7053:7053 -p 7053:7053/udp \
    -p 8053:8053 -p 8053:8053/udp \
    -v "$(cygpath -w "$HOME/nestingdns/etc")":/nestingdns/etc \
    -v "$(cygpath -w "$HOME/nestingdns/work")":/nestingdns/work \
    -v "$(cygpath -w "$HOME/nestingdns/log")":/nestingdns/log \
    -e TZ=Asia/Shanghai \
    -e SCHEDULE="0  4  *  *  *" \
    217heidai/nestingdns
```

## Windows DNS debugging gotchas (hard-won, do not skip)
- **Windows nslookup cannot query non-53 ports.** `-port=N` and interactive `set port=N` are silently ignored; queries go to :53 and time out — this looks exactly like "container DNS broken" but is a tool artifact. Use `scripts/dnstest.py` (raw socket), or dig inside WSL/a container.
- **Clash/Mihomo TUN interference:** if the box runs a Meta Tunnel (fake-ip pool 198.18.0.0/15, system DNS like 198.18.0.x), stray :53 queries get answered with fake IPs in 198.18.x.x — a misleading "success". Validate answers are real IPs. Queries aimed at the TUN gateway IP (198.18.0.x) do not reach Windows loopback docker-proxy.
- Baseline path test — socat UDP echo (proves Windows->container UDP forwarding):
```
docker run -d --name udptest -p 9999:9999/udp alpine sh -c 'apk add --no-cache socat >/dev/null 2>&1 && exec socat -v UDP-RECVFROM:9999,fork EXEC:cat'
```
then send with a python socket; `docker logs udptest` shows arrivals. Dual TCP+UDP mappings for one port are fine (verified).
- Inspect inside the container netns without touching it:
```
docker run --rm --network container:nestingdns alpine sh -c 'apk add --no-cache bind-tools tcpdump >/dev/null 2>&1; dig @127.0.0.1 -p 4053 www.baidu.com; tcpdump -l -n -i any port 4053'
```
Start the capture and verify the 'listening' banner BEFORE sending test queries from the host.
- Container healthcheck only pgreps the 3 daemons — it does not prove DNS works. Verify functionally.

## Verification
- `python scripts/dnstest.py www.baidu.com 127.0.0.1 4053` -> expect `rcode=0` and real IPs (not 198.18.x).
- TCP variant: append `tcp` as 4th arg. Layer probes: 4053 AdGuard, 5053 MosDNS, 7053 SmartDNS mainland; gfw path: `www.google.com` via 4053/8053.
- Web: `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/login.html` (200 = AdGuard up).
- Post-deploy dirs: `~/nestingdns/etc/conf` (5 config files), `etc/site` (rules), `work/`, `log/`.
