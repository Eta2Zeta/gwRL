"""Local, read-only browser viewer and standalone HTML packaging for game replays.

Only explicitly selected campaign replay files and the viewer's fixed assets
are served. This process does not run search, update models, or expose a shell.
"""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import threading
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "web/campaign_viewer"
DEFAULT_DIRECTORY = ROOT / "output/campaign_viewer/replays"
SCHEMA = "campaign-replay-v1"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/model.js": ("model.js", "text/javascript; charset=utf-8")}


def read_replay(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict) or value.get("schema") != SCHEMA
            or not isinstance(value.get("steps"), list) or not isinstance(value.get("initial"), dict)
            or not isinstance(value.get("map"), dict)
            or not isinstance(value["map"].get("nodes"), dict)):
        raise ValueError(f"Not a campaign replay: {path.name}")
    return value


class ReplayRegistry:
    def __init__(self, paths: list[Path], *, live_traces: list[Path] = (), root: int = 0,
                 episode: int = 0, allow_source_drift: bool = False):
        self.paths: dict[str, Path] = {}
        self.live = {}
        self.live_bodies = {}
        self.lock = threading.RLock()
        for path in paths:
            path = path.resolve()
            read_replay(path)
            slug = re.sub(r"[^a-zA-Z0-9_-]", "-", path.stem)[:48] or "replay"
            suffix = hashlib.sha256(str(path).encode()).hexdigest()[:12]
            self.paths[f"{slug}-{suffix}"] = path
        if live_traces:
            from .replay import LiveReplay
            for path in live_traces:
                path = path.resolve()
                identity = "live-" + hashlib.sha256(str(path).encode()).hexdigest()[:12]
                self.live[identity] = LiveReplay(path, root=root, episode=episode,
                    allow_source_drift=allow_source_drift)

    def catalog(self) -> dict:
        entries = []
        for identity, path in self.paths.items():
            value = read_replay(path)
            metadata = value.get("metadata", {})
            entries.append({"id": identity, "title": metadata.get("title", path.stem),
                            "steps": len(value["steps"]), "terminal": bool(metadata.get("terminal")),
                            "origin": metadata.get("origin"), "filename": path.name})
        for identity, source in self.live.items():
            with self.lock:
                value = source.update()
            metadata = value["metadata"] if value else {}
            entries.append({"id": identity, "title": metadata.get("title", "Live self-play · waiting for episode"),
                            "steps": len(value["steps"]) if value else 0,
                            "terminal": bool(metadata.get("terminal")), "live": True,
                            "origin": metadata.get("origin")})
        return {"replays": entries}

    def body(self, identity: str) -> tuple[bytes, str] | None:
        if identity in self.paths:
            body = self.paths[identity].read_bytes()
            return body, '"' + hashlib.sha256(body).hexdigest() + '"'
        if identity in self.live:
            with self.lock:
                source = self.live[identity]
                value = source.update()
                if value is None:
                    raise ValueError("Waiting for the requested episode to begin")
                cached = self.live_bodies.get(identity)
                if cached is None or cached[0] != source.revision:
                    body = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
                    cached = source.revision, body, '"' + hashlib.sha256(body).hexdigest() + '"'
                    self.live_bodies[identity] = cached
                return cached[1:]
        return None


