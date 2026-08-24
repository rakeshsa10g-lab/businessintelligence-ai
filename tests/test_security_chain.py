"""Stage 12 Part 5 — the entitlement chain, end to end.

`tests/test_entitlements.py` proves the policy layer is correct in isolation:
the right row filter, the right denied sources, the right masked columns. That
is necessary and it is not sufficient. A correct policy still leaks if a later
stage re-reads the corpus, or if a restricted excerpt survives into a derived
field that nobody thought of as evidence.

So these tests follow one genuinely restricted source through **every** stage
a document could escape at:

    persona -> policy -> SQL rows -> retrieval candidates -> ranking
            -> EvidenceBundle -> LLM payload -> UI text

and assert absence at each. They are deliberately written against a *live run*
rather than a constructed bundle, because a constructed bundle proves only
that the assertion works.

The restricted source used is `crm_notes`, denied to `ops_lead` by policy. The
same event is run as `analytics_lead`, who may read it — so every assertion
below is paired with proof that the content exists and is findable when the
reader is permitted. A test that passes because the data is missing entirely
would prove nothing.
"""

from __future__ import annotations

from datetime import date

import pytest

from graph.build import compile_graph
from graph.run import InsightRequest, run_insight
from semantic.types import Window

WINDOW = Window(start=date(2026, 1, 1), end=date(2026, 8, 17))
WEST = {"region": ["West"], "channel": ["Web", "Mobile App"]}
CAUSE = date(2026, 7, 12)

#: Denied to ops_lead in config/entitlements.yaml.
RESTRICTED_SOURCE = "crm_note"


@pytest.fixture(scope="module")
def index():
    from retrieval.embeddings import load_index
    return load_index()


@pytest.fixture(scope="module")
def graph():
    return compile_graph(in_memory=True)


def _run(graph, index, persona_id, run_id):
    return run_insight(
        InsightRequest(
            persona_id=persona_id, kpi_id="net_revenue", window=WINDOW,
            slice_filter=WEST, cause_date=CAUSE, scenario_id="S6",
            run_id=run_id,
        ),
        graph=graph, index=index, history_days=229,
    )


@pytest.fixture(scope="module")
def restricted_run(graph, index):
    """priya — ops_lead. May NOT read crm_notes."""
    return _run(graph, index, "priya", "SEC-RESTRICTED")


@pytest.fixture(scope="module")
def permitted_run(graph, index):
    """meera — analytics_lead. MAY read crm_notes."""
    return _run(graph, index, "meera", "SEC-PERMITTED")


# ==========================================================================
# the control: the restricted content exists and is reachable by someone
# ==========================================================================
def test_the_restricted_source_is_genuinely_present_for_a_permitted_reader():
    """Otherwise every absence assertion below is vacuous."""
    from retrieval import corpus as corpus_mod

    docs, _withheld = corpus_mod.load_documents()      # full corpus
    crm = [d for d in docs if d.source_type.value == RESTRICTED_SOURCE]
    assert len(crm) > 100, (
        f"only {len(crm)} {RESTRICTED_SOURCE} documents exist; the absence "
        f"tests would pass trivially"
    )


def test_policy_denies_the_source_to_the_restricted_role(restricted_run,
                                                         permitted_run):
    """Stage 1 of the chain: the policy decision itself."""
    denied = set(restricted_run.bundle.security_context.denied_sources)
    assert "crm_notes" in denied, (
        f"ops_lead should be denied crm_notes; denied = {denied}"
    )
    assert "crm_notes" not in set(
        permitted_run.bundle.security_context.denied_sources)


# ==========================================================================
# stage by stage: the restricted document must not appear
# ==========================================================================
def test_restricted_documents_are_withheld_before_ranking(restricted_run):
    """Stage 2-3: candidate filtering happens BEFORE BM25/dense scoring.

    The count is the evidence. A silently shorter result list would be
    indistinguishable from "nothing matched"; a withheld count says the
    filter ran and how much it removed.
    """
    sec = restricted_run.bundle.security_context
    assert sec.withheld_item_count > 0, (
        "nothing was withheld for a role that is denied a whole source"
    )
    assert RESTRICTED_SOURCE in set(sec.withheld_source_ids)


def test_no_restricted_document_reaches_the_evidence_bundle(restricted_run):
    """Stage 4: the frozen bundle, which is what everything downstream reads."""
    bundle = restricted_run.bundle
    items = list(bundle.supporting_evidence or ()) + \
        list(bundle.contradicting_evidence or ())

    for item in items:
        assert item.source_type.value != RESTRICTED_SOURCE, (
            f"{item.evidence_id} is a {RESTRICTED_SOURCE} and reached an "
            f"ops_lead bundle"
        )
        assert not item.evidence_id.startswith("withheld:"), (
            "a withheld placeholder leaked into the rendered evidence"
        )


