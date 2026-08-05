"""Localhost receiver for QC result JSON (the ops-playbook retrieval route).

Reading results back out of the QC page is the slow, error-prone half of every
run. Slicing `window.__json` through the JS channel truncates near ~1,030 chars
and has silently dropped characters at a slice boundary; the OS-clipboard
bridge needs a trusted gesture and can leave the PREVIOUS run's JSON in place
after a missed copy. Both failure modes are silent, which is why every route
ends in a SHA-256 comparison.

This receiver removes the slicing entirely: the page POSTs the whole payload
once, the script writes it and prints the sha256 it computed over the bytes it
actually stored, and that is compared against the hash the browser computed
over the bytes it actually sent. A mismatch means the transport corrupted
something and the file must not be ingested.

Port 8765 is BLOCKED on this machine; 51735 works.

    python scripts/recv_qc_json.py --out data/raw/qc/nb_quote_smoke.json
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import pathlib
import sys
import threading

PORT = 51735


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="path to write the payload to")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--timeout", type=float, default=900.0,
                    help="give up after this many seconds with nothing received")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = threading.Event()
    state: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n)
            try:
                msg = json.loads(body.decode("utf-8"))
                payload = msg.get("json")
                # Accept both a JSON-encoded string and a raw object.
                text = payload if isinstance(payload, str) else json.dumps(payload)
                data = text.encode("utf-8")
                out.write_bytes(data)
                sha = hashlib.sha256(data).hexdigest()
                state.update(name=msg.get("name", "?"), sha=sha, bytes=len(data))
                resp = json.dumps({"ok": True, "sha256": sha, "bytes": len(data)})
                code = 200
            except Exception as e:                       # noqa: BLE001
                state.update(error=f"{type(e).__name__}: {e}")
                resp = json.dumps({"ok": False, "error": str(e)})
                code = 500
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.encode())
            done.set()

        def log_message(self, *a):                        # silence access log
            pass

    srv = http.server.HTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"listening on http://127.0.0.1:{args.port} -> {out}", flush=True)

    if not done.wait(args.timeout):
        print("TIMEOUT: nothing received", file=sys.stderr)
        return 2
    srv.shutdown()

    if "error" in state:
        print(f"FAILED: {state['error']}", file=sys.stderr)
        return 1
    print(f"received name={state['name']} bytes={state['bytes']}")
    print(f"sha256={state['sha']}")
    print("COMPARE this against the hash the browser computed before ingesting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
