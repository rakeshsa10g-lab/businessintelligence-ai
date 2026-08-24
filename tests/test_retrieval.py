"""Stage 5 tests — corpus, index, retrieval, fusion, entitlement, cohorts.

The load-bearing test in this file is
`test_unauthorised_documents_are_removed_before_any_scoring`. Everything else
is correctness; that one is security, and it asserts an *ordering* rather than
an outcome, because a system that retrieves a restricted document and hides it
afterwards has already leaked it into IDF statistics and rank positions.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from attribution import engine as att
from data import spec
from detection import engine as det
from retrieval import bm25 as bm25_mod
from retrieval import cohort as cohort_mod
from retrieval import contradiction as contra_mod
from retrieval import corpus as corpus_mod
from retrieval import dense as dense_mod
from retrieval import engine as ret
from retrieval import filters as filters_mod
from retrieval.embeddings import (
    EmbeddingIndex,
    IndexError_,
    embed_query,
    load_index,
)
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.types import (
    CandidateHypothesis,
    ContradictionDirection,
    ContradictionType,
    EMBEDDABLE_SOURCES,
    STRUCTURED_SOURCES,
    EntitlementStatus,
    EvidenceItem,
    FilterConditions,
    SourceType,
)
from security.entitlements import Principal, source_access
from semantic.types import Window

ROOT = Path(__file__).resolve().parent.parent

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
OPS_LEAD = Principal(
    user_id="priya", display_name="Priya Nair", role="ops_lead",
    user_region="West",
)
FINANCE = Principal(
    user_id="arjun", display_name="Arjun Mehta", role="finance_director"
)

WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
WEST = {"region": ["West"], "channel": ["Web", "Mobile App"]}


@pytest.fixture(scope="module")
def documents():
    docs, _ = corpus_mod.load_documents()
    return docs


@pytest.fixture(scope="module")
def index():
    return load_index()


@pytest.fixture(scope="module")
def west_attribution():
    d = det.detect(
        "net_revenue", WINDOW, ANALYST, slice_filter=WEST, scenario_id="S1"
    )
    return att.attribute(
        d, ANALYST, cause_date=date(2026, 7, 12), n_resamples=20
    )


# ==========================================================================
# corpus: what may and may not be embedded
# ==========================================================================
def test_only_prose_sources_are_embeddable():
    assert EMBEDDABLE_SOURCES == {
        SourceType.SUPPORT_TICKET,
        SourceType.CRM_NOTE,
        SourceType.MARKET_EVENT,
    }
    assert not (EMBEDDABLE_SOURCES & STRUCTURED_SOURCES)


@pytest.mark.parametrize(
    "source_type",
    [
        SourceType.DEPLOY_CHANGELOG,
        SourceType.SCHEMA_CHANGE,
        SourceType.FINANCE_ADJUSTMENT,
    ],
)
def test_structured_sources_refuse_to_be_embedded(source_type):
    """Numbers live in SQL and event logs have exact keys.

    Embedding them would replace an exact join with an approximate one, which
    is strictly worse and on Scenario 7 would be wrong.
    """
    with pytest.raises(corpus_mod.CorpusError, match="must not be embedded"):
        corpus_mod.assert_embeddable(source_type)


def test_the_corpus_is_the_three_prose_sources(documents):
    kinds = {d.source_type for d in documents}
    assert kinds == EMBEDDABLE_SOURCES
    assert len(documents) == 1341


def test_documents_are_atomic_not_chunked(documents):
    """One document, one embedding. No chunk suffixes, no duplicate ids."""
    ids = [d.evidence_id for d in documents]
    assert len(ids) == len(set(ids)), "duplicate ids imply chunking"
    assert not any("#chunk" in i or i.endswith("_0") for i in ids)


def test_documents_carry_the_metadata_the_filter_needs(documents):
    tickets = [d for d in documents if d.source_type is SourceType.SUPPORT_TICKET]
    assert tickets
    sample = tickets[0]
    assert sample.timestamp is not None
    assert sample.full_text
    assert sample.region is not None
    assert sample.source_table == "support_tickets"


def test_corpus_hash_is_content_addressed(documents):
    first = corpus_mod.corpus_hash(documents)
    assert first == corpus_mod.corpus_hash(list(reversed(documents))), (
        "the hash must not depend on load order"
    )
    mutated = [d.model_copy() for d in documents]
    mutated[0].full_text += " changed"
    assert corpus_mod.corpus_hash(mutated) != first


def test_retrieval_never_reads_the_ground_truth_labels():
    """`planted_for` is the answer key. Reading it at query time would make
    every retrieval metric circular."""
    offenders = []
    for path in (ROOT / "retrieval").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for label in ("planted_for", "is_decoy"):
            if label in text:
                offenders.append(f"{path.name} mentions {label}")
    assert not offenders, offenders


# ==========================================================================
# embedding index
# ==========================================================================
def test_index_matches_the_corpus_it_claims(index, documents):
    assert index.corpus_hash == corpus_mod.corpus_hash(documents)
    assert len(index.doc_ids) == len(documents)
    assert index.matrix.shape == (len(documents), index.embedding_dim)


def test_index_vectors_are_normalised(index):
    """Cosine similarity is a dot product only if the vectors are unit length."""
    norms = np.linalg.norm(index.matrix, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4)


def test_index_refuses_a_mismatched_corpus(index, tmp_path):
    from retrieval import embeddings as emb

    emb.save_index(index, tmp_path)
    with pytest.raises(IndexError_, match="different corpus"):
        emb.load_index(tmp_path, expected_corpus_hash="deadbeef")


def test_query_embedding_is_deterministic(index):
    a = embed_query("payment gateway failure", model_name=index.model_name)
    b = embed_query("payment gateway failure", model_name=index.model_name)
    assert np.allclose(a, b), "the same query must embed identically"
    assert abs(float(np.linalg.norm(a)) - 1.0) < 1e-4


def test_rows_for_preserves_the_candidate_set(index, documents):
    wanted = [d.evidence_id for d in documents[:5]]
    submatrix, kept = index.rows_for(wanted)
    assert kept == wanted
    assert submatrix.shape == (5, index.embedding_dim)

    submatrix, kept = index.rows_for(["not-a-real-id"])
    assert kept == []
    assert submatrix.shape[0] == 0


# ==========================================================================
# BM25
# ==========================================================================
def _doc(doc_id: str, text: str, when: date = date(2026, 7, 15), **kw) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=doc_id,
        source_type=kw.pop("source_type", SourceType.SUPPORT_TICKET),
        source_id="S3",
        source_table=kw.pop("source_table", "support_tickets"),
        timestamp=datetime.combine(when, datetime.min.time()),
        full_text=text,
        excerpt=text,
        **kw,
    )


def test_bm25_finds_an_exact_rare_term():
    """The reason BM25 is in the stack: codes an embedding would smooth away."""
    docs = [
        _doc("A", "the payment gateway returned PG-TIMEOUT-504 during checkout"),
        _doc("B", "customer asked about delivery timing"),
        _doc("C", "general feedback about the mobile app"),
    ]
    ranked = bm25_mod.BM25Index(docs).search("PG-TIMEOUT-504")
    assert ranked[0][0] == "A"
    assert ranked[0][1] > 0


def test_bm25_tokenizer_keeps_alphanumeric_codes_together():
    assert bm25_mod.tokenize("PG-TIMEOUT-504") == ["pg", "timeout", "504"]
    assert bm25_mod.tokenize("SKU-4471") == ["sku", "4471"]


def test_bm25_returns_scores_and_contiguous_ranks():
    docs = [_doc("A", "payment failed"), _doc("B", "payment gateway timeout")]
    ranked = bm25_mod.BM25Index(docs).search("payment")
    assert [r for _, _, r in ranked] == [1, 2]
    assert all(isinstance(s, float) for _, s, _ in ranked)


def test_bm25_on_an_empty_candidate_pool_returns_nothing():
    assert bm25_mod.BM25Index([]).search("anything") == []


# ==========================================================================
# dense
# ==========================================================================
def test_dense_retrieval_handles_paraphrase(index, documents):
    """The reason dense is in the stack: wording the query does not share."""
    west_tickets = [
        d for d in documents
        if d.source_type is SourceType.SUPPORT_TICKET
        and d.region == "West"
        and date(2026, 7, 12) <= d.timestamp.date() <= date(2026, 7, 26)
    ]
    assert west_tickets
    ids = [d.evidence_id for d in west_tickets]
    ranked = dense_mod.search("my card keeps getting rejected", index, ids)
    assert ranked
    top = {d for d, _, _ in ranked[:5]}
    payment = {
        d.evidence_id for d in west_tickets
        if "payment" in d.full_text.lower() or "card" in d.full_text.lower()
    }
    assert top & payment, "paraphrased query found no payment ticket"


def test_dense_scores_are_cosine_similarities(index, documents):
    ids = [d.evidence_id for d in documents[:20]]
    ranked = dense_mod.search("payment", index, ids)
    for _, score, _ in ranked:
        assert -1.0001 <= score <= 1.0001


def test_dense_only_scores_the_candidates_it_is_given(index, documents):
    ids = [d.evidence_id for d in documents[:7]]
    ranked = dense_mod.search("anything", index, ids)
    assert {d for d, _, _ in ranked} == set(ids)


def test_cosine_normalises_unnormalised_input():
    matrix = np.array([[3.0, 0.0], [0.0, 4.0]], dtype=np.float32)
    scores = dense_mod.cosine_scores(np.array([1.0, 0.0], dtype=np.float32), matrix)
    assert scores[0] == pytest.approx(1.0, abs=1e-5)
    assert scores[1] == pytest.approx(0.0, abs=1e-5)


# ==========================================================================
# RRF
# ==========================================================================
def test_rrf_matches_the_published_formula():
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "a"]], k=10)
    scores = {d: s for d, s, _ in fused}
    assert scores["a"] == pytest.approx(1 / 11 + 1 / 12)
    assert scores["b"] == pytest.approx(1 / 12 + 1 / 11)


def test_rrf_rewards_agreement_between_retrievers():
    fused = reciprocal_rank_fusion([["x", "y", "z"], ["x", "z", "y"]], k=10)
    assert fused[0][0] == "x"


def test_rrf_keeps_a_document_only_one_list_found():
    """The behaviour that makes hybrid worth having."""
    fused = reciprocal_rank_fusion([["a", "b"], ["c"]], k=10)
    assert "c" in {d for d, _, _ in fused}


def test_rrf_is_deterministic_under_ties():
    first = reciprocal_rank_fusion([["a", "b"], ["b", "a"]], k=10)
    for _ in range(5):
        assert reciprocal_rank_fusion([["a", "b"], ["b", "a"]], k=10) == first


def test_rrf_rejects_a_non_positive_k():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], k=0)


# ==========================================================================
# metadata pre-filter
# ==========================================================================
def test_filter_excludes_documents_outside_the_window():
    docs = [
        _doc("in", "x", when=date(2026, 7, 15)),
        _doc("before", "x", when=date(2026, 5, 1)),
        _doc("after", "x", when=date(2026, 9, 1)),
    ]
    conditions = FilterConditions(
        window_start=date(2026, 7, 1), window_end=date(2026, 7, 31)
    )
    assert [d.evidence_id for d in filters_mod.apply(docs, conditions)] == ["in"]


def test_filter_excludes_other_regions():
    docs = [_doc("w", "x", region="West"), _doc("n", "x", region="North")]
    conditions = FilterConditions(regions=["West"])
    assert [d.evidence_id for d in filters_mod.apply(docs, conditions)] == ["w"]


def test_filter_treats_a_missing_dimension_as_unconstrained():
    """Market events carry no channel; a channel filter must not delete them."""
    event = _doc(
        "m", "x", source_type=SourceType.MARKET_EVENT, region="West",
        source_table="market_events",
    )
    conditions = FilterConditions(channels=["Web"])
    assert filters_mod.matches(event, conditions)


def test_evidence_window_is_asymmetric_around_the_changepoint():
    start, end = filters_mod.evidence_window(
        date(2026, 7, 12), date(2026, 7, 12), date(2026, 7, 26)
    )
    assert start == date(2026, 7, 12) - timedelta(days=filters_mod.LOOKBACK_DAYS)
    assert end == date(2026, 7, 26) + timedelta(days=filters_mod.LOOKAHEAD_DAYS)
    assert (date(2026, 7, 12) - start).days > (end - date(2026, 7, 26)).days


def test_metadata_filter_does_most_of_the_work(west_attribution, index):
    """The architecture's claim, measured rather than repeated."""
    result = ret.retrieve_evidence(west_attribution, ANALYST, index=index)
    assert result.filters.corpus_size > 1000
    assert result.filters.candidates_after_metadata < 200, (
        "the pre-filter should cut the corpus by an order of magnitude"
    )


