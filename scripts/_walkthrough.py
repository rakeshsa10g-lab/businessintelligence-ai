"""Drives the real Streamlit app through all eight scenarios via AppTest.

Not a pytest file — a one-shot script that prints what a human would see, so
the manual walkthrough (Part 24, Part 26) can be verified against real
rendered output rather than trusted from memory. Run directly:

    python scripts/_walkthrough.py
"""
from __future__ import annotations

import io as _io
import pathlib
import sys
import time

sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest

SCENARIOS = ["S1", "S2", "S3", "S4", "S5a", "S5b", "S6", "S7"]
APP_PATH = str(pathlib.Path(__file__).resolve().parents[1] / "app.py")


def _text_of(at) -> str:
    chunks = []
    for md in at.markdown:
        v = md.value
        if v.strip().startswith("<style>"):
            continue
        chunks.append(v)
    for c in at.caption:
        chunks.append(f"[caption] {c.value}")
    for m in at.metric:
        chunks.append(f"[metric] {m.label}: {m.value}")
    return "\n\n".join(chunks)


def run_scenario(sid: str, persona_id: str | None = None) -> dict:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    t0 = time.time()
    at.run()
    if at.exception:
        return {"sid": sid, "ok": False, "exception": str(at.exception[0])}

    sb = at.sidebar.selectbox(key="scenario_id")
    sb.set_value(sid).run()
    if at.exception:
        return {"sid": sid, "ok": False, "exception": str(at.exception[0]),
                "stage": "select scenario"}

    if persona_id:
        pb = at.sidebar.selectbox(key=f"persona_pick_{sid}")
        pb.set_value(persona_id).run()
        if at.exception:
            return {"sid": sid, "ok": False, "exception": str(at.exception[0]),
                    "stage": "select persona"}

    at.sidebar.button[0].click().run()
    if at.exception:
        return {"sid": sid, "ok": False, "exception": str(at.exception[0]),
                "stage": "run analysis"}

    text = _text_of(at)
    elapsed = time.time() - t0
    return {"sid": sid, "ok": True, "text": text, "elapsed": elapsed, "at": at}


def main():
    out_dir = pathlib.Path(__file__).resolve().parent / "_walkthrough_out"
    out_dir.mkdir(exist_ok=True)

    results = []
    for sid in SCENARIOS:
        r = run_scenario(sid)
        results.append(r)
        status = "OK" if r["ok"] else "FAIL"
        print(f"\n{'='*70}\n{sid}  [{status}]  {r.get('elapsed', 0):.1f}s\n{'='*70}")
        if not r["ok"]:
            print(f"  stage: {r.get('stage', '?')}")
            print(f"  exception: {r['exception'][:800]}")
        else:
            (out_dir / f"{sid}.txt").write_text(r["text"], encoding="utf-8")
            print(f"  ({len(r['text'])} chars written to "
                  f"scripts/_walkthrough_out/{sid}.txt)")
            print(r["text"][:900])

    failures = [r for r in results if not r["ok"]]
    print(f"\n\n{'#' * 70}")
    print(f"SUMMARY: {len(results) - len(failures)}/{len(results)} scenarios OK")
    if failures:
        for f in failures:
            print(f"  FAILED: {f['sid']} at {f.get('stage', 'render')}: "
                  f"{f['exception'][:300]}")
    print(f"{'#' * 70}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
