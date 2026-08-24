"""The hard pre-filter (Architecture Part 11.1 step 1, Part 11.4).

Two claims from the architecture, both load-bearing:

**"Metadata filtering does more work than the embedding does."** Cutting 1,341
documents to ~60 by date and slice is a bigger precision win than any model
upgrade. The filter is not a soft signal or a post-hoc tidy-up; it decides
what is searchable.

**Entitlement is security, not presentation.** The order is

    entitlement filter -> candidate corpus -> BM25/dense -> ranking

and never the reverse. Retrieving a restricted document and hiding it later
leaks it: it has already influenced IDF statistics, similarity neighbourhoods
and rank positions, and "we removed it from the display" is not a defence.
Source-level entitlement is enforced upstream of this module, in the gateway,
so restricted documents are never materialised at all.

A `None` metadata field means *unconstrained*, not *excluded*. Market events
carry a region but no channel; CRM notes carry no channel either. Treating a
missing field as a mismatch would silently delete whole source types from
every channel-scoped query.
"""

from __future__ import annotations

from datetime import date, timedelta

from retrieval.types import EvidenceItem, FilterConditions, SourceType

# The evidence window is asymmetric around the changepoint, and deliberately
# so: a cause usually precedes its effect, so more history is worth searching
# than future. Part 11.1 specifies [cp-14d, cp+7d].
LOOKBACK_DAYS = 14
LOOKAHEAD_DAYS = 7


def evidence_window(
    changepoint: date | None,
    event_start: date | None = None,
    event_end: date | None = None,
    lookback: int = LOOKBACK_DAYS,
    lookahead: int = LOOKAHEAD_DAYS,
) -> tuple[date, date]:
    """The date range worth searching for evidence about one movement."""
    anchor_start = changepoint or event_start
    anchor_end = event_end or changepoint or event_start
    if anchor_start is None or anchor_end is None:
        raise ValueError("cannot build an evidence window without a date anchor")
    return anchor_start - timedelta(days=lookback), anchor_end + timedelta(days=lookahead)


def _field_matches(value: str | None, allowed: list[str]) -> bool:
    if not allowed:
        return True
    if value is None:
        # the document does not carry this dimension, so it cannot contradict
        # the filter - see the module docstring
        return True
    return value in allowed


def matches(item: EvidenceItem, conditions: FilterConditions) -> bool:
    """Does one document survive the hard pre-filter?"""
    if conditions.source_types and item.source_type not in conditions.source_types:
        return False

    day = item.timestamp.date()
    if conditions.window_start and day < conditions.window_start:
        return False
    if conditions.window_end and day > conditions.window_end:
        return False

    return (
        _field_matches(item.region, conditions.regions)
        and _field_matches(item.channel, conditions.channels)
        and _field_matches(item.segment, conditions.segments)
        and _field_matches(item.product_category, conditions.product_categories)
    )


def apply(
    documents: list[EvidenceItem], conditions: FilterConditions
) -> list[EvidenceItem]:
    """Reduce the permitted corpus to the searchable candidate pool."""
    return [d for d in documents if matches(d, conditions)]


def build_conditions(
    *,
    slice_filter: dict[str, list[str]],
    window_start: date,
    window_end: date,
    source_types: list[SourceType] | None = None,
    allowed_sources: list[str] | None = None,
    denied_sources: list[str] | None = None,
) -> FilterConditions:
    """Translate an attributed slice into filter conditions.

    Dimension names come from the analytical layer unchanged, so a slice that
    detection and attribution agreed on is the same slice retrieval searches.
    """
    return FilterConditions(
        window_start=window_start,
        window_end=window_end,
        regions=list(slice_filter.get("region", [])),
        channels=list(slice_filter.get("channel", [])),
        segments=list(slice_filter.get("segment", [])),
        product_categories=list(slice_filter.get("product_category", [])),
        source_types=list(source_types or []),
        allowed_sources=list(allowed_sources or []),
        denied_sources=list(denied_sources or []),
    )