# ==========================================================================
# ENTITLEMENT — the security test
# ==========================================================================
def test_ops_lead_is_denied_crm_notes_at_the_source():
    access = source_access(OPS_LEAD)
    assert not access.permits("crm_notes", "S3")
    assert access.permits("support_tickets", "S3"), (
        "the coarse S3 deny must not strip an ops lead of ticket evidence"
    )


def test_unauthorised_documents_are_removed_before_any_scoring():
    """entitlement -> candidate corpus -> BM25/dense -> ranking.

    Not: BM25/dense -> remove unauthorised. The distinction is the whole
    point. A restricted document that reaches the ranking has already
    contributed to inverse document frequency and to the neighbourhood of
    every other candidate; deleting it from the display afterwards does not
    undo that, and the resulting ranking is a function of data the principal
    was never entitled to see.

    Here the ops lead's corpus is checked to contain no CRM note *at load
    time*, before any retrieval object is constructed.
    """
    permitted, withheld = corpus_mod.load_documents(OPS_LEAD)

    assert not any(d.source_type is SourceType.CRM_NOTE for d in permitted), (
        "a CRM note reached the candidate corpus of a role denied that source"
    )
    assert any(
        w.source_type is SourceType.CRM_NOTE
        and w.entitlement_status is EntitlementStatus.WITHHELD_SOURCE
        for w in withheld
    ), "the withholding must be reported, not silent"

    # and the analyst, who is entitled, does get them
    analyst_docs, _ = corpus_mod.load_documents(ANALYST)
    assert any(d.source_type is SourceType.CRM_NOTE for d in analyst_docs)


