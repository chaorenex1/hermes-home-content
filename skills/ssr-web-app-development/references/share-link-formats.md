# Share Link and Embed Formats

Use when a web app lets users share uploaded text, images, or files and must offer a direct link, an HTML embed, and a Markdown snippet.

## Classify the content first

Prefer the browser-provided MIME type, then the filename extension, then an explicit editor language. Return one kind and drive both the UI label and all snippets from it.

- `image/*` or an image extension: image
- `video/*` or a video extension: video
- `audio/*` or an audio extension: audio
- Markdown extension or editor language `markdown`: markdown
- Text editor content with no filename: text
- Anything else: file

A text paste with a filename such as `notes.py` is still a text paste: the editor mode is the source of truth, not the extension. A `.md` filename or `markdown` language selects the rendered-article route.

## URL roles

Keep the three URLs distinct; mixing them produces links that open source when the user expected a viewer, or vice versa.

| URL | Meaning |
|---|---|
| raw | The stored bytes, served with the inferred MIME type and inline disposition |
| viewer | A browser page that renders the paste for humans |
| article | A rendered Markdown/article view, when the app has one |

The direct link is the raw URL for unencrypted content. For client-side encrypted content the raw URL is ciphertext, so the direct link must be the viewer URL with the decryption key in the fragment.

## Embed matrix

| Kind | HTML | Markdown |
|---|---|---|
| image | `<img src="RAW" alt="TITLE" />` | `![TITLE](RAW)` |
| video | `<video src="RAW" controls></video>` | `[TITLE](RAW)` |
| audio | `<audio src="RAW" controls></audio>` | `[TITLE](RAW)` |
| file | `<a href="RAW" target="_blank" rel="noopener noreferrer">TITLE</a>` | `[TITLE](RAW)` |
| markdown | `<iframe src="ARTICLE" title="TITLE" loading="lazy" style="width:100%;height:600px;border:0"></iframe>` | `[TITLE](ARTICLE)` |
| text | `<iframe src="VIEWER" title="TITLE" loading="lazy" style="width:100%;height:420px;border:0"></iframe>` | `[TITLE](VIEWER)` |

Use a real `<iframe>` for text-like content because a remote page cannot fetch and inline it safely. Use an `<img>` for images so the host page gets a native image embed.

## Escaping

- HTML attribute/text values: replace `&`, `<`, `>`, and `"` before interpolation. Never concatenate a user filename into an attribute raw.
- Markdown labels: escape backslashes, `[`, and `]`; otherwise a filename breaks the link syntax.
- URLs produced by the app are already encoded. Do not double-encode them.

## Encryption

When content is encrypted in the browser, remote sites cannot decrypt it. Show only the viewer/direct link, include the key after `#`, and explicitly say that HTML and Markdown embeds are unavailable. Do not silently generate an `<img>` or `<iframe>` snippet that will render ciphertext.

## Server requirements

- Raw image responses need `Content-Type: image/*` and `Content-Disposition: inline`, otherwise `<img>` and direct navigation fail.
- Do not serve uploaded HTML as `text/html`. Convert it to `text/plain` or link to it; an HTML embed of untrusted content is an XSS path.
- Keep CORS on raw assets if the snippets are meant for third-party pages that fetch them.

## UI shape

Offer three formats in one result panel: Link, HTML, Markdown. Put copy on every format and a QR code on the direct link. Compute all snippets from one pure function so the three formats cannot drift; unit-test each kind and the escaping cases.