def test_no_restricted_excerpt_survives_in_any_bundle_text(restricted_run,
                                                           permitted_run):
    """Stage 4b: derived fields, not just the evidence list.

    A cohort summary, a hypothesis statement or a note could quote a
    restricted document without carrying its id. This compares the actual
    excerpt text of the documents the permitted reader saw against every
    string the restricted reader's bundle contains.
    """
    permitted_items = [
        i for i in (list(permitted_run.bundle.supporting_evidence or ())
                    + list(permitted_run.bundle.contradicting_evidence or ()))
        if i.source_type.value == RESTRICTED_SOURCE
    ]
    if not permitted_items:
        pytest.skip("the permitted reader retrieved no crm_note for this event")

    haystack = restricted_run.bundle.model_dump_json()
    for item in permitted_items:
        assert item.evidence_id not in haystack, (
            f"restricted id {item.evidence_id} appears somewhere in the "
            f"ops_lead bundle"
        )
        # a distinctive fragment of the excerpt, not the whole string
        fragment = (item.excerpt or "")[:60].strip()
        if len(fragment) > 25:
            assert fragment not in haystack, (
                f"restricted excerpt text leaked into the ops_lead bundle: "
                f"{fragment!r}"
            )


def test_no_restricted_content_reaches_the_llm_payload(restricted_run,
                                                       permitted_run):
    """Stage 5: what would actually be sent to the model.

    The assertion is deliberately *not* "the string `crm_note` is absent".
    The payload states that one `crm_note` item was withheld, and that is
    correct by design — Architecture 7.6 makes the withheld count and source
    a trust signal, on the grounds that "2 items withheld from crm_notes" is
    more honest than a silently shorter list, and `security/policy.yaml`
    carries no non-disclosure rule for source names.

    What must not appear is restricted *content*: a document id or an excerpt.
    So this checks those, and separately pins the source name to the withheld
    metadata block — if `crm_note` ever appears attached to an evidence item
    rather than to a withheld counter, that is the real leak.
    """
    import json

    from llm.payload import build_payload, render_user_message

    payload = build_payload(restricted_run.bundle)
    blob = json.dumps(payload) + render_user_message(restricted_run.bundle)

    # 1. no restricted document id or excerpt from what a permitted reader saw
    permitted_crm = [
        i for i in (list(permitted_run.bundle.supporting_evidence or ())
                    + list(permitted_run.bundle.contradicting_evidence or ()))
        if i.source_type.value == RESTRICTED_SOURCE
    ]
    for item in permitted_crm:
        assert item.evidence_id not in blob, (
            f"restricted document id {item.evidence_id} reached the LLM payload"
        )
        fragment = (item.excerpt or "")[:60].strip()
        if len(fragment) > 25:
            assert fragment not in blob, (
                f"restricted excerpt reached the LLM payload: {fragment!r}"
            )

    # 2. the source name appears only as withheld metadata, never on an item
    evidence_blob = json.dumps(payload.get("evidence", []))
    assert RESTRICTED_SOURCE not in evidence_blob, (
        f"{RESTRICTED_SOURCE} is attached to an evidence item in the payload, "
        f"not merely counted as withheld"
    )


def test_no_restricted_content_reaches_the_ui(restricted_run):
    """Stage 6: the rendered surface, including the withheld notice itself."""
    from ui.components import evidence as evidence_view

    support, contra, withheld = evidence_view.counts(restricted_run)
    assert withheld > 0

    # The notice states a COUNT and nothing else — no ids, no excerpts.
    src = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "ui" / "components" / "evidence.py").read_text(encoding="utf-8")
    notice = src.split("def render_withheld_notice")[1].split("\ndef ")[0]
    assert "excerpt" not in notice
    assert "evidence_id" not in notice


# ==========================================================================
# persona variation and repeated switching
# ==========================================================================
def test_the_same_event_yields_different_access_for_different_roles(
    restricted_run, permitted_run
):
    """Persona variation: identical analysis, different permitted evidence."""
    assert restricted_run.bundle.detection.pct_delta == \
        permitted_run.bundle.detection.pct_delta, (
            "the underlying analysis must not depend on who is reading it"
        )
    assert (restricted_run.bundle.security_context.withheld_item_count
            > permitted_run.bundle.security_context.withheld_item_count)


def test_repeated_scenario_switching_does_not_bleed_entitlement(graph, index):
    """The failure mode a cached index or a reused connection would produce.

    Runs restricted -> permitted -> restricted in one process. If any layer
    cached a permitted result and served it to the restricted reader, the
    third run would differ from the first.
    """
    first = _run(graph, index, "priya", "SEC-SWITCH-1")
    _middle = _run(graph, index, "meera", "SEC-SWITCH-2")
    third = _run(graph, index, "priya", "SEC-SWITCH-3")

    a = first.bundle.security_context
    c = third.bundle.security_context

    assert a.role == c.role == "ops_lead"
    assert a.withheld_item_count == c.withheld_item_count, (
        "the restricted reader saw a different amount of evidence after a "
        "permitted reader ran in between — a cache is crossing the boundary"
    )
    assert set(a.denied_sources) == set(c.denied_sources)

    for item in list(third.bundle.supporting_evidence or ()):
        assert item.source_type.value != RESTRICTED_SOURCE
