"""Package the shipped src modules for upload as flat QuantConnect project files.

QC project files live in one flat namespace, so a package-relative import
(`from .intraday_reversion import ...`) cannot resolve there. Rather than
maintain a second, hand-edited copy of each module in `lean/` — which would
drift from the tested source and quietly invalidate every result — this script
does exactly one transformation: it rewrites `from .x import` to `from x import`.

Everything else is byte-identical to what `pytest` exercised, and the manifest
records a sha256 per file so a run's provenance can be checked against the repo.

Output: a gzip+base64 payload split into paste-sized chunks, because uploads go
through same-origin `fetch()` calls typed into the QC project page (the v2 API
needs credentials this environment does not have, and `backtests/create` is
paid-gated anyway — see the ops playbook).

    python scripts/build_qc_upload.py [--chunk 7000] [--out DIR]
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

# Order is documentation: later files import earlier ones.
MODULES = [
    ("src/spread_research/calendars.py", "calendars.py"),
    ("src/spread_research/signals.py", "signals.py"),
    ("src/spread_research/roll_adjustment.py", "roll_adjustment.py"),
    ("src/spread_research/intraday_reversion.py", "intraday_reversion.py"),
    ("src/spread_research/pair_minute_report.py", "pair_minute_report.py"),
    ("lean/research/qc_pair_minute_analysis.py", "main.py"),
]

RELATIVE_IMPORT = re.compile(r"^(\s*from\s+)\.(\w+)(\s+import\s+)", re.MULTILINE)


def flatten(text: str) -> tuple[str, int]:
    """Rewrite package-relative imports to flat ones. Returns (text, n_changed)."""
    out, n = RELATIVE_IMPORT.subn(r"\1\2\3", text)
    leftover = re.findall(r"^\s*from\s+\.", out, re.MULTILINE)
    if leftover:
        raise SystemExit(f"unhandled relative import form: {leftover!r}")
    return out, n


def build() -> dict:
    files, manifest = {}, []
    for src, dest in MODULES:
        path = REPO / src
        raw = path.read_text(encoding="utf-8")
        text, n = flatten(raw)
        files[dest] = text
        manifest.append({
            "src": src, "dest": dest, "bytes": len(text.encode()),
            "sha256_src": hashlib.sha256(raw.encode()).hexdigest()[:16],
            "imports_flattened": n,
        })
    return {"files": files, "manifest": manifest}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=7000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    bundle = build()
    blob = base64.b64encode(
        gzip.compress(json.dumps(bundle["files"]).encode(), 9)).decode()

    out = pathlib.Path(args.out) if args.out else REPO / "data" / "interim" / "qc_upload"
    out.mkdir(parents=True, exist_ok=True)
    chunks = [blob[i:i + args.chunk] for i in range(0, len(blob), args.chunk)]
    for i, c in enumerate(chunks):
        (out / f"chunk_{i:02d}.txt").write_text(c, encoding="utf-8")
    (out / "manifest.json").write_text(
        json.dumps(bundle["manifest"], indent=2), encoding="utf-8")

    for m in bundle["manifest"]:
        print(f"  {m['dest']:<28} {m['bytes']:>6}B  sha={m['sha256_src']}  "
              f"rel-imports flattened={m['imports_flattened']}")
    print(f"\npayload: {len(blob)} b64 chars in {len(chunks)} chunk(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