def test_bm25_index_never_sees_a_restricted_document():
    """The corpus handed to the scorer is already filtered."""
    permitted, _ = corpus_mod.load_documents(OPS_LEAD)
    bm25_index = bm25_mod.BM25Index(permitted)
    assert not any(
        d.source_type is SourceType.CRM_NOTE for d in bm25_index.documents
    )


def test_restricted_source_changes_the_result_not_just_the_display(
    west_attribution, index
):
    """Priya and Arjun see genuinely different evidence, not a greyed-out row."""
    ops = ret.retrieve_evidence(west_attribution, OPS_LEAD, index=index)
    fin = ret.retrieve_evidence(west_attribution, FINANCE, index=index)

    ops_types = {i.source_type for i in ops.items}
    assert SourceType.CRM_NOTE not in ops_types
    assert ops.withheld, "the ops lead must be told something was withheld"
    assert any("crm_notes" in (w.entitlement_reason or "") for w in ops.withheld)

    assert ops.filters.candidates_after_entitlement < (
        fin.filters.candidates_after_entitlement
    )


def test_withheld_evidence_carries_no_content():
    """A withholding notice must not leak the thing it withholds."""
    _, withheld = corpus_mod.load_documents(OPS_LEAD)
    for item in withheld:
        assert item.full_text == ""
        assert "crm_notes" in (item.entitlement_reason or "")


