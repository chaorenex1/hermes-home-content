#!/usr/bin/env python
"""Login-state probe for the camofox-search profile (read-only).

Prints: store row count, domain buckets, auth-cookie-name presence, and live
logged-in discriminators per site. Never prints cookie values.

Run with the plugin runtime (hermes-agent venv, Python 3.11) and BOTH the
camofox-search repo plugin dir and the hermes-agent tree on PYTHONPATH so
camofox_search + hermes_cli import, e.g.:

  PYTHONPATH="<repo>/plugin;<HERMES_HOME>/hermes-agent" \
    "<HERMES_HOME>/hermes-agent/venv/Scripts/python.exe" \
    scripts/camofox-login-state-check.py [bilibili github google x zhihu ...]

Closes its scratch tab; the profile's holder tab is verified to survive.
"""

from __future__ import annotations

import collections
import json
import sys
import time

try:
    from camofox_search.client import CamofoxClient
    from camofox_search.settings import camofox_api_key, camofox_base_url, camofox_user_id
except ImportError:  # script run without the repo plugin dir on PYTHONPATH
    sys.path.insert(0, r"<USER_HOME>/projects/camofox-search/plugin")
    from camofox_search.client import CamofoxClient
    from camofox_search.settings import camofox_api_key, camofox_base_url, camofox_user_id

READY_TIMEOUT = 15.0
SETTLE_SECONDS = 1.5

SITES = {
    "bilibili": {
        "url": "https://www.bilibili.com/",
        "cookies": ("SESSDATA", "bili_jct"),
        "js": (
            "(()=>{const av=!!document.querySelector('.header-avatar-wrap,.bili-avatar');"
            "const lb=!!document.querySelector('.header-login-entry');"
            "return JSON.stringify({avatar:av,loginEntry:lb})})()"
        ),
        "logged_in": lambda d: bool(d.get("avatar")) and not d.get("loginEntry"),
    },
    "github": {
        "url": "https://github.com/",
        "cookies": ("user_session",),
        "js": (
            "(()=>JSON.stringify({metaUserLogin:!!document.querySelector('meta[name=\"user-login\"]'),"
            "loginLink:!!document.querySelector('a[href=\"/login\"]')}))()"
        ),
        "logged_in": lambda d: bool(d.get("metaUserLogin")),
    },
    "google": {
        "url": "https://www.google.com/",
        "cookies": ("SID",),
        "js": (
            "(()=>{const ac=!!document.querySelector('a[href*=\"myaccount.google.com\"],"
            "a[aria-label*=\"Google Account\"],a[aria-label*=\"Google 帐号\"]');"
            "const si=!!document.querySelector('a[href*=\"ServiceLogin\"]');"
            "return JSON.stringify({accountLink:ac,signIn:si})})()"
        ),
        "logged_in": lambda d: bool(d.get("accountLink")) and not d.get("signIn"),
    },
    "x": {
        "url": "https://x.com/home",
        "cookies": ("auth_token", "ct0"),
        "js": (
            "(()=>JSON.stringify({title:document.title,url:location.href,"
            "switcher:!!document.querySelector('[data-testid=\"SideNav_AccountSwitcher_Button\"]')}))()"
        ),
        "logged_in": lambda d: bool(d.get("switcher")),
    },
    "zhihu": {
        "url": "https://www.zhihu.com/",
        "cookies": ("z_c0",),
        # z_c0 absent from the store is already definitive; the API status is
        # the live check (200 logged in / 401 not). Zhihu DOM selectors rotate.
        "js": (
            "(async()=>{let st=null;try{const r=await fetch('/api/v4/me',{credentials:'include'});"
            "st=r.status;}catch(e){st='err'}"
            "return JSON.stringify({meStatus:st,"
            "signInBtn:!!document.querySelector('[class*=SignFlow],.AppHeader-login')})})()"
        ),
        "logged_in": lambda d: d.get("meStatus") == 200,
    },
}


def main() -> int:
    wanted = [a.lower() for a in sys.argv[1:]] or list(SITES)
    unknown = [s for s in wanted if s not in SITES]
    if unknown:
        print(f"unknown site(s): {unknown}; known: {sorted(SITES)}")
        return 2

    client = CamofoxClient(base_url=camofox_base_url(), api_key=camofox_api_key(), timeout=60)
    uid = camofox_user_id()
    print(f"base_url={camofox_base_url()} user={uid} api_key_set={bool(camofox_api_key())}")
    tab = client.create_tab(uid, "")
    try:
        cookies = client.get_tab_cookies(tab, uid)
        print(f"cookie rows in camofox profile: {len(cookies)}")
        buckets = collections.Counter(
            (c.get("domain") or "").lstrip(".").lower() for c in cookies
        )
        probed_domains = tuple("x.com" if s == "x" else s for s in wanted)
        print("domain buckets (>=10 rows or probed sites):")
        for dom, n in buckets.most_common():
            if n >= 10 or any(p in dom for p in probed_domains):
                print(f"  {dom}: {n}")
        for site in wanted:
            for name in SITES[site]["cookies"]:
                hits = sorted({(c.get("domain") or "") for c in cookies if c.get("name") == name})
                state = hits if hits else "ABSENT (source browser likely not logged in here)"
                print(f"auth cookie {name!r} ({site}): {state}")

        for site in wanted:
            spec = SITES[site]
            t0 = time.time()
            try:
                client.navigate(tab, uid, spec["url"])
                deadline = time.time() + READY_TIMEOUT
                ready = ""
                while time.time() < deadline:
                    ready = str(client.evaluate(tab, uid, "document.readyState", timeout=20))
                    if ready == "complete":
                        break
                    time.sleep(1)
                time.sleep(SETTLE_SECONDS)
                raw = client.evaluate(tab, uid, spec["js"], timeout=30)
                data = json.loads(raw) if isinstance(raw, str) else (raw or {})
                verdict = spec["logged_in"](data) if isinstance(data, dict) else None
                print(
                    f"[{site}] dt={time.time() - t0:.1f}s ready={ready} "
                    f"logged_in={verdict} probe={json.dumps(data, ensure_ascii=False)}"
                )
            except Exception as exc:  # noqa: BLE001 - keep probing other sites
                print(f"[{site}] ERROR: {type(exc).__name__}: {exc}")
    finally:
        try:
            client.close_tab(tab, uid)
        except Exception as exc:  # noqa: BLE001
            print(f"scratch tab close failed: {exc}")
    try:
        remaining = client.list_tabs(uid)
        print(f"tabs left for {uid}: {len(remaining)} (holder tab must survive)")
    except Exception as exc:  # noqa: BLE001
        print(f"holder-tab check failed: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
