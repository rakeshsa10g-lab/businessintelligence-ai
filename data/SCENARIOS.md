# Generated dataset — scenario summary

Seed `20260821`. Window 2025-03-01 to 2026-08-17 (535 days). Regenerate with `python -m data.generate`.

## Table row counts

| Table | Rows |
|---|---|
| `fact_orders` | 105,216 |
| `fact_sessions` | 205,440 |
| `fact_funnel_steps` | 821,760 |
| `support_tickets` | 895 |
| `crm_notes` | 334 |
| `market_events` | 112 |
| `deploy_changelog` | 177 |
| `schema_change_log` | 24 |
| `finance_adjustments` | 80 |
| `source_watermarks` | 3 |

## Injected events

| ID | Event | Window | Slice | True driver | Detectable | Net revenue change |
|---|---|---|---|---|---|---|
| E1 | Payment gateway degradation | 2026-07-12 to 2026-07-26 | region=West, channel=Web/Mobile App | `conversion_rate` | yes | -25.0% |
| E2 | Ambiguous: competitor promo vs stockout | 2026-06-02 to 2026-06-16 | region=South, product_category=Apparel | `orders` | yes | -21.9% |
| E3 | Unexplained softness, thin evidence | 2026-08-05 to 2026-08-15 | region=East, segment=SMB | `orders` | yes | -17.4% |
| E4 | NewLaunch category, sparse history | 2026-07-20 to 2026-07-31 | product_category=NewLaunch | `orders` | no (sparse path) | +210.9% |
| E5 | Schema change masquerading as a business event | 2026-06-14 to 2026-06-28 | channel=Marketplace | `schema_change` | yes | n/a (data artifact) |
| E6 | One event, two personas | 2026-07-12 to 2026-07-26 | region=West, channel=Web/Mobile App | `conversion_rate` | yes | -25.0% |

## Demo scenarios

These are the scenarios as the evaluation harness actually runs them (ADR-028). `eval/run_recommendation_eval.py` is the executable definition; this table is generated from the same manifest it reads, so the two cannot drift apart.

The **Expected outcome** column states design *intent*. It is not a record of what the system decides. That is the scenario table in `eval/recommendation_report.md`, which is authoritative for every terminal decision (ADR-027).

| ID | Title | Events | Persona | Expected outcome (intent) | Case requirement |
|---|---|---|---|---|---|
| S1 | High-confidence multi-factor movement | E1 | meera | Ranked hypothesis with gateway deploy + payment tickets as corroboration | R2-MPE-4, R2-MPE-8 |
| S2 | Conflicting evidence | E2 | meera | Two hypotheses within the ambiguity margin, both shown | R2-MPE-4, R2-CX-6 |
| S3 | Low confidence / thin evidence | E3 | meera | System declines to assert a cause and names what would settle it | R2-MPE-5 |
| S4 | Sparse history | E4 | meera | Sparse path used; standard detector suppressed; levers restricted | R2-MPE-6 |
| S5a | Two personas, one event - operations lead | E1, E6 | priya | Same movement, different narrative, actions and owners | R2-MPE-3 |
| S5b | Two personas, one event - finance director | E1, E6 | arjun | Same movement, different narrative, actions and owners | R2-MPE-3 |
| S6 | Entitlement restriction | E6 | priya | CRM evidence withheld with an explicit count and reason | R2-MPE-7, R2-CX-8 |
| S7 | Schema change masquerading as a business event | E5 | meera | Identified as a data artifact, not a business movement | R2-CX-3 |

### Divergence from the Round-1 specification (historical)

The original assignment is preserved here because it is the record of what was first intended, and because a reader who finds it quoted elsewhere needs to know it was superseded rather than mistaken for current.

The Round-1 table gave S1 to `priya` and S2 to `arjun`. That confounds two variables: a difference between those two runs could come from the event or from the persona, and nothing in the output separates them. The harness varies one factor at a time instead - S1..S4 hold the persona fixed and vary the event, S1/S5a/S5b hold the event fixed and vary the persona. S5 was one row naming two personas, so the two runs it implied had no separate identity and could not be cited individually; it is now S5a and S5b.

| ID | Round-1 spec | Now | Why |
|---|---|---|---|
| S1 | priya | meera | fixed persona across S1..S4 so the event is the only variable; the persona contrast moved to S1/S5a/S5b on one event |
| S2 | arjun | meera | fixed persona across S1..S4 so the event is the only variable |
| S3 | priya | meera | fixed persona across S1..S4 so the event is the only variable |
| S4 | arjun | meera | fixed persona across S1..S4 so the event is the only variable |
| S5a | part of S5 | priya | S5 named two personas in one row, so the two runs it implies had no separate identity in any result table; split so each can be cited |
| S5b | part of S5 | arjun | the finance director half of the original S5 row; a larger decision value, so the deferral arithmetic differs on identical evidence |

S6 and S7 were never reassigned. No injected event, slice, window or seed changed: the divergence is in who reads each scenario, not in what the data contains.

## Deliberate data quirks

- `channel` value `marketplace` was renamed `Marketplace` on 2026-06-14, splitting that series. Both spellings exist in `fact_orders`. This is event E5.
- `fact_sessions` has ~3.5% null `region` (unknown geo), forcing an explicit completeness check.
- Support-ticket volume carries a Monday spike, so a naive day-over-day count comparison mis-reads Mondays as signal.
- `NewLaunch` does not exist before 2026-06-27, giving it sparse history.
- Source `S3` finance is stamped T+3, so the most recent week is genuinely unavailable rather than zero.