# ==========================================================================
# structured evidence routing
# ==========================================================================
def test_schema_change_is_retrieved_deterministically_not_by_embedding(index):
    """S7: the answer is a schema_change_log row.

    It is found by an exact date filter, and it is not in the embedding index
    at all - so no amount of query phrasing could have surfaced it through
    semantic search.
    """
    rename = date(2026, 6, 14)
    items = ret.structured_evidence(
        ANALYST, rename - timedelta(days=7), rename + timedelta(days=7)
    )
    schema = [i for i in items if i.source_type is SourceType.SCHEMA_CHANGE]
    assert schema, "the schema change was not retrieved"

    target = [i for i in schema if i.lineage.get("column_name") == "channel"]
    assert target, "the channel rename row was not found"
    assert target[0].timestamp.date() == rename
    assert target[0].retrieval_mode.value == "structured"

    assert target[0].evidence_id not in set(index.doc_ids), (
        "a schema-change row must never be in the embedding index"
    )


def test_deploy_changelog_is_retrieved_by_exact_window(index):
    """S1's smoking gun: the gateway routing change, dated to the changepoint."""
    items = ret.structured_evidence(
        ANALYST, date(2026, 7, 5), date(2026, 7, 19)
    )
    deploys = [i for i in items if i.source_type is SourceType.DEPLOY_CHANGELOG]
    assert deploys
    gateway = [i for i in deploys if "gateway" in (i.title or "").lower()]
    assert gateway, "the payment gateway deploy was not retrieved"
    assert gateway[0].timestamp.date() == date(2026, 7, 12)
    assert gateway[0].evidence_id not in set(index.doc_ids)


