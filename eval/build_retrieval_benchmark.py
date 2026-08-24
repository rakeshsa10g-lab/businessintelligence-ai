"""Freeze the labelled retrieval benchmark to disk.

    python -m eval.build_retrieval_benchmark

Labels come from the generator's `planted_for` and `is_decoy` columns, which
record exactly which documents were planted as genuine corroboration for each
injected event and which were planted as decoys. That is the advantage of a
seeded corpus: hand-labelling 20 query/document pairs is normally the
expensive part of building an in-domain eval, and here the answer key already
exists.

Two rules this file exists to enforce:

1. **`planted_for` is a LABEL, never a feature.** It is read here, and in the
   evaluation harness, and nowhere else. `tests/test_retrieval.py` asserts
   that no module under `retrieval/` mentions it - if retrieval could see the
   answer key at query time the whole measurement would be circular.

2. **dev / eval split.** Queries are split so that any future threshold
   tuning happens on `dev` and is reported on `eval`. Nothing in Stage 5 was
   tuned against either: the retriever was built before this file existed.
   The split is here so that the next person to touch a threshold has a
   held-out set to be honest with.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "warehouse.duckdb"
OUT = ROOT / "eval" / "retrieval_benchmark.json"


def _ids(con, sql: str) -> list[str]:
    return [str(r[0]) for r in con.execute(sql).fetchall()]


def build() -> dict:
    con = duckdb.connect(str(DB), read_only=True)

    e1_tickets = _ids(
        con, "SELECT ticket_id FROM support_tickets WHERE planted_for='E1' ORDER BY 1"
    )
    e1_deploy = _ids(
        con, "SELECT deploy_id FROM deploy_changelog WHERE planted_for='E1'"
    )
    e1_decoy_market = _ids(
        con,
        "SELECT event_id_doc FROM market_events WHERE planted_for='E1' AND is_decoy",
    )
    e2_stockout = _ids(
        con, "SELECT note_id FROM crm_notes WHERE planted_for='E2' AND kind='stockout' ORDER BY 1"
    )
    e2_competitor = _ids(
        con, "SELECT note_id FROM crm_notes WHERE planted_for='E2' AND kind='competitor' ORDER BY 1"
    )
    e2_market = _ids(
        con, "SELECT event_id_doc FROM market_events WHERE planted_for='E2' ORDER BY 1"
    )
    e3_vague = _ids(
        con, "SELECT ticket_id FROM support_tickets WHERE planted_for='E3' ORDER BY 1"
    )
    e4_launch = _ids(
        con, "SELECT note_id FROM crm_notes WHERE planted_for='E4' ORDER BY 1"
    )
    e5_schema = _ids(
        con, "SELECT change_id FROM schema_change_log WHERE planted_for='E5'"
    )
    e5_decoy_account = _ids(
        con,
        "SELECT ticket_id FROM support_tickets WHERE planted_for='E5' "
        "AND category='account' ORDER BY 1",
    )
    e5_decoy_delivery = _ids(
        con,
        "SELECT ticket_id FROM support_tickets WHERE planted_for='E5' "
        "AND category='delivery' ORDER BY 1",
    )
    e6_gateway = _ids(
        con, "SELECT note_id FROM crm_notes WHERE planted_for='E6' ORDER BY 1"
    )

    # unrelated documents, well outside every event window - the "irrelevant
    # evidence must not dominate" check
    far_tickets = _ids(
        con,
        "SELECT ticket_id FROM support_tickets WHERE created_at < DATE '2026-03-01' "
        "AND (planted_for IS NULL OR planted_for='') ORDER BY 1 LIMIT 12",
    )
    routine_notes = _ids(
        con,
        "SELECT note_id FROM crm_notes WHERE kind='routine' "
        "AND (planted_for IS NULL OR planted_for='') ORDER BY 1 LIMIT 12",
    )
    con.close()

    def q(
        query_id, split, text, relevant, negatives, *, region=None,
        window=None, source_types=None, note="", mode="unstructured",
    ) -> dict:
        return {
            "query_id": query_id,
            "split": split,
            "query": text,
            "region": region,
            "window_start": window[0].isoformat() if window else None,
            "window_end": window[1].isoformat() if window else None,
            "source_types": source_types or [],
            "relevant_doc_ids": relevant,
            "hard_negative_ids": negatives,
            "retrieval_mode": mode,
            "note": note,
        }

    W_E1 = (date(2026, 6, 28), date(2026, 8, 2))
    W_E2 = (date(2026, 5, 19), date(2026, 6, 23))
    W_E3 = (date(2026, 7, 22), date(2026, 8, 22))
    W_E4 = (date(2026, 7, 6), date(2026, 8, 7))
    W_E5 = (date(2026, 5, 31), date(2026, 7, 5))

    pairs = [
        # ---------------- dev (7) ----------------
        q("D01", "dev", "payment gateway checkout failure West",
          e1_tickets, far_tickets, region="West", window=W_E1,
          note="S1 core: the 34 planted payment tickets"),
        q("D02", "dev", "card declined at payment step",
          e1_tickets, routine_notes, region="West", window=W_E1),
        q("D03", "dev", "competitor promotion apparel discounting",
          e2_competitor + e2_market, far_tickets, region="South", window=W_E2,
          note="S2 side A: competitor"),
        q("D04", "dev", "out of stock core SKUs availability",
          e2_stockout, far_tickets, region="South", window=W_E2,
          note="S2 side B: stockout"),
        # E4's launch notes span North and East, so no region filter: the
        # validator below rejects any query whose filters exclude its own
        # labelled documents.
        q("D05", "dev", "new product launch early feedback",
          e4_launch, routine_notes, window=W_E4),
        q("D06", "dev", "gateway failures escalated by client",
          e6_gateway, routine_notes, region="West", window=W_E1,
          note="E6: CRM notes visible to finance/analytics only"),
        q("D07", "dev", "routine quarterly check-in no issues",
          routine_notes, e1_tickets, window=None,
          note="a query whose answer is the boring documents"),

        # ---------------- eval (14) ----------------
        q("E01", "eval", "transaction error at final step West web",
          e1_tickets, far_tickets, region="West", window=W_E1),
        q("E02", "eval", "gateway timeout on order",
          e1_tickets, routine_notes, region="West", window=W_E1),
        q("E03", "eval", "cannot complete payment repeatedly",
          e1_tickets, e5_decoy_account, region="West", window=W_E1,
          note="hard negatives are E5's coincidental account tickets"),
        q("E04", "eval", "payment gateway routing change deployment",
          e1_deploy, far_tickets, window=W_E1,
          source_types=["deploy_changelog"], mode="structured",
          note="structured: exact filter on deployed_at, never embedded"),
        q("E05", "eval", "rival launches festive discounting early",
          e2_market, far_tickets, region="South", window=W_E2),
        q("E06", "eval", "category price war trade press apparel",
          e2_market, routine_notes, region="South", window=W_E2),
        q("E07", "eval", "buyer flagged aggressive competitor promotion",
          e2_competitor, e2_stockout, region="South", window=W_E2,
          note="hard negatives are the OTHER side of the same event"),
        q("E08", "eval", "repeated out of stock messages during period",
          e2_stockout, e2_competitor, region="South", window=W_E2,
          note="the mirror of E07"),
        q("E09", "eval", "vague slowness complaint East SMB",
          e3_vague, far_tickets, region="East", window=W_E3,
          note="S3: only two thin tickets exist"),
        q("E10", "eval", "channel value renamed marketplace consistency",
          e5_schema, e5_decoy_account + e5_decoy_delivery, window=W_E5,
          source_types=["schema_change"], mode="structured",
          note="S7: the answer is a schema_change_log row, retrieved by "
               "exact filter. The hard negatives are the 12 coincidental "
               "tickets planted to tempt a semantic retriever"),
        # These two ask for the E5 decoys - the tickets planted to tempt a
        # retriever into blaming the schema rename on customer complaints. The
        # decoys deliberately span several regions, so these queries carry no
        # region filter; an earlier version filtered to one region and thereby
        # excluded its own labelled documents from the candidate pool, which
        # `_validate` now catches mechanically.
        q("E11", "eval", "new address disappears after saving",
          e5_decoy_account, e1_tickets, window=W_E5,
          note="decoys are the correct answer to their own query"),
        q("E12", "eval", "order delayed shipment has not moved",
          e5_decoy_delivery, e1_tickets, window=W_E5),
        q("E13", "eval", "new launch category customer interest",
          e4_launch, far_tickets, window=W_E4),
        q("E14", "eval", "client escalated repeated payment failures region",
          e6_gateway, e2_stockout, region="West", window=W_E1),
    ]

    return {
        "version": "1.0.0",
        "description": (
            "In-domain retrieval benchmark for BusinessIntelligence.ai. "
            "Labels derive from the generator's planted_for / is_decoy "
            "columns. planted_for is a label only and is never read by any "
            "module under retrieval/."
        ),
        "n_queries": len(pairs),
        "n_dev": sum(1 for p in pairs if p["split"] == "dev"),
        "n_eval": sum(1 for p in pairs if p["split"] == "eval"),
        "queries": pairs,
    }


def _pool_for(spec: dict, documents: list):
    """The candidate pool a query's own metadata filter produces."""
    from datetime import date as _date

    from retrieval import filters as _filters
    from retrieval.types import FilterConditions as _FC

    conditions = _FC(
        window_start=(
            _date.fromisoformat(spec["window_start"])
            if spec["window_start"] else None
        ),
        window_end=(
            _date.fromisoformat(spec["window_end"])
            if spec["window_end"] else None
        ),
        regions=[spec["region"]] if spec["region"] else [],
    )
    return _filters.apply(documents, conditions)


