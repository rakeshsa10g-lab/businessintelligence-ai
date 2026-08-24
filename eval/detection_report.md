# Detection evaluation

> **SYNTHETIC_EVALUATION.** Precision and recall of the detection pipeline measured on the generated dataset — seed `20260821`, 535 days, 6 injected events (`python -m data.generate`). The events were injected by this repository, so their ground truth is known by construction rather than labelled by a human. These figures characterise the method on this dataset; they are **not** production accuracy and do not predict performance on real business data.
>
> A recall of 1.000 means every injected event was found. It does not mean no real-world movement would be missed: the injected events were built to be detectable by this method's own assumptions.


KPI `net_revenue`, window 2026-01-01..2026-08-17, 64 slices scanned.

| Metric | Value | Target |
|---|---:|---:|
| Precision | 1.000 | >= 0.85 |
| Recall | 1.000 | >= 0.90 |
| True positives | 16 | |
| False positives | 0 | |
| False negatives | 0 | |

## Per-event

| Event | Detected | Slices |
|---|---|---|
| E1 | yes | 11 |
| E2 | yes | 1 |
| E3 | yes | 1 |

## Schema artifact (E5)

| Check | Result |
|---|---|
| Rename | `'marketplace' -> 'Marketplace'` |
| Stitched series | 229 / 229 days continuous |
| Unstitched | severed into 164 + 65 days |
| Fires material event at rename | False |
| Passed | yes |

## Sparse-history routing

| Event | Exited via coverage gate | Outcome |
|---|---|---|
| E4 | yes | `SPARSE_HISTORY` |
