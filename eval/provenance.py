"""One provenance banner, emitted by every generated evaluation report.

Stage 12's claim audit found four reports carrying performance numbers with no
statement of where the data came from — including `detection_report.md`, whose
headline is **precision 1.000, recall 1.000**. Those numbers are real and they
are reproducible, but on a dataset this repository generates itself, with
events it injects and therefore knows the ground truth of.

An unlabelled 1.000 invites exactly one reading, and it is the wrong one. The
fix is not to delete the number — it is a legitimate result and deleting it
would hide a real property of the detector — but to make the sentence next to
it say what kind of result it is.

Kept as a shared constant rather than pasted into each generator so the four
reports cannot drift into saying four different things about the same dataset.
"""

from __future__ import annotations

#: Classification vocabulary used by `eval/claim_audit.md`.
SYNTHETIC_EVALUATION = "SYNTHETIC_EVALUATION"

#: The dataset every offline evaluation in this repository runs against.
DATASET = (
    "seed `20260821`, 535 days, 6 injected events "
    "(`python -m data.generate`)"
)


def banner(*, what: str, caveat: str = "") -> list[str]:
    """Markdown lines naming the dataset and what the numbers do not mean.

    `what` names the thing being measured, so the sentence reads specifically
    rather than as boilerplate a reader learns to skip.
    """
    lines = [
        f"> **{SYNTHETIC_EVALUATION}.** {what} measured on the generated "
        f"dataset — {DATASET}. The events were injected by this repository, "
        f"so their ground truth is known by construction rather than "
        f"labelled by a human. These figures characterise the method on this "
        f"dataset; they are **not** production accuracy and do not predict "
        f"performance on real business data.",
    ]
    if caveat:
        lines.append(">")
        lines.append(f"> {caveat}")
    lines.append("")
    return lines