def _expand_identical_text(bench: dict) -> dict:
    """Documents with byte-identical text are identically relevant.

    The generated corpus uses templates, so "Address not saving / New address
    disappears after save" appears verbatim on 20 tickets in one window while
    only 8 carry `planted_for='E5'`. No retriever can tell those apart - the
    text is the same - so marking 8 relevant and 12 not measures luck rather
    than retrieval. Relevance is a property of the document, and identical
    documents are equally relevant.

    This is a correction to the LABELS, not to the retriever, and it is
    applied uniformly to every query rather than to the ones that scored
    badly. It is also a real limitation of a synthetic corpus, and is reported
    as one.
    """
    from retrieval import corpus as _corpus

    documents, _ = _corpus.load_documents()
    by_text: dict[str, list[str]] = {}
    for doc in documents:
        by_text.setdefault(" ".join(doc.full_text.lower().split()), []).append(
            doc.evidence_id
        )
    by_id = {d.evidence_id: d for d in documents}

    added = 0
    for spec in bench["queries"]:
        if spec["retrieval_mode"] == "structured":
            continue
        relevant = set(spec["relevant_doc_ids"])
        negatives = set(spec["hard_negative_ids"])

        # Only twins inside the query's own candidate pool count. A document
        # the filter excludes is not a candidate, so calling it relevant would
        # make the benchmark unanswerable by construction - which is exactly
        # what _validate refuses.
        in_pool = {d.evidence_id for d in _pool_for(spec, documents)}

        expanded = set(relevant)
        for doc_id in relevant:
            doc = by_id.get(doc_id)
            if doc is None:
                continue
            key = " ".join(doc.full_text.lower().split())
            expanded.update(t for t in by_text.get(key, []) if t in in_pool)
        # never let an expansion swallow a document already labelled negative
        expanded -= negatives
        added += len(expanded) - len(relevant)
        spec["relevant_doc_ids"] = sorted(expanded)

    bench["identical_text_expansion"] = added
    return bench


