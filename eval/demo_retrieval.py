"""Deterministic retrieval demo across the required Stage 5 scenarios.

    python -m eval.demo_retrieval           all scenarios
    python -m eval.demo_retrieval --s1      West revenue / conversion
    python -m eval.demo_retrieval --s2      conflicting evidence
    python -m eval.demo_retrieval --s7      schema change, deterministic
    python -m eval.demo_retrieval --persona ops_lead   entitlement contrast

Everything here is reproducible: the query is built from analytical state, the
index carries a corpus hash, and no LLM is involved at any point.
"""

from __future__ import annotations

import sys
import time
from datetime import date

from attribution import engine as att
from data import spec
from detection import engine as det
from retrieval import engine as ret
from retrieval.embeddings import load_index
from retrieval.types import ContradictionDirection, SourceType
from security.entitlements import Principal
from semantic.types import Window

WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
RULE = "=" * 78

PERSONAS = {
    "analytics_lead": Principal(
        user_id="meera", display_name="Meera Rao", role="analytics_lead"
    ),
    "finance_director": Principal(
        user_id="arjun", display_name="Arjun Mehta", role="finance_director"
    ),
    "ops_lead": Principal(
        user_id="priya", display_name="Priya Nair", role="ops_lead",
        user_region="West",
    ),
}

SCENARIOS = {
    "S1": {
        "label": "West revenue / conversion movement",
        "slice": {"region": ["West"], "channel": ["Web", "Mobile App"]},
        "cause_date": date(2026, 7, 12),
        "expect": "payment / gateway evidence",
    },
    "S2": {
        "label": "South x Apparel — conflicting evidence",
        "slice": {"region": ["South"], "product_category": ["Apparel"]},
        "cause_date": date(2026, 6, 2),
        "expect": "both supporting and contradicting signals",
    },
    "S7": {
        "label": "Marketplace rename — schema change",
        "slice": {"channel": ["Marketplace"]},
        "cause_date": date(2026, 6, 14),
        "expect": "schema-change row retrieved deterministically",
    },
}


def _pipeline(scenario_id: str, principal: Principal, index):
    cfg = SCENARIOS[scenario_id]
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=cfg["slice"],
        scenario_id=scenario_id,
    )
    a = att.attribute(
        d, principal, cause_date=cfg["cause_date"], n_resamples=40
    )
    if a.movement.changepoint_date is None and a.movement.event_start is None:
        return d, a, None
    r = ret.retrieve_evidence(a, principal, index=index)
    return d, a, r


def show(scenario_id: str, principal: Principal, index) -> None:
    cfg = SCENARIOS[scenario_id]
    print(RULE)
    print(f"{scenario_id} — {cfg['label']}")
    print(f"persona: {principal.display_name} ({principal.role})")
    print(f"expect : {cfg['expect']}")
    print(RULE)

    d, a, r = _pipeline(scenario_id, principal, index)
    print(f"detection   : {d.outcome.value}  changepoint={d.changepoint_date}")
    print(f"attribution : {a.outcome.value}")
    if r is None:
        print("retrieval   : not run (no dated movement to anchor evidence to)")
        print(RULE)
        return

    print(f"\nquery       : {r.query.text!r}")
    print(f"built from  : {r.query.built_from}")
    print(f"filters     : {r.filters.summary()}")
    print(f"window      : {r.filters.window_start}..{r.filters.window_end}")

    if r.withheld:
        print("\nWITHHELD (never loaded, so never ranked):")
        for w in r.withheld:
            print(f"  - {w.excerpt}")

    print(f"\nSTRUCTURED EVIDENCE ({len(r.structured_items)}) — exact SQL, no embeddings:")
    for item in r.structured_items:
        flag = " <-- SCHEMA CHANGE" if item.source_type is SourceType.SCHEMA_CHANGE else ""
        print(f"  {item.timestamp.date()}  {item.source_type.value:<17}"
              f"{(item.title or '')[:52]}{flag}")

    print(f"\nRETRIEVED ({len(r.items)}) — BM25 + dense fused by RRF:")
    for item in r.items:
        dup = f" (+{item.duplicate_count} near-identical)" if item.duplicate_count else ""
        print(f"  #{item.rrf_rank} {item.source_type.value:<15}"
              f"bm25={item.bm25_score or 0:6.2f}(r{item.bm25_rank or 0:<3}) "
              f"dense={item.dense_score or 0:.3f}(r{item.dense_rank or 0:<3}) "
              f"rrf={item.rrf_score:.4f}")
        print(f"      {(item.title or item.excerpt)[:66]}{dup}")

    if r.cohorts:
        print(f"\nCOHORTS ({len(r.cohorts)}) — the evidence, not the individual tickets:")
        for c in r.cohorts[:5]:
            print(f"  - {c.statement()}")

    if r.contradictions:
        print(f"\nSIGNALS ({len(r.contradictions)}):")
        for s in r.contradictions:
            mark = "SUPPORT " if s.direction is ContradictionDirection.SUPPORTS else "CONTRA  "
            print(f"  {mark}[{s.contradiction_type.value}] strength {s.strength:.2f}")
            print(f"      {s.detail[:88]}")
            print(f"      checked: {s.checked}")

    t = r.timing
    print(f"\nLATENCY (warm model): filter {t.filter_ms:.1f} | structured "
          f"{t.structured_ms:.1f} | query-embed {t.query_embed_ms:.1f} | "
          f"bm25 {t.bm25_ms:.1f} | dense {t.dense_ms:.1f} | rrf {t.rrf_ms:.2f} | "
          f"cohort {t.cohort_ms:.1f} | TOTAL {t.total_ms:.1f} ms")
    print(RULE)
    print()


def main() -> None:
    args = set(sys.argv[1:])
    persona_name = "analytics_lead"
    for name in PERSONAS:
        if f"--persona={name}" in args or name in args:
            persona_name = name
    principal = PERSONAS[persona_name]

    index = load_index()
    # warm the model so the reported latency is steady-state, not a one-off
    # 30-second load. Both numbers matter and conflating them would flatter us.
    t = time.perf_counter()
    ret.embed_query("warmup", model_name=index.model_name)
    print(f"[model warm-up: {(time.perf_counter() - t) * 1000:.0f} ms]\n")

    wanted = [s for s in ("S1", "S2", "S7") if f"--{s.lower()}" in args]
    for scenario_id in wanted or ["S1", "S2", "S7"]:
        show(scenario_id, principal, index)


if __name__ == "__main__":
    main()