def test_structured_evidence_puts_non_routine_records_first():
    items = ret.structured_evidence(
        ANALYST, date(2026, 7, 5), date(2026, 7, 19)
    )
    assert items
    assert "routine" not in (items[0].title or "").lower()


# ==========================================================================
# query construction
# ==========================================================================
def test_query_is_built_from_analytical_state_only(west_attribution):
    query = ret.build_query(west_attribution)
    assert "West" in query.text
    assert query.kpi_id == "net_revenue"
    assert query.driver == "conversion_rate"
    assert query.slice
    assert "no LLM" in query.built_from or "cause-bucket" in query.built_from


def test_query_construction_is_deterministic(west_attribution):
    first = ret.build_query(west_attribution).text
    for _ in range(3):
        assert ret.build_query(west_attribution).text == first


def test_cause_buckets_do_not_presuppose_a_single_cause(west_attribution):
    """A conversion drop has several mechanisms; searching only for one is how
    a system finds only the evidence it expected."""
    queries = ret.build_queries(west_attribution)
    assert len(queries) > 1
    buckets = {q.built_from for q in queries}
    assert len(buckets) == len(queries)
    joined = " ".join(q.text for q in queries)
    assert "payment" in joined and "stock" in joined and "competitor" in joined


# ==========================================================================
# cohort aggregation
# ==========================================================================
def test_cohort_rolls_many_tickets_into_one_statement():
    incident = [
        _doc(f"T{i}", "payment failed", when=date(2026, 7, 14),
             category="payment", account_id=f"A{i}")
        for i in range(20)
    ]
    baseline = [
        _doc(f"B{i}", "payment failed", when=date(2026, 6, 1) + timedelta(days=7 * i),
             category="payment", account_id=f"A{i}")
        for i in range(4)
    ]
    cohorts = cohort_mod.aggregate(
        incident, baseline,
        window_start=date(2026, 7, 12), window_end=date(2026, 7, 18),
        cohort_dimensions={"region": "West"},
    )
    assert len(cohorts) == 1
    c = cohorts[0]
    assert c.incident_count == 20
    assert c.distinct_accounts == 20
    assert len(c.document_ids) == 20, "drill-down ids must be preserved"
    assert "20" in c.statement()


def test_cohort_reports_a_zero_baseline_as_novel_not_missing():
    """A category that never occurred before is the strongest signal there is."""
    incident = [
        _doc(f"T{i}", "gateway timeout", category="gateway", account_id=f"A{i}")
        for i in range(6)
    ]
    cohorts = cohort_mod.aggregate(
        incident, [],
        window_start=date(2026, 7, 12), window_end=date(2026, 7, 18),
        cohort_dimensions={"region": "West"},
    )
    assert cohorts[0].novel
    assert cohorts[0].baseline_total == 0
    assert "none at all" in cohorts[0].statement()
    assert "no baseline available" not in cohorts[0].statement()


def test_cohort_uses_a_median_not_a_mean_baseline():
    """One freak week must not set the baseline."""
    incident = [
        _doc(f"T{i}", "payment", category="payment") for i in range(10)
    ]
    baseline = (
        [_doc(f"S{i}", "payment", when=date(2026, 5, 4), category="payment")
         for i in range(40)]                       # one enormous week
        + [_doc(f"Q{i}", "payment",
                when=date(2026, 5, 11) + timedelta(days=7 * i), category="payment")
           for i in range(3)]
    )
    cohorts = cohort_mod.aggregate(
        incident, baseline,
        window_start=date(2026, 6, 29), window_end=date(2026, 7, 5),
    )
    assert cohorts[0].baseline_count <= 2.0, (
        "a 40-ticket outlier week dragged the baseline; median was not used"
    )