def _validate(bench: dict) -> list[str]:
    """A labelled document the query's own filters exclude is unanswerable.

    This check exists because two queries shipped that way: they filtered to
    one region while their labelled documents spanned three, so every
    retriever scored zero on them and the number looked like a retrieval
    failure rather than a benchmark bug. A benchmark that can be failed by
    construction measures nothing.
    """
    from datetime import date as _date

    from retrieval import corpus as _corpus
    from retrieval import filters as _filters
    from retrieval.types import FilterConditions as _FC

    documents, _ = _corpus.load_documents()
    by_id = {d.evidence_id: d for d in documents}
    problems: list[str] = []

    for spec in bench["queries"]:
        if spec["retrieval_mode"] == "structured":
            continue                      # not in the embedded corpus by design
        conditions = _FC(
            window_start=(
                _date.fromisoformat(spec["window_start"])
                if spec["window_start"] else None
            ),
            window_end=(
                _date.fromisoformat(spec["window_end"])
                if spec["window_end"] else None
            ),
            regions=[spec["region"]] if spec["region"] else [],
        )
        missing = [
            doc_id for doc_id in spec["relevant_doc_ids"]
            if doc_id in by_id and not _filters.matches(by_id[doc_id], conditions)
        ]
        if missing:
            problems.append(
                f"{spec['query_id']}: {len(missing)} labelled document(s) are "
                f"excluded by the query's own filters, e.g. {missing[:3]}"
            )
    return problems


def main() -> None:
    bench = _expand_identical_text(build())
    problems = _validate(bench)
    if problems:
        print("BENCHMARK IS UNANSWERABLE AS WRITTEN:")
        for line in problems:
            print(f"  {line}")
        raise SystemExit(1)
    OUT.write_text(json.dumps(bench, indent=2), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  {bench['n_queries']} queries "
          f"({bench['n_dev']} dev, {bench['n_eval']} eval)")
    total_rel = sum(len(p["relevant_doc_ids"]) for p in bench["queries"])
    total_neg = sum(len(p["hard_negative_ids"]) for p in bench["queries"])
    print(f"  {total_rel} relevant labels, {total_neg} hard negatives")
    print(f"  {bench['identical_text_expansion']} labels added by "
          f"identical-text expansion")
    thin = [p["query_id"] for p in bench["queries"] if not p["relevant_doc_ids"]]
    if thin:
        print(f"  WARNING: queries with no relevant documents: {thin}")


if __name__ == "__main__":
    main()