def make_server(paths: list[Path], *, port: int = 8765, live_traces: list[Path] = (),
                root: int = 0, episode: int = 0, allow_source_drift: bool = False) -> ThreadingHTTPServer:
    registry = ReplayRegistry(paths, live_traces=live_traces, root=root, episode=episode,
                              allow_source_drift=allow_source_drift)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            pass

        def _reply(self, status: int, body: bytes, content_type: str, etag: str | None = None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if etag:
                self.send_header("ETag", etag)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            host = self.headers.get("Host", "").partition(":")[0].lower()
            if host not in {"127.0.0.1", "localhost"}:
                self._reply(403, b"Local viewer host required", "text/plain; charset=utf-8")
                return
            path = unquote(urlsplit(self.path).path)
            try:
                if path in STATIC:
                    name, kind = STATIC[path]
                    self._reply(200, (ASSETS / name).read_bytes(), kind)
                elif path == "/api/replays":
                    body = json.dumps(registry.catalog(), ensure_ascii=False, allow_nan=False).encode()
                    self._reply(200, body, "application/json; charset=utf-8")
                elif path.startswith("/api/replays/") and path.count("/") == 3:
                    identity = path.rsplit("/", 1)[1]
                    result = registry.body(identity)
                    if result is None:
                        self._reply(404, b"Unknown recording", "text/plain; charset=utf-8")
                        return
                    body, etag = result
                    if self.headers.get("If-None-Match") == etag:
                        self._reply(304, b"", "application/json; charset=utf-8", etag)
                    else:
                        self._reply(200, body, "application/json; charset=utf-8", etag)
                else:
                    self._reply(404, b"Not found", "text/plain; charset=utf-8")
            except (OSError, ValueError, TypeError, KeyError):
                self._reply(503, b"Recording unavailable or still being written", "text/plain; charset=utf-8")

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def standalone_html(replay: dict) -> str:
    """Package the same viewer with its recording; no server or CDN is needed."""
    if replay.get("schema") != SCHEMA:
        raise ValueError("Expected campaign-replay-v1 data")
    page = (ASSETS / "index.html").read_text()
    css = (ASSETS / "style.css").read_text()
    model = (ASSETS / "model.js").read_text()
    app = (ASSETS / "app.js").read_text()
    app, count = re.subn(r"\Aimport\s+\{[\s\S]*?\}\s+from\s+['\"]\./model\.js['\"];\s*", "", app, count=1)
    if count != 1:
        raise ValueError("Viewer model import no longer matches the standalone packager")
    data = json.dumps(replay, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    data = data.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    script = f"globalThis.CAMPAIGN_REPLAY={data};\n{model}\n{app}"
    script = script.replace("</script", "<\\/script")
    page = page.replace('<link rel="stylesheet" href="./style.css">', f"<style>{css}</style>")
    page = page.replace('<script type="module" src="./app.js"></script>',
                        f'<script type="module">{script}</script>')
    return page


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, action="append", default=[], help="Exported replay JSON; repeat for several games")
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--live-trace", type=Path, action="append", default=[],
                        help="Follow an opt-in replay.jsonl stream; repeat for several runs")
    parser.add_argument("--root", type=int, default=0, help="Parallel game index for live traces")
    parser.add_argument("--episode", type=int, default=0, help="Episode index within that game stream")
    parser.add_argument("--allow-source-drift", action="store_true",
                        help="Permit changed sources, retaining exact rule/context/transition verification")
    parser.add_argument("--port", type=int, default=8765, help="Local port; 0 selects an available port")
    parser.add_argument("--export-html", type=Path, help="Write a standalone page for one --replay and exit")
    args = parser.parse_args(argv)
    paths = args.replay or (sorted(args.directory.glob("*.json")) if not args.live_trace and args.directory.is_dir() else [])
    try:
        if args.export_html:
            if args.live_trace:
                raise ValueError("Export a trace to replay JSON before packaging a standalone page")
            if len(paths) != 1:
                raise ValueError("Standalone HTML needs exactly one replay")
            if args.export_html.exists():
                raise ValueError("Choose a new output path; existing pages are preserved")
            page = standalone_html(read_replay(paths[0]))
            args.export_html.parent.mkdir(parents=True, exist_ok=True)
            with args.export_html.open("x", encoding="utf-8") as handle:
                handle.write(page)
            print(args.export_html.resolve())
            return 0
        server = make_server(paths, port=args.port, live_traces=args.live_trace, root=args.root,
                             episode=args.episode, allow_source_drift=args.allow_source_drift)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Campaign viewer: http://127.0.0.1:{server.server_port}/", flush=True)
    print(f"{len(paths)} recording(s), {len(args.live_trace)} live trace(s). Ctrl-C stops this local server.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