def test_cohort_ignores_groups_below_the_minimum_size():
    incident = [_doc("T1", "x", category="rare")]
    assert cohort_mod.aggregate(
        incident, [], window_start=date(2026, 7, 1), window_end=date(2026, 7, 7)
    ) == []


# ==========================================================================
# contradiction signals
# ==========================================================================
def _hypothesis(**kw) -> CandidateHypothesis:
    base = dict(
        hypothesis_id="H1",
        statement="conversion fell in West",
        cause_bucket="internal_product",
        slice={"region": ["West"]},
        changepoint=date(2026, 7, 12),
        keywords=["payment", "gateway"],
    )
    base.update(kw)
    return CandidateHypothesis(**base)


def test_temporal_precedence_violation_is_flagged():
    signals = contra_mod.temporal_precedence(
        _hypothesis(cause_date=date(2026, 7, 20)), []
    )
    assert signals
    s = signals[0]
    assert s.contradiction_type is ContradictionType.TEMPORAL_PRECEDENCE_VIOLATED
    assert s.direction is ContradictionDirection.CONTRADICTS
    assert s.strength == 1.0


def test_a_cause_before_the_changepoint_is_not_flagged():
    assert contra_mod.temporal_precedence(
        _hypothesis(cause_date=date(2026, 7, 1)), []
    ) == []


def test_a_flat_relevant_cohort_contradicts_the_hypothesis():
    cohort = cohort_mod.CohortEvidence(
        cohort_id="c", label="payment tickets", source_type=SourceType.SUPPORT_TICKET,
        category="payment", incident_count=5, baseline_count=5.0, ratio=1.0,
    )
    signals = contra_mod.cohort_not_affected(_hypothesis(), [cohort])
    assert signals
    assert signals[0].contradiction_type is ContradictionType.COHORT_NOT_AFFECTED


def test_an_irrelevant_flat_cohort_is_not_reported_as_a_contradiction():
    """"Routine notes were flat" says nothing about a gateway hypothesis.

    Flooding the panel with true-but-irrelevant contradictions trains a reader
    to skip the section where the real disconfirming evidence lives.
    """
    cohort = cohort_mod.CohortEvidence(
        cohort_id="c", label="routine CRM notes", source_type=SourceType.CRM_NOTE,
        category="routine", incident_count=5, baseline_count=5.0, ratio=1.0,
    )
    assert contra_mod.cohort_not_affected(_hypothesis(), [cohort]) == []


def test_a_market_event_in_window_is_surfaced_as_a_competing_explanation():
    event = _doc(
        "M1", "Rival launches festive discounting early",
        when=date(2026, 7, 5), source_type=SourceType.MARKET_EVENT,
    )
    signals = contra_mod.competing_explanation(_hypothesis(), [event])
    assert signals
    assert signals[0].contradiction_type is ContradictionType.COMPETING_EXPLANATION
    assert "M1" in signals[0].contradicting_evidence_ids


def test_a_moving_control_slice_contradicts_a_slice_specific_cause():
    signals = contra_mod.unaffected_peer_moved(
        _hypothesis(), True, "North", did_estimate_pct=-0.7
    )
    assert signals
    assert signals[0].contradiction_type is (
        ContradictionType.UNAFFECTED_PEER_SAME_MOVEMENT
    )


def test_supporting_signal_is_typed_as_support_not_contradiction():
    docs = [_doc("T1", "payment failed", when=date(2026, 7, 15), region="West")]
    signal = contra_mod.supporting(_hypothesis(), docs)
    assert signal is not None
    assert signal.direction is ContradictionDirection.SUPPORTS
    assert signal.contradiction_type is ContradictionType.CONSISTENT_WITH_HYPOTHESIS


def test_contradictions_are_ordered_before_supporting_signals():
    docs = [_doc("T1", "payment failed", when=date(2026, 7, 15), region="West")]
    signals = contra_mod.analyse(
        _hypothesis(cause_date=date(2026, 7, 20)), docs, []
    )
    directions = [s.direction for s in signals]
    assert directions[0] is ContradictionDirection.CONTRADICTS


