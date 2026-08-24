# Pitch deck — visual QA

Method: each of the 11 slides was rendered to PNG at the canvas's native
1600×900 (3200×1800 at the 2x capture used for print quality) via
`python -m submission.deck.render`, then inspected as a rendered image —
not "looks fine" by reading the HTML. Two real defects were found this way
and are recorded below with what was wrong, not just that something was
fixed.

Checked per slide: clipping, overflow, unreadable text, alignment,
inconsistent margins/font sizes, broken diagrams, source-strip visibility,
contrast, accidental empty areas, pixelation, purple/neutral consistency.

## Findings summary

Two defects were real bugs, not polish:

1. **Slide 05 — broken sentence rendering.** The `.impact .desc` component
   is `display:flex`. Rich inline HTML (`<b>`, `<span>`) placed directly
   inside it was fragmented: the browser treats every child element *and*
   every text node between them as a separate flex item, so a single
   sentence rendered as scattered columns instead of flowing prose.
   **Fixed** by wrapping the sentence in one `<span>` so `.desc` has exactly
   one flex child, which lays out its own contents as normal inline flow.
2. **Slides 06, 10, 11 — `.flow` / `.chevrons` rendered as a vertical
   stack instead of a horizontal sequence.** After adding `.body.fill` to
   reduce dead space (see below), any `.flow` or `.chevrons` block sitting
   as a *direct* child of `.body.fill` was caught by the rule
   `.body.fill > div:not(.grid):not(.band) { flex-direction: column }`,
   which is more specific than the component's own `.flow { display:flex }`
   and silently overrides its row direction. The design system's own
   reference markup avoids this by always wrapping `.flow` one level
   deeper (inside a plain `<div>` with a kicker above it) — that wrapper
   absorbs the column rule while the `.flow` itself, now a grandchild,
   keeps its horizontal layout. **Fixed** by wrapping the three affected
   blocks in a container `<div>`, matching the pattern the system already
   uses elsewhere (e.g. slide 01).

The remaining nine "issues" were a single, non-bug pattern: slides using
the default `.body` (rows spread by `justify-content: space-between`)
looked sparse when a slide only had 3–4 rows, leaving large gaps that read
as unfinished. Not a rendering defect — a legitimate design-density
problem, addressed once via `.body.fill` (rows grow to absorb the slack)
rather than per-slide.

## Per-slide results

