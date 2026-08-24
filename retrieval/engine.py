"""Stage 5 orchestration — evidence retrieval (Architecture Part 11.1).

    AttributionResult + Principal
      -> 0. QUERY CONSTRUCTION   deterministic, from analytical state
      -> 1. STRUCTURED EVIDENCE  exact SQL on changelog / schema log
      -> 2. HARD PRE-FILTER      entitlement, then date, then slice
      -> 3. BM25                 over the candidate pool only
      -> 4. DENSE                cosine over the same candidate rows
      -> 5. RRF FUSION           k=10, fused by rank
      -> 6. COHORT ROLL-UP       many tickets -> one rate statement
      -> 7. CONTRADICTION PASS   deterministic disconfirming signals
      -> RetrievalResult

The single public entry point is `retrieve_evidence(attribution, principal)`.
It consumes deterministic analytical output and returns structured evidence.

It does not know about Streamlit, does not know about LangGraph, and never
calls an LLM - including for query construction. A model that writes its own
search query is a model choosing what evidence it sees, which is exactly the
loop this architecture forbids.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta

from attribution.types import AttributionResult
from retrieval import bm25 as bm25_mod
from retrieval import cohort as cohort_mod
from retrieval import contradiction as contra_mod
from retrieval import corpus as corpus_mod
from retrieval import dense as dense_mod
from retrieval import filters as filters_mod
from retrieval.embeddings import EmbeddingIndex, embed_query, load_index
from retrieval.fusion import DEFAULT_K, reciprocal_rank_fusion
from retrieval.types import (
    CandidateHypothesis,
    EvidenceItem,
    FilterConditions,
    RetrievalConfig,
    RetrievalMode,
    RetrievalQuery,
    RetrievalResult,
    RetrievalTiming,
    SourceType,
)
from security.entitlements import Principal, source_access
from semantic import gateway

DEFAULT_TOP_K = 8

# Cause-bucket vocabularies. Fixed, inspectable and version-controlled - the
# alternative is asking a model to invent search terms, which makes the query
# unreproducible and the ranking unauditable (Part 11.7).
#
# One vocabulary PER BUCKET, not one per driver, and every plausible bucket for
# a driver is searched. The first version of this keyed a single keyword list
# off the dominant LMDI factor, which meant a conversion drop was always
# searched for with payment-failure terms. On Scenario 2 - a South/Apparel
# movement whose real causes are a competitor promotion and a stockout - that
# retrieved "Payment failed at checkout" as the top result and buried the
# actual evidence. The engine had assumed the cause and then found what it
# assumed.
#
# A conversion drop has several genuine mechanisms: checkout can fail, stock
# can run out, a rival can undercut. Retrieval searches all of them and lets
# Stage 6 rank the hypotheses; presupposing one here is how a system finds only
# the evidence it expected to find.
CAUSE_BUCKETS: dict[str, list[tuple[str, list[str]]]] = {
    "conversion_rate": [
        ("internal_product", [
            "payment", "gateway", "checkout", "declined", "timeout",
            "card", "transaction", "failed",
        ]),
        ("internal_inventory", [
            "stock", "stockout", "out of stock", "availability", "sku",
            "inventory",
        ]),
        ("external_competitor", [
            "competitor", "rival", "promotion", "discounting", "price war",
        ]),
    ],
    "orders": [
        ("internal_inventory", [
            "stockout", "out of stock", "inventory", "availability", "sku",
        ]),
        ("external_competitor", [
            "competitor", "rival", "promotion", "discounting", "price war",
        ]),
        ("external_market", ["demand", "seasonal", "festive", "trade press"]),
    ],
    "sessions": [
        ("internal_product", ["outage", "latency", "app", "error", "downtime"]),
        ("external_market", ["campaign", "traffic", "search", "referral"]),
    ],
    "average_order_value": [
        ("internal_pricing", ["pricing", "discount", "promotion", "basket"]),
        ("external_competitor", ["competitor", "rival", "price war"]),
    ],
    "net_realisation": [
        ("internal_quality", ["refund", "return", "defect", "quality", "damaged"]),
        ("internal_pricing", ["discount", "chargeback", "credit note"]),
    ],
}

# Used when the driver is unknown, so retrieval still runs rather than
# searching with nothing but the slice name.
GENERIC_BUCKET = ("unknown", ["issue", "problem", "failure", "delay", "complaint"])

DIMENSION_TERMS = ("region", "channel", "segment", "product_category")


# --------------------------------------------------------------------------
# 0. query construction
# --------------------------------------------------------------------------
def _base_terms(attribution: AttributionResult) -> tuple[list[str], dict]:
    """Slice, KPI and month - the part of the query every bucket shares."""
    terms: list[str] = []
    slice_filter: dict[str, list[str]] = {}

    top = attribution.top_slice
    if top is not None:
        slice_filter[top.dimension] = [top.element]
        terms.append(str(top.element))

    for dim, values in (attribution.slice or {}).items():
        slice_filter.setdefault(dim, list(values))
        terms.extend(str(v) for v in values)

    terms.append(attribution.kpi_id.replace("_", " "))
    if attribution.movement.event_start:
        terms.append(attribution.movement.event_start.strftime("%B"))
    return terms, slice_filter


def _dedupe(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for term in terms:
        key = term.lower()
        if key and key not in seen:
            seen.add(key)
            ordered.append(term)
    return ordered


def build_queries(attribution: AttributionResult) -> list[RetrievalQuery]:
    """One query per plausible cause bucket for the dominant driver.

    Deterministic throughout: the same movement produces the same queries in
    the same order, which is what makes a retrieval result something a judge
    can re-run rather than something they must trust.
    """
    base, slice_filter = _base_terms(attribution)
    driver = attribution.identity.dominant_driver if attribution.identity else None
    buckets = CAUSE_BUCKETS.get(driver or "", [GENERIC_BUCKET])

    movement = attribution.movement
    queries: list[RetrievalQuery] = []
    for bucket_name, keywords in buckets:
        terms = _dedupe(
            base
            + ([driver.replace("_", " ")] if driver else [])
            + list(keywords)
        )
        queries.append(
            RetrievalQuery(
                text=" ".join(terms),
                terms=terms,
                kpi_id=attribution.kpi_id,
                driver=driver,
                slice=slice_filter,
                window_start=movement.event_start,
                window_end=movement.event_end,
                cause_keywords=list(keywords),
                built_from=(
                    f"cause bucket '{bucket_name}' = kpi + slice + dominant "
                    f"LMDI driver + fixed bucket vocabulary (no LLM)"
                ),
            )
        )
    return queries


def build_query(attribution: AttributionResult) -> RetrievalQuery:
    """The combined query, for display and for single-query callers."""
    queries = build_queries(attribution)
    base, slice_filter = _base_terms(attribution)
    driver = attribution.identity.dominant_driver if attribution.identity else None
    all_keywords = [k for q in queries for k in q.cause_keywords]
    terms = _dedupe(
        base + ([driver.replace("_", " ")] if driver else []) + all_keywords
    )
    movement = attribution.movement
    return RetrievalQuery(
        text=" ".join(terms),
        terms=terms,
        kpi_id=attribution.kpi_id,
        driver=driver,
        slice=slice_filter,
        window_start=movement.event_start,
        window_end=movement.event_end,
        cause_keywords=all_keywords,
        built_from=(
            f"union of {len(queries)} cause-bucket queries "
            f"({', '.join(q.built_from.split(chr(39))[1] for q in queries)})"
        ),
    )


# --------------------------------------------------------------------------
# 1. structured evidence — exact SQL, never embedded
# --------------------------------------------------------------------------
def structured_evidence(
    principal: Principal,
    window_start: date,
    window_end: date,
    *,
    upstream_tables: list[str] | None = None,
    services: list[str] | None = None,
) -> list[EvidenceItem]:
    """Deploy changelog and schema changes, by deterministic filter.

    These have exact keys - a deploy has a service and a timestamp, a schema
    change has a table and a column - so an exact join is both cheaper and
    correct. Embedding them would replace it with an approximate match, and on
    Scenario 7 the schema-change row is the *answer*: retrieving it by cosine
    similarity would be a worse system that happened to work.
    """
    items: list[EvidenceItem] = []

    rows, reason = gateway.documents("deploy_changelog", principal)
    if not reason:
        for row in rows:
            when = row.get("deployed_at")
            day = when.date() if isinstance(when, datetime) else when
            if day is None or not (window_start <= day <= window_end):
                continue
            if services and str(row.get("service")) not in services:
                continue
            items.append(
                EvidenceItem(
                    evidence_id=str(row["deploy_id"]),
                    source_type=SourceType.DEPLOY_CHANGELOG,
                    source_id="S3",
                    source_table="deploy_changelog",
                    timestamp=when if isinstance(when, datetime)
                    else datetime.combine(day, datetime.min.time()),
                    title=str(row.get("summary") or ""),
                    excerpt=(
                        f"{row.get('service')} / {row.get('component')}: "
                        f"{row.get('summary')} (risk {row.get('risk_level')})"
                    ),
                    full_text=str(row.get("summary") or ""),
                    service=str(row.get("service") or "") or None,
                    category=str(row.get("risk_level") or "") or None,
                    retrieval_mode=RetrievalMode.STRUCTURED,
                    lineage={
                        "source_table": "deploy_changelog",
                        "filter": (
                            f"deployed_at BETWEEN {window_start} AND {window_end}"
                        ),
                        "rollback_at": str(row.get("rollback_at")),
                    },
                )
            )

    rows, reason = gateway.documents("schema_change", principal)
    if not reason:
        for row in rows:
            when = row.get("changed_at")
            day = when.date() if isinstance(when, datetime) else when
            if day is None or not (window_start <= day <= window_end):
                continue
            if upstream_tables and str(row.get("table_name")) not in upstream_tables:
                continue
            items.append(
                EvidenceItem(
                    evidence_id=str(row["change_id"]),
                    source_type=SourceType.SCHEMA_CHANGE,
                    source_id="S1",
                    source_table="schema_change_log",
                    timestamp=when if isinstance(when, datetime)
                    else datetime.combine(day, datetime.min.time()),
                    title=(
                        f"{row.get('change_type')} on "
                        f"{row.get('table_name')}.{row.get('column_name')}"
                    ),
                    excerpt=str(row.get("note") or ""),
                    full_text=str(row.get("note") or ""),
                    category=str(row.get("change_type") or "") or None,
                    retrieval_mode=RetrievalMode.STRUCTURED,
                    lineage={
                        "source_table": "schema_change_log",
                        "table_name": str(row.get("table_name")),
                        "column_name": str(row.get("column_name")),
                        "actor": str(row.get("actor")),
                        "filter": (
                            f"changed_at BETWEEN {window_start} AND {window_end}"
                        ),
                    },
                )
            )

    # Non-routine records first. A changelog window contains mostly routine
    # releases; sorting purely by date buries the one high-risk deploy that
    # the whole structured branch exists to surface.
    def _priority(e: EvidenceItem) -> tuple:
        routine = "routine" in (e.title or "").lower()
        high_risk = (e.category or "").lower() in ("high", "critical")
        return (routine, not high_risk, e.timestamp, e.evidence_id)

    items.sort(key=_priority)
    return items


# --------------------------------------------------------------------------
# the pipeline
# --------------------------------------------------------------------------
def _normalise(text: str) -> str:
    """Collapse whitespace and case so verbatim repeats compare equal."""
    return " ".join(text.lower().split())


def _select_top_k(
    fused: list[tuple[str, float, int]],
    by_id: dict[str, EvidenceItem],
    bm25_lookup: dict[str, tuple[float, int]],
    dense_lookup: dict[str, tuple[float, int]],
    top_k: int,
    mode: RetrievalMode,
    kpi_id: str,
) -> list[EvidenceItem]:
    """Take the top k fused results, collapsing verbatim duplicates.

    Generated support tickets for one incident are frequently identical
    sentences, and without this the entire result list is eight copies of
    "Payment failed at checkout". That is not a ranking problem - the ranking
    is right - it is a presentation-of-evidence problem: eight identical
    documents carry the information of one, and they crowd out the CRM note or
    market event that would have said something new.

    The volume is not lost. It is exactly what the cohort roll-up reports, and
    the suppressed ids stay on the representative item for drill-down.
    """
    representatives: dict[str, EvidenceItem] = {}
    order: list[str] = []

    for doc_id, rrf_score, rrf_rank in fused:
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        key = _normalise(doc.full_text)

        if key in representatives:
            rep = representatives[key]
            rep.duplicate_count += 1
            rep.duplicate_ids.append(doc_id)
            continue

        item = doc.model_copy()
        if doc_id in bm25_lookup:
            item.bm25_score, item.bm25_rank = bm25_lookup[doc_id]
        if doc_id in dense_lookup:
            item.dense_score, item.dense_rank = dense_lookup[doc_id]
        item.rrf_score = rrf_score
        item.rrf_rank = rrf_rank
        item.retrieval_mode = mode
        item.relevant_kpi = kpi_id
        representatives[key] = item
        order.append(key)

    # keep the fused ordering, then renumber so ranks are contiguous
    selected = [representatives[k] for k in order[:top_k]]
    for position, item in enumerate(selected, start=1):
        item.rrf_rank = position
    return selected


def retrieve_evidence(
    attribution: AttributionResult,
    principal: Principal,
    *,
    index: EmbeddingIndex | None = None,
    top_k: int = DEFAULT_TOP_K,
    rrf_k: int = DEFAULT_K,
    lookback_days: int = filters_mod.LOOKBACK_DAYS,
    lookahead_days: int = filters_mod.LOOKAHEAD_DAYS,
    hypothesis: CandidateHypothesis | None = None,
    mode: RetrievalMode = RetrievalMode.HYBRID,
) -> RetrievalResult:
    """The one public entry point for Stage 5."""
    t_total = time.perf_counter()

    query = build_query(attribution)
    bucket_queries = build_queries(attribution)
    movement = attribution.movement

    anchor = movement.changepoint_date or movement.event_start
    if anchor is None:
        raise ValueError(
            "attribution carries no changepoint or event window; there is "
            "nothing to date evidence against"
        )
    window_start, window_end = filters_mod.evidence_window(
        movement.changepoint_date,
        movement.event_start,
        movement.event_end,
        lookback=lookback_days,
        lookahead=lookahead_days,
    )

    access = source_access(principal)

    # --- 1. structured evidence ------------------------------------------
    t = time.perf_counter()
    structured = structured_evidence(principal, window_start, window_end)
    structured_ms = (time.perf_counter() - t) * 1000

    # --- 2. hard pre-filter: entitlement FIRST ---------------------------
    # `load_documents` passes the principal to the gateway, which refuses
    # non-permitted sources outright. Restricted documents are therefore never
    # materialised, never indexed into BM25, and never scored - the ordering
    # the entitlement test asserts.
    t = time.perf_counter()
    permitted, withheld = corpus_mod.load_documents(principal)

    conditions = filters_mod.build_conditions(
        slice_filter=query.slice,
        window_start=window_start,
        window_end=window_end,
        allowed_sources=access.allowed_sources,
        denied_sources=access.denied_sources,
    )
    conditions.corpus_size = len(permitted) + sum(
        1 for _ in withheld
    )
    conditions.candidates_after_entitlement = len(permitted)
    conditions.withheld_by_entitlement = len(withheld)
    conditions.withheld_by_source = {
        w.source_type.value: 1 for w in withheld
    }

    candidates = filters_mod.apply(permitted, conditions)
    conditions.candidates_after_metadata = len(candidates)
    filter_ms = (time.perf_counter() - t) * 1000

    if index is None:
        index = load_index()

    config = RetrievalConfig(
        embedding_model=index.model_name,
        embedding_dim=index.embedding_dim,
        corpus_hash=index.corpus_hash,
        rrf_k=rrf_k,
        top_k=top_k,
    )
    timing = RetrievalTiming(filter_ms=filter_ms, structured_ms=structured_ms)

    by_id = {d.evidence_id: d for d in candidates}
    candidate_ids = [d.evidence_id for d in candidates]

    # --- 3/4. BM25 and dense, once per cause bucket -----------------------
    # Every bucket contributes its own ranked list, and RRF fuses across
    # buckets as well as across retrievers. On an ambiguous movement that is
    # what surfaces both sides: the stockout evidence and the competitor
    # evidence each win their own bucket's ranking, and neither is crowded out
    # by whichever one happens to share more words with a single blended query.
    bm25_lists: list[list[str]] = []
    dense_lists: list[list[str]] = []
    bm25_lookup: dict[str, tuple[float, int]] = {}
    dense_lookup: dict[str, tuple[float, int]] = {}

    bm25_index = None
    if mode in (RetrievalMode.HYBRID, RetrievalMode.BM25_ONLY) and candidates:
        bm25_index = bm25_mod.BM25Index(
            candidates, k1=config.bm25_k1, b=config.bm25_b
        )

    for bq in bucket_queries:
        if bm25_index is not None:
            t = time.perf_counter()
            ranked = bm25_index.search(bq.text)
            timing.bm25_ms += (time.perf_counter() - t) * 1000
            bm25_lists.append([d for d, _, _ in ranked])
            for doc_id, score, rank in ranked:
                best = bm25_lookup.get(doc_id)
                if best is None or rank < best[1]:
                    bm25_lookup[doc_id] = (score, rank)

        if mode in (RetrievalMode.HYBRID, RetrievalMode.DENSE_ONLY) and candidates:
            t = time.perf_counter()
            query_vector = embed_query(bq.text, model_name=index.model_name)
            timing.query_embed_ms += (time.perf_counter() - t) * 1000

            t = time.perf_counter()
            ranked = dense_mod.search(
                bq.text, index, candidate_ids, query_vector=query_vector
            )
            timing.dense_ms += (time.perf_counter() - t) * 1000
            dense_lists.append([d for d, _, _ in ranked])
            for doc_id, score, rank in ranked:
                best = dense_lookup.get(doc_id)
                if best is None or rank < best[1]:
                    dense_lookup[doc_id] = (score, rank)

    # --- 5. RRF -----------------------------------------------------------
    t = time.perf_counter()
    lists = [lst for lst in (bm25_lists + dense_lists) if lst]
    fused = reciprocal_rank_fusion(lists, k=rrf_k) if lists else []
    timing.rrf_ms = (time.perf_counter() - t) * 1000

    items = _select_top_k(
        fused, by_id, bm25_lookup, dense_lookup, top_k, mode, attribution.kpi_id
    )

    # --- 6. cohort roll-up ------------------------------------------------
    t = time.perf_counter()
    baseline_start = window_start - timedelta(days=7 * cohort_mod.BASELINE_WEEKS)
    baseline_conditions = filters_mod.build_conditions(
        slice_filter=query.slice,
        window_start=baseline_start,
        window_end=window_start - timedelta(days=1),
    )
    baseline_docs = filters_mod.apply(permitted, baseline_conditions)
    cohorts = cohort_mod.aggregate(
        candidates,
        baseline_docs,
        window_start=window_start,
        window_end=window_end,
        cohort_dimensions={
            k: "/".join(v) for k, v in query.slice.items() if v
        },
    )
    timing.cohort_ms = (time.perf_counter() - t) * 1000

    # --- 7. contradiction pass -------------------------------------------
    contradictions = []
    if hypothesis is None and attribution.top_slice is not None:
        counter = attribution.counterfactual
        hypothesis = CandidateHypothesis(
            hypothesis_id=f"H-{attribution.kpi_id}-{attribution.top_slice.element}",
            statement=attribution.descriptive_statement(),
            cause_bucket="unknown",
            slice=query.slice,
            expected_direction=(
                "decrease" if (movement.pct_delta or 0) < 0 else "increase"
            ),
            cause_date=None,
            changepoint=movement.changepoint_date,
            keywords=query.cause_keywords,
        )
    if hypothesis is not None:
        counter = attribution.counterfactual
        peer_moved = bool(counter is not None and not counter.passed
                          and counter.control is not None
                          and counter.parallel_trend_passed)
        contradictions = contra_mod.analyse(
            hypothesis,
            candidates,
            cohorts,
            peer_moved=peer_moved,
            peer_label=counter.control if counter else None,
            did_estimate_pct=counter.estimate_pct if counter else None,
        )

    timing.total_ms = (time.perf_counter() - t_total) * 1000

    notes: list[str] = []
    if withheld:
        for w in withheld:
            notes.append(
                f"{w.excerpt} - documents from this source were never loaded, "
                f"so they took no part in ranking"
            )

    return RetrievalResult(
        items=items,
        structured_items=structured,
        withheld=withheld,
        query=query,
        filters=conditions,
        config=config,
        timing=timing,
        cohorts=cohorts,
        contradictions=contradictions,
        retrieved_at=datetime.now(),
        persona=principal.role,
        method=(
            f"entitlement -> metadata filter -> {len(bucket_queries)} cause "
            f"bucket(s) -> BM25(k1={config.bm25_k1},"
            f"b={config.bm25_b}) + dense({index.model_name}) "
            f"-> RRF(k={rrf_k}) -> cohort -> contradiction"
        ),
        notes=notes,
    )
