# Local Dev Verification Through a Containerized Browser

Use when the built-in browser or a Playwright container must test a dev server running on the host.

## 1. Reach the page

- Start the dev server with a PTY when a background wrapper reports `stdin is not a tty`; confirm the port answers before navigating.
- Host port example: `8787`
- Container URL: `http://host.docker.internal:8787`
- `http://localhost:8787` from inside the container points at the container itself.

## 2. Make the app's API origin reachable

The page may load, but client requests still target the API base baked into the client bundle, often `http://localhost:PORT`.

Option A: rebuild the client with the public origin.

Option B: run a temporary forwarder inside the browser container:

```bash
docker exec -d <container> node -e "const http=require('http');http.createServer((req,res)=>{const p=http.request({host:'host.docker.internal',port:8787,path:req.url,method:req.method,headers:req.headers},pr=>{res.writeHead(pr.statusCode,pr.headers);pr.pipe(res)});p.on('error',e=>{res.writeHead(502,{'content-type':'text/plain'});res.end('proxy error: '+e.message)});req.pipe(p)}).listen(8787,'127.0.0.1',()=>console.log('proxy up'))"
```

Verify the forwarder from inside the container:

```bash
docker exec <container> node -e "fetch('http://127.0.0.1:8787/').then(r=>console.log(r.status))"
```

Browser-console evaluations may run in an isolated JavaScript world. DOM reads and `dispatchEvent` reach the page, but monkey-patching page globals such as `window`, `XMLHttpRequest`, or `fetch` may not affect the application. Do not rely on a console patch to fix the API origin; use the forwarder, rebuild, or a server-side change. If a patch must work, prove it with a direct request before relying on it.

Cleanup:

```bash
docker exec <container> sh -c "ps -eo pid,args | grep -F 'createServer' | grep -v grep"
docker exec <container> kill <pid>
```

Same-origin is better. The page and its API should use one origin, otherwise the app must allow CORS from the alias.

## 3. Simulate a file upload

File inputs cannot be populated by typing. For an app with a hidden input and a visible picker button:

1. Click the tab or picker button that sets the app's expected file kind, for example Image then Choose image. Click before dispatching `change`, because the app may keep the expected kind in a ref.
2. Set `input.files` from a `DataTransfer` and dispatch a bubbling `change` event:

```js
const input = document.querySelector('input[type=file]')
const dt = new DataTransfer()
dt.items.add(new File([bytes], 'pixel.png', { type: 'image/png' }))
input.files = dt.files
input.dispatchEvent(new Event('change', { bubbles: true }))
```

The handler may clear `input.value` immediately. Read the result from the app DOM, not from `input.files` after dispatch.

3. For a realistic preview, generate a PNG with canvas:

```js
canvas.toBlob((blob) => {
  const file = new File([blob], 'share-card.png', { type: 'image/png' })
  // add to DataTransfer and dispatch change as above
}, 'image/png')
```

## 4. Verify the result

- Check the rendered confirmation panel and copy or embed values in the DOM.
- Fetch the generated direct URL and assert its headers:

```bash
curl -s -D - -o /dev/null http://localhost:8787/<name> | grep -iE 'content-type|content-disposition'
```

- For a binary/raw asset, assert `status` and headers with `fetch(url)` or curl. Navigating the browser to the raw URL may fail, trigger a download, or return a backend-level error; that is not a rendering test.
- Take screenshots after the final build. In CLI sessions, report absolute screenshot paths.

## 5. Cleanup

- Kill the forwarder.
- Kill the dev server process tree, not only its wrapper.
- Confirm the port is closed before finishing.

## 6. Remote deployed site behind a fake-IP resolver

Symptom: browser navigation returns `NS_ERROR_NET_RESET`, `ERR_CONNECTION_RESET`, or a backend-level 500, while a direct request to a real edge IP succeeds. The host's TUN/VPN is returning a fake address (often `198.18.x.x`) inside the container; the app is not down.

1. Prove the deployment with a real edge address before changing the browser:

```bash
curl --resolve <host>:443:<edge-ip> -sS -m 20 -H 'User-Agent: Mozilla/5.0' https://<host>/ | grep -aF '<title>Expected Title'
```

For Cloudflare, any edge IP serves the zone by SNI; use a current one rather than assuming the first address works.

2. Add a temporary hosts entry inside the browser container, not on the host:

```bash
docker exec -u root <container> sh -c 'grep -q "<host>" /etc/hosts || echo "<edge-ip> <host>" >> /etc/hosts'
docker exec <container> node -e "require('dns').lookup('<host>',(e,a)=>console.log(e?e.message:a))"
```

3. Navigate again. The browser keeps the hostname for SNI and Host, but resolves to the edge IP. After the run, restart the container to let Docker regenerate `/etc/hosts`, or remove the line explicitly.

Do not edit the host's system hosts file for a test-only workaround. A container-level navigation failure is not evidence that the deployment is broken; report the curl/edge evidence and the browser limitation separately.