| Slide | Pass/Fail | Issue | Resolution |
|---|:---:|---|---|
| 01 — The gap has not moved | **Pass** | None. Dense from first render — 4 rows (stat cards, reasons/quotes, 5-step flow, closing band) fill the canvas with no dead space. | — |
| 02 — The obvious fix is dangerous | **Pass** | Initial render: ~45% of the canvas was blank gap between the thesis banner, the 3-card row, and the chevron row — `.body`'s default row-spread has too few rows to fill 900px. | Applied `.body.fill`. Gaps collapsed to a small, intentional-looking margin above the footnote. Re-rendered and confirmed. |
| 03 — One engine, one screen | **Pass** | None. Real Streamlit screenshot (`assets/hero_s1_workspace.png`, captured live via Playwright against the running app — not a mock) renders cleanly in its frame via `object-fit: cover`; right-column bullets fully visible; no clipping. | — |
| 04 — Round 1 → Round 2 | **Pass** | Initial render: same accidental-empty-area pattern as slide 02, worse (two tables leave a visible gap before and after). | Applied `.body.fill`. Verified: tables now sit close to their headers; residual space is a normal-looking section break, not a void. |
| 05 — Every number is computed | **Pass** | **Two issues.** (1) Accidental empty area, same pattern. (2) **Critical**: the 109.9% explainer sentence rendered as scrambled, broken-up text fragments instead of a sentence — see Findings above. | Applied `.body.fill`; wrapped the `.impact .desc` content in a single `<span>`. Re-rendered and read the sentence end-to-end to confirm it now flows correctly. |
| 06 — Nothing ships unverified | **Pass** | **Two issues, sequentially.** (1) Accidental empty area. (2) After fixing (1) with `.body.fill`, the 4-step gate flow rendered as four full-width stacked boxes instead of a horizontal sequence — see Findings above. | Wrapped `.flow` in a container `<div>`. Re-rendered: flow is now a correct horizontal 4-step sequence with visible arrows, and the slide is dense with no dead space. |
| 07 — It declines | **Pass** | Initial render: accidental empty area between the 3 outcome-percentage cards, the 3 scenario cards, and the 2 explanation cards. | Applied `.body.fill`. All three card rows now stretch to fill the canvas; no residual gap. |
| 08 — Who may see what | **Pass** | Initial render: accidental empty area below the persona row and inside two of the lower cards. | Applied `.body.fill`. Gaps substantially reduced; minor whitespace remains inside two cards but reads as padding, not as missing content. |
| 09 — What we measured | **Pass** | Initial render: accidental empty area between the label band, the two evidence tables, and the "numbers that got worse" card. | Applied `.body.fill`. Now dense — tables, the highlighted card, and the closing band fill the canvas edge to edge. |
| 10 — Prototype readiness | **Pass** | **Two issues, sequentially**, identical pattern to slide 06: (1) accidental empty area; (2) the 4-step production-migration flow rendered as a vertical stack after the first fix. | Wrapped `.flow` in a container `<div>`. Re-rendered: correct horizontal migration sequence with arrows; slide fills the canvas with no dead zones. |
| 11 — Why this wins | **Pass** | **Two issues, sequentially**, identical pattern: (1) accidental empty area; (2) the 3-stage roadmap chevrons rendered as a vertical stack after the first fix. | Wrapped `.chevrons` in a container `<div>`. Re-rendered: correct horizontal Now/V2/V3 chevron sequence; comparison table, card, chevrons and both closing bands are all fully visible with consistent margins. |

## Cross-slide consistency checks

| Check | Result |
|---|---|
| Canvas size | All 11 PNGs confirmed exactly 3200×1800 px (1600×900 at 2x) via a direct pixel-dimension check — not assumed. |
| Purple/neutral palette | `theme-accenture` tokens used throughout (`#A100FF` primary, `#460073` deep, `#F4EAFF` tint, `#1B1B25` ink, `#FFC53D` accent gold, `#2E1046` dark plate). No hard-coded colour introduced outside the vendored `design/tokens.css`. |
| Typography | Arial only, matching the Round 1 template mandate — no other font-family declared anywhere in the deck's CSS or inline styles. |
| Source strip | Present on all 11 slides, in the `.footnote` position, non-empty. |
| Tab navigation | Present and correctly highlighted per section (Problem / Solution / Trust & Access / Evidence & Close) on every slide, consistent with the design system's "required for 6+ slide decks" rule. |
| Pixelation | None — hero screenshot was captured at `device_scale_factor: 2` (2800px source width before crop) specifically so it would not visibly downscale-blur inside its frame. |
| Slide-title grammar | Every title is `<num> | <claim>`, colon not dash, matching the Round 1 convention recovered from the submitted deck's actual XML (`docs/ROUND1_MASTER.md` §6 cross-checked against the live `.pptx`). |

## What this QA did not check

- **Print/PDF fidelity beyond page count.** `submission/R2_BUSINESSINTELLIGENCE_PITCH.pdf` was confirmed to contain 11 pages in slide order; each page was not re-screenshotted from the PDF itself (the PNGs embedded into it are the ones inspected above, and PNG→PDF via Pillow is a lossless RGB embed, not a re-render).
- **Cross-viewer rendering** (Acrobat, Preview, PowerPoint import) — only Chrome's rendering was verified, matching the Round 1 workflow's own export path (Chrome print-to-PDF).
