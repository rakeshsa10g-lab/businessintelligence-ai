"""The document corpus — atomic records, never chunked (Architecture Part 11.3).

Three sources are embeddable prose: support tickets, CRM notes and market
events. Everything else in the database is either a number, a definition or an
event log, and each of those has a better retrieval mechanism than a vector:

    numbers        authoritative in SQL
    definitions    authoritative in the semantic contract
    event logs     exact join on time x service, or table x column
    lever catalogue a fixed enumeration, not a search problem

`assert_embeddable()` enforces that split in code rather than leaving it to
discipline, and `tests/test_retrieval.py` asserts the enforcement.

One document is one embedding. A ticket is ~80 words, a note ~120, an event
~60; splitting them would break the metadata binding (which account, which
region, which date) that the hard pre-filter depends on, and would fragment
the cohort signal that is the actual predictor.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from retrieval.types import (
    EMBEDDABLE_SOURCES,
    STRUCTURED_SOURCES,
    EntitlementStatus,
    EvidenceItem,
    SourceType,
)
from security.entitlements import Principal
from semantic import gateway

# Where a long threaded ticket would be truncated. Part 11.3's one exception:
# subject + first + last message, dropping the middle, because persistence
# rather than intensity is the signal. Our generated tickets are single
# messages, so this never fires - it is here so the rule is visible, and a
# test records that it is currently inert.
LONG_DOCUMENT_CHARS = 2000


class CorpusError(ValueError):
    """A retrieval operation was attempted on a source that forbids it."""


def assert_embeddable(source_type: SourceType) -> None:
    """Refuse to embed anything outside the three prose sources."""
    if source_type in STRUCTURED_SOURCES:
        raise CorpusError(
            f"'{source_type.value}' must not be embedded. It has exact keys "
            f"(dates, services, table/column names), so a deterministic SQL "
            f"filter is both cheaper and correct; an embedding would replace "
            f"an exact join with an approximate one."
        )
    if source_type not in EMBEDDABLE_SOURCES:
        raise CorpusError(f"'{source_type}' is not a known embeddable source")


# --------------------------------------------------------------------------
# row -> EvidenceItem
# --------------------------------------------------------------------------
def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


def _clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "nan", "None", "NaT"):
        return None
    return text


def _excerpt(text: str, limit: int = 240) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def _ticket(row: dict) -> EvidenceItem:
    subject = _clean(row.get("subject")) or ""
    body = _clean(row.get("body")) or ""
    text = f"{subject}\n{body}".strip()
    return EvidenceItem(
        evidence_id=str(row["ticket_id"]),
        source_type=SourceType.SUPPORT_TICKET,
        source_id="S3",
        source_table="support_tickets",
        timestamp=_as_datetime(row["created_at"]),
        title=subject or None,
        excerpt=_excerpt(text),
        full_text=text,
        region=_clean(row.get("region")),
        segment=_clean(row.get("segment")),
        channel=_clean(row.get("channel")),
        account_id=_clean(row.get("account_id")),
        category=_clean(row.get("category")),
        severity=_clean(row.get("severity")),
        lineage={
            "source_table": "support_tickets",
            "resolved_at": str(row.get("resolved_at")),
        },
    )


def _crm_note(row: dict) -> EvidenceItem:
    body = _clean(row.get("body")) or ""
    return EvidenceItem(
        evidence_id=str(row["note_id"]),
        source_type=SourceType.CRM_NOTE,
        source_id="S3",
        source_table="crm_notes",
        timestamp=_as_datetime(row["note_date"]),
        title=None,
        excerpt=_excerpt(body),
        full_text=body,
        region=_clean(row.get("region")),
        segment=_clean(row.get("segment")),
        account_id=_clean(row.get("account_id")),
        category=_clean(row.get("kind")),
        lineage={
            "source_table": "crm_notes",
            "author_role": _clean(row.get("author_role")),
        },
    )


def _market_event(row: dict) -> EvidenceItem:
    headline = _clean(row.get("headline")) or ""
    body = _clean(row.get("body")) or ""
    text = f"{headline}\n{body}".strip()
    return EvidenceItem(
        evidence_id=str(row["event_id_doc"]),
        source_type=SourceType.MARKET_EVENT,
        source_id="S3",
        source_table="market_events",
        timestamp=_as_datetime(row["event_date"]),
        title=headline or None,
        excerpt=_excerpt(text),
        full_text=text,
        region=_clean(row.get("region")),
        category=_clean(row.get("category")),
        lineage={
            "source_table": "market_events",
            "source_name": _clean(row.get("source_name")),
        },
    )


_BUILDERS = {
    SourceType.SUPPORT_TICKET: ("support_ticket", _ticket),
    SourceType.CRM_NOTE: ("crm_note", _crm_note),
    SourceType.MARKET_EVENT: ("market_event", _market_event),
}


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def load_documents(
    principal: Principal | None = None,
    source_types: list[SourceType] | None = None,
) -> tuple[list[EvidenceItem], list[EvidenceItem]]:
    """Load the embeddable corpus.

    Returns (permitted, withheld). When a principal is supplied, documents
    from a source the role may not read are never materialised at all - the
    gateway returns nothing for them - so the withheld entries carry the count
    and the reason, not the content.

    Passing `principal=None` loads the full corpus, which is what the offline
    index build does. Query-time retrieval always passes a principal.
    """
    wanted = source_types or sorted(EMBEDDABLE_SOURCES, key=lambda s: s.value)
    permitted: list[EvidenceItem] = []
    withheld: list[EvidenceItem] = []

    for source_type in wanted:
        assert_embeddable(source_type)
        key, build = _BUILDERS[source_type]
        rows, reason = gateway.documents(key, principal)

        if reason:
            withheld.append(
                EvidenceItem(
                    evidence_id=f"withheld:{source_type.value}",
                    source_type=source_type,
                    source_id="S3",
                    source_table=gateway.CORPUS_TABLES[key]["table"],
                    timestamp=datetime.min,
                    title=f"{source_type.value} withheld",
                    excerpt=reason,
                    entitlement_status=EntitlementStatus.WITHHELD_SOURCE,
                    entitlement_reason=reason,
                )
            )
            continue

        for row in rows:
            permitted.append(build(row))

    permitted.sort(key=lambda d: (d.source_type.value, d.evidence_id))
    return permitted, withheld


def corpus_hash(documents: list[EvidenceItem]) -> str:
    """A content hash, so an index can prove which corpus it was built from.

    Hashes ids and text rather than the database file: DuckDB embeds metadata
    that varies between writes, which is the same reason ADR-013 hashes table
    contents rather than bytes.
    """
    digest = hashlib.sha256()
    for doc in sorted(documents, key=lambda d: d.evidence_id):
        digest.update(doc.evidence_id.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(doc.full_text.encode("utf-8"))
        digest.update(b"\x01")
    return digest.hexdigest()


def document_texts(documents: list[EvidenceItem]) -> list[str]:
    """What actually gets embedded, with the long-thread rule applied."""
    out = []
    for doc in documents:
        text = doc.full_text
        if len(text) > LONG_DOCUMENT_CHARS:
            # subject + first message + last message; the middle is dropped
            # deliberately (Part 11.3)
            head = text[: LONG_DOCUMENT_CHARS // 2]
            tail = text[-(LONG_DOCUMENT_CHARS // 2) :]
            text = f"{head}\n...\n{tail}"
        out.append(text)
    return out