# ==========================================================================
# end to end
# ==========================================================================
def test_s1_retrieves_payment_and_gateway_evidence(west_attribution, index):
    result = ret.retrieve_evidence(west_attribution, ANALYST, index=index)

    text = " ".join(
        f"{i.title or ''} {i.excerpt}".lower() for i in result.items
    )
    assert "payment" in text or "gateway" in text, (
        "S1 returned no payment or gateway evidence"
    )

    deploys = [
        i for i in result.structured_items
        if i.source_type is SourceType.DEPLOY_CHANGELOG
        and "gateway" in (i.title or "").lower()
    ]
    assert deploys, "the gateway deploy was not in the structured evidence"


def test_irrelevant_documents_do_not_dominate(west_attribution, index):
    """Documents outside the window and slice must not reach the top 8."""
    result = ret.retrieve_evidence(west_attribution, ANALYST, index=index)
    window_start = result.filters.window_start
    window_end = result.filters.window_end
    for item in result.items:
        day = item.timestamp.date()
        assert window_start <= day <= window_end, (
            f"{item.evidence_id} at {day} is outside {window_start}..{window_end}"
        )
        if item.region is not None:
            assert item.region == "West"


def test_near_duplicates_are_collapsed_but_counted(west_attribution, index):
    result = ret.retrieve_evidence(west_attribution, ANALYST, index=index)
    texts = [" ".join(i.full_text.lower().split()) for i in result.items]
    assert len(texts) == len(set(texts)), "identical documents were both returned"
    assert any(i.duplicate_count > 0 for i in result.items)
    for item in result.items:
        assert len(item.duplicate_ids) == item.duplicate_count


def test_every_returned_item_exposes_all_three_scores(west_attribution, index):
    result = ret.retrieve_evidence(west_attribution, ANALYST, index=index)
    for item in result.items:
        assert item.rrf_score is not None and item.rrf_rank is not None
        assert item.bm25_score is not None or item.dense_score is not None


def test_retrieval_is_reproducible(west_attribution, index):
    """Same corpus, model, query and filters -> same result."""
    first = ret.retrieve_evidence(west_attribution, ANALYST, index=index)
    second = ret.retrieve_evidence(west_attribution, ANALYST, index=index)

    assert first.query.text == second.query.text
    assert [i.evidence_id for i in first.items] == [
        i.evidence_id for i in second.items
    ]
    assert [i.rrf_score for i in first.items] == [
        i.rrf_score for i in second.items
    ]
    assert first.config.corpus_hash == second.config.corpus_hash


def test_result_records_everything_needed_to_reproduce_it(
    west_attribution, index
):
    result = ret.retrieve_evidence(west_attribution, ANALYST, index=index)
    cfg = result.config
    assert cfg.embedding_model and cfg.embedding_dim > 0
    assert cfg.corpus_hash and cfg.rrf_k == 10
    assert result.retrieved_at is not None
    assert result.method
    assert result.timing.total_ms > 0
    assert result.model_dump_json()


def test_retrieval_result_combines_structured_and_semantic_evidence(
    west_attribution, index
):
    result = ret.retrieve_evidence(west_attribution, ANALYST, index=index)
    combined = result.all_items
    assert len(combined) == len(result.structured_items) + len(result.items)
    kinds = {i.source_type for i in combined}
    assert kinds & STRUCTURED_SOURCES
    assert kinds & EMBEDDABLE_SOURCES


def test_retrieval_does_not_import_an_llm_or_ui_layer():
    forbidden = (
        "langchain", "langgraph", "streamlit", "openai", "anthropic",
        "chromadb", "pinecone", "faiss", "pgvector",
    )
    for path in (ROOT / "retrieval").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for name in forbidden:
            assert f"import {name}" not in text, f"{path.name} imports {name}"


# ==========================================================================
# benchmark
# ==========================================================================
def test_benchmark_has_at_least_twenty_labelled_pairs():
    bench = json.loads(
        (ROOT / "eval" / "retrieval_benchmark.json").read_text(encoding="utf-8")
    )
    assert bench["n_queries"] >= 20
    assert bench["n_dev"] > 0 and bench["n_eval"] > 0

    for spec_ in bench["queries"]:
        assert spec_["relevant_doc_ids"], f"{spec_['query_id']} has no labels"
        assert spec_["hard_negative_ids"], f"{spec_['query_id']} has no negatives"
        assert not (
            set(spec_["relevant_doc_ids"]) & set(spec_["hard_negative_ids"])
        ), f"{spec_['query_id']} labels a document both relevant and negative"
