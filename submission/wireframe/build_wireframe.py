"""Generate an Excalidraw wireframe for the 6-slide BusinessIntelligence.ai deck.

Layout DNA is lifted from the HiLabs PS3 deck (1920x1080, persistent section
nav, thesis banner, 3-column evidence grid with per-row source lines, two-panel
lower zone, centre-stage visual flanked by callouts).

    python submission/wireframe/build_wireframe.py

Produces `businessintelligence_wireframe.excalidraw` — drag it onto
excalidraw.com to open and edit.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "businessintelligence_wireframe.excalidraw"

W, H = 1920, 1080          # one slide canvas
GAP_X, GAP_Y = 180, 200    # spacing between slides on the whiteboard
COLS = 2

# Accenture-continuous palette
PURPLE = "#a100ff"
DEEP = "#460073"
TINT = "#f4eaff"
INK = "#1b1b25"
GREY = "#5f6070"
DANGER = "#c0245c"
SUCCESS = "#0b7b5c"
GOLD = "#ffc53d"
RULE = "#d8d8de"
WHITE = "#ffffff"
SOFT = "#f7f7f9"

_els: list[dict] = []
_seed = random.Random(7)


def _base(kind: str, x: float, y: float, w: float, h: float, **kw) -> dict:
    e = {
        "id": f"e{len(_els)}_{_seed.randint(1000, 9999)}",
        "type": kind,
        "x": round(x, 1), "y": round(y, 1),
        "width": round(w, 1), "height": round(h, 1),
        "angle": 0,
        "strokeColor": kw.pop("stroke", INK),
        "backgroundColor": kw.pop("bg", "transparent"),
        "fillStyle": kw.pop("fill", "solid"),
        "strokeWidth": kw.pop("sw", 1),
        "strokeStyle": kw.pop("ss", "solid"),
        "roughness": kw.pop("rough", 0),
        "opacity": kw.pop("opacity", 100),
        "groupIds": kw.pop("groups", []),
        "frameId": None,
        "roundness": kw.pop("round", None),
        "seed": _seed.randint(1, 2 ** 31),
        "version": 1, "versionNonce": _seed.randint(1, 2 ** 31),
        "isDeleted": False, "boundElements": None,
        "updated": 1, "link": None, "locked": False,
    }
    e.update(kw)
    return e


def rect(x, y, w, h, *, bg="transparent", stroke=RULE, sw=1, radius=True, ss="solid", groups=None):
    e = _base("rectangle", x, y, w, h, bg=bg, stroke=stroke, sw=sw, ss=ss,
              round={"type": 3} if radius else None, groups=groups or [])
    _els.append(e)
    return e


def txt(x, y, s, *, size=16, color=INK, w=None, align="left", groups=None):
    lines = s.count("\n") + 1
    est_w = w if w is not None else max(10, int(len(max(s.split("\n"), key=len)) * size * 0.52))
    e = _base("text", x, y, est_w, size * 1.25 * lines, stroke=color, groups=groups or [])
    e.update({
        "text": s, "fontSize": size, "fontFamily": 2,
        "textAlign": align, "verticalAlign": "top",
        "baseline": int(size * 0.9), "containerId": None,
        "originalText": s, "lineHeight": 1.25, "autoResize": True,
    })
    _els.append(e)
    return e


def line(x1, y1, x2, y2, *, stroke=RULE, sw=1, ss="solid"):
    e = _base("line", x1, y1, x2 - x1, y2 - y1, stroke=stroke, sw=sw, ss=ss)
    e["points"] = [[0, 0], [x2 - x1, y2 - y1]]
    e["lastCommittedPoint"] = None
    e["startBinding"] = None
    e["endBinding"] = None
    e["startArrowhead"] = None
    e["endArrowhead"] = None
    _els.append(e)
    return e


def arrow(x1, y1, x2, y2, *, stroke=PURPLE, sw=2):
    e = _base("arrow", x1, y1, x2 - x1, y2 - y1, stroke=stroke, sw=sw)
    e["points"] = [[0, 0], [x2 - x1, y2 - y1]]
    e["lastCommittedPoint"] = None
    e["startBinding"] = None
    e["endBinding"] = None
    e["startArrowhead"] = None
    e["endArrowhead"] = "arrow"
    _els.append(e)
    return e


# --------------------------------------------------------------------------
# composite blocks — the repeating furniture of the deck
# --------------------------------------------------------------------------
def slide_shell(ox, oy, num, title, active_section):
    """Canvas, persistent section nav, numbered claim-title bar."""
    rect(ox, oy, W, H, bg=WHITE, stroke=INK, sw=2, radius=False)

    # section nav (their signature element — judge always knows where they are)
    rect(ox, oy, W, 52, bg=DEEP, stroke=DEEP, radius=False)
    sections = ["Problem & Context", "Landscape & Goal", "Users & Journey",
                "Solution Design", "Roadmap & Business", "Risk & Future"]
    cx = ox + 40
    for i, s in enumerate(sections):
        on = (i == active_section)
        txt(cx, oy + 17, s.upper(), size=15,
            color=GOLD if on else "#b9a8cc")
        cx += len(s) * 9.4 + 46

    # numbered title bar
    rect(ox, oy + 52, W, 74, bg=PURPLE, stroke=PURPLE, radius=False)
    txt(ox + 40, oy + 74, f"{num:02d}", size=30, color="#dcb3ff")
    txt(ox + 100, oy + 74, title, size=29, color=WHITE)


def panel(ox, oy, x, y, w, h, header, *, hbg=PURPLE, body_bg="transparent"):
    """A panel = one coloured header band + open body. No nested cards."""
    rect(ox + x, oy + y, w, h, bg=body_bg, stroke=RULE)
    rect(ox + x, oy + y, w, 34, bg=hbg, stroke=hbg)
    txt(ox + x + 14, oy + y + 9, header.upper(), size=14, color=WHITE)


def stat(ox, oy, x, y, w, figure, label, *, color=PURPLE, size=44):
    txt(ox + x, oy + y, figure, size=size, color=color)
    txt(ox + x, oy + y + size * 1.15, label, size=13, color=GREY, w=w)


def bullets(ox, oy, x, y, items, *, size=14, lead=27, color=INK, w=420, bullet="—"):
    for i, s in enumerate(items):
        txt(ox + x, oy + y + i * lead, f"{bullet} {s}", size=size, color=color, w=w)


def band(ox, oy, y, text, *, bg=DEEP, color=WHITE, size=19, x=40, w=None):
    ww = w if w else W - 80
    rect(ox + x, oy + y, ww, 54, bg=bg, stroke=bg)
    txt(ox + x + 22, oy + y + 16, text, size=size, color=color, w=ww - 40)


def sources(ox, oy, y, text):
    txt(ox + 40, oy + y, text, size=12, color=GREY, w=W - 80)


def flow(ox, oy, x, y, w, nodes, *, h=78, gap=26, node_bg=TINT):
    n = len(nodes)
    nw = (w - gap * (n - 1)) / n
    for i, (head, sub) in enumerate(nodes):
        nx = x + i * (nw + gap)
        rect(ox + nx, oy + y, nw, h, bg=node_bg, stroke=PURPLE)
        txt(ox + nx + 12, oy + y + 12, head, size=14, color=DEEP, w=nw - 24)
        txt(ox + nx + 12, oy + y + 38, sub, size=12, color=GREY, w=nw - 24)
        if i < n - 1:
            arrow(ox + nx + nw + 4, oy + y + h / 2, ox + nx + nw + gap - 4, oy + y + h / 2)


def note(ox, oy, x, y, w, text, *, color=DANGER, size=12):
    """A red annotation for the wireframe reader (not deck copy)."""
    txt(ox + x, oy + y, text, size=size, color=color, w=w)


# ==========================================================================
# SLIDE 1 — Problem
# ==========================================================================
def slide1(ox, oy):
    slide_shell(ox, oy, 1,
                "A dashboard tells you what moved on Monday. The explanation arrives Thursday. "
                "The decision was made Tuesday.", 0)

    band(ox, oy, 142,
         '"Dashboards are great at telling you what\'s happening, but the moment you ask why…"'
         "   —  ThoughtSpot user, G2", bg=INK, size=18)

    # 3-column evidence grid, two rows, source line per row  (their p2 pattern)
    cols = [40, 670, 1300]
    cw = 580
    heads = ["THE GAP IS STRUCTURAL", "THE LABOUR IS THE COST", "THE OBVIOUS FIX MAKES IT WORSE"]
    r1 = [("73%", "of BI implementations fail on the diagnostic gap — not on technology"),
          ("~70%", "of analyst time spent investigating alerts that prove legitimate"),
          ("3 of 4", "risk factors where an LLM inverted the direction, under constrained prompting")]
    r2 = [("~21%", "of employees actively use the dashboards that cannot answer \"why\""),
          ("22%", "decline in detection accuracy past 30+ alerts reviewed a day"),
          ("24%", "worse abstention in reasoning-tuned models vs non-reasoning")]

    for i, x in enumerate(cols):
        rect(ox + x, oy + 216, cw, 30, bg=TINT, stroke=TINT)
        txt(ox + x + 12, oy + 223, heads[i], size=13, color=DEEP)

    for i, x in enumerate(cols):
        rect(ox + x + 8, oy + 268, 54, 54, bg=SOFT, stroke=RULE)   # icon slot
        txt(ox + x + 22, oy + 285, "icon", size=11, color=GREY)
        stat(ox, oy, x + 78, 262, cw - 90, r1[i][0], r1[i][1], size=38)
    sources(ox, oy, 356, "Sources:  sranalytics.io BI failure study   ·   Gartner 2025   ·   arXiv 2026 narrative-fidelity audit")
    line(ox + 40, oy + 380, ox + W - 40, oy + 380)

    for i, x in enumerate(cols):
        rect(ox + x + 8, oy + 404, 54, 54, bg=SOFT, stroke=RULE)
        txt(ox + x + 22, oy + 421, "icon", size=11, color=GREY)
        stat(ox, oy, x + 78, 398, cw - 90, r2[i][0], r2[i][1], size=38)
    sources(ox, oy, 492, "Sources:  sranalytics.io   ·   alert-fatigue research   ·   AbstentionBench, Kirichenko et al. 2025 (arXiv:2506.09038)")

    # the story timeline — the emotional spine
    panel(ox, oy, 40, 540, W - 80, 210, "The path a leader lives today")
    flow(ox, oy, 60, 592, W - 120, [
        ("MON", "Dashboard flags ↓ 25.0%"),
        ("TUE", "Decision taken — no explanation"),
        ("WED–THU", "Analyst reconciles 4+ tools"),
        ("THU", "Plausible, unranked, no confidence"),
        ("AFTER", "Window already closed"),
    ], h=90)
    txt(ox + 60, oy + 706, "Every step here is normal. That is the problem.", size=17, color=DANGER)

    band(ox, oy, 776,
         "The capability you want for root-cause analysis actively works against the humility you need. "
         "Gartner names the result — agent drift — and prescribes guardian layers.", bg=GOLD, color=INK, size=18)

    note(ox, oy, 40, 856,
         W - 80,
         "WIREFRAME NOTE — density target: 6 stat cells + 1 five-node flow + 2 bands. "
         "Emptiest zone is the timeline row; let it breathe. Icons are 54px glyphs, not illustrations.")


# ==========================================================================
# SLIDE 2 — Landscape & goal
# ==========================================================================
def slide2(ox, oy):
    slide_shell(ox, oy, 2,
                "Several categories produce an explanation. None of them declines to produce one.", 1)

    # left: what exists  |  right: the gaps  (their p2 lower-zone split)
    panel(ox, oy, 40, 150, 1080, 430, "What exists today")
    rows = [
        ("Dashboards", "Show what moved", "No cause, no confidence, no next step"),
        ("Threshold alerting", "Fire on a rule", "Fires on noise; trains people to ignore it"),
        ("Manual SQL analysis", "Everything — well", "Days not seconds; no trail that survives absence"),
        ("Generic BI copilots", "Write prose about a chart", "Fluent, unverified, never abstains"),
        ("Generic RAG assistants", "Cite documents", "No metric grounding, no decision rights"),
    ]
    txt(ox + 58, oy + 198, "CATEGORY", size=12, color=GREY)
    txt(ox + 380, oy + 198, "WHAT IT DOES", size=12, color=GREY)
    txt(ox + 700, oy + 198, "WHERE IT STOPS", size=12, color=DANGER)
    for i, (a, b, c) in enumerate(rows):
        yy = 228 + i * 66
        txt(ox + 58, oy + yy, a, size=15, color=INK, w=300)
        txt(ox + 380, oy + yy, b, size=14, color=GREY, w=300)
        txt(ox + 700, oy + yy, c, size=14, color=DANGER, w=400)
        line(ox + 56, oy + yy + 46, ox + 1104, oy + yy + 46)

    panel(ox, oy, 1150, 150, 730, 430, "The three gaps nobody closes", hbg=DANGER)
    gaps = [
        ("1  No tool says when it doesn't know.",
         "Every one of them always renders an answer.",
         "→ Six typed reasons to stop — sparse history, conflicting evidence, "
         "access denied, data quality, insufficient evidence, clarification needed — "
         "not one generic \"no results\" screen."),
        ("2  No tool separates measured from generated.",
         "A computed figure and an invented sentence look identical.",
         "→ Every number is computed before the model runs; the request carries no "
         "tools key, so nothing generated can reach the warehouse mid-answer."),
        ("3  No tool carries decision rights.",
         "An explanation with no owner and no bounded action is a report.",
         "→ Every recommendation names an owner, a monitoring metric, and a lever "
         "this persona may request — never one it can execute, and never a rollback."),
    ]
    for i, (h_, s_, p_) in enumerate(gaps):
        yy = 210 + i * 122
        txt(ox + 1172, oy + yy, h_, size=16, color=INK, w=680)
        txt(ox + 1172, oy + yy + 30, s_, size=14, color=GREY, w=680)
        txt(ox + 1172, oy + yy + 58, p_, size=12, color=SUCCESS, w=680)
        line(ox + 1168, oy + yy + 96, ox + 1862, oy + yy + 96)

    # impact strip — 4 measured figures
    panel(ox, oy, 40, 606, W - 80, 200, "What the prototype already demonstrates  ·  measured, not projected")
    figs = [("4–50 s", "movement → ranked, evidenced, verified explanation  [M]"),
            ("25%", "of demo scenarios end with NO recommendation — the feature  [M]"),
            ("0 / 10", "corrupted narratives that got past verification  [S]"),
            ("0", "restricted items reaching any stage, across a 6-stage leak chain  [M]")]
    for i, (f, l) in enumerate(figs):
        stat(ox, oy, 70 + i * 460, 664, 420, f, l, size=46)
    txt(ox + 70, oy + 762,
        "No revenue, cost-saving or time-saved figure is claimed anywhere in this project.  "
        "Value mechanisms and their limits are on slide 6.", size=13, color=GREY, w=1780)

    band(ox, oy, 830,
         "GOAL   —   Detect what is both statistically and commercially significant, explain it only when the "
         "evidence supports the words, and hand to a human whenever a human is likely to do better.", bg=DEEP)

    note(ox, oy, 40, 906, W - 80,
         "WIREFRAME NOTE — left table uses hairline row rules, NOT boxed cards. "
         "Red is reserved for the 'where it stops' column and the gaps panel header.")


# ==========================================================================
# SLIDE 3 — Users & journey
# ==========================================================================
def slide3(ox, oy):
    slide_shell(ox, oy, 3,
                "Three roles read the same event and need three different answers — and the system enforces the difference.", 2)

    people = [
        ("MEERA  ·  Analytics Lead", '"Is this defensible enough to circulate?"',
         ["Method, contribution, counterfactual", "Full lineage — 15 records per run"],
         "Investigation becomes review"),
        ("PRIYA  ·  Regional Ops Lead", '"Do I escalate, and to whom?"',
         ["Region-scoped analysis, named owner", "An action she is entitled to raise"],
         "DENIED crm_notes — and told how many items were withheld"),
        ("ARJUN  ·  Finance Director", '"Is this material to the quarter?"',
         ["Impact range with its basis named", "Calibrated reliability, explicit unknowns"],
         "Higher decision value — same evidence routes differently"),
    ]
    for i, (role, q, gets, twist) in enumerate(people):
        x = 40 + i * 620
        panel(ox, oy, x, 150, 580, 296, role)
        rect(ox + x + 18, oy + 200, 56, 56, bg=TINT, stroke=PURPLE)   # avatar glyph slot
        txt(ox + x + 88, oy + 208, q, size=16, color=DEEP, w=470)
        bullets(ox, oy, x + 20, 278, gets, size=14, w=540)
        rect(ox + x + 18, oy + 352, 544, 74, bg="#fdeef2", stroke=DANGER)
        txt(ox + x + 32, oy + 366, twist, size=14, color=DANGER, w=516)

    band(ox, oy, 468,
         "The analytical truth is identical for all three. Only entitlement and decision rights differ — "
         "and both are enforced by tests, not by styling.", bg=GOLD, color=INK, size=18)

    # two journeys on one axis
    panel(ox, oy, 40, 552, W - 80, 300, "The same movement, two paths")
    txt(ox + 62, oy + 604, "TODAY   ·   blind for days", size=15, color=DANGER)
    flow(ox, oy, 62, 630, W - 124, [
        ("Dashboard flags", "no cause attached"),
        ("Open 4+ tools", "manual reconciliation"),
        ("Cross-reference", "tickets · CRM · changelogs"),
        ("Write narrative", "unranked, no confidence"),
        ("Decide", "window already closed"),
    ], h=76, node_bg="#fdeef2")

    txt(ox + 62, oy + 730, "WITH THE SYSTEM   ·   decision before the damage", size=15, color=SUCCESS)
    flow(ox, oy, 62, 756, W - 124, [
        ("DETECT", "is it real and material?"),
        ("ATTRIBUTE", "what drove it, and where?"),
        ("RETRIEVE", "what corroborates it?"),
        ("VERIFY", "can every claim be checked?"),
        ("RECOMMEND", "who acts — or does it stop?"),
    ], h=76, node_bg="#eef6f1")

    note(ox, oy, 40, 878, W - 80,
         "WIREFRAME NOTE — the two flows must sit on the SAME x-axis so the reader compares positions, "
         "not shapes. Red track above, green track below. This is the most persuasive slide: give it air.")


# ==========================================================================
# SLIDE 4 — Solution I
# ==========================================================================
def slide4(ox, oy):
    slide_shell(ox, oy, 4,
                "Every number a user sees is computed by SQL, statistics or a business rule — never generated.", 3)

    # LEFT — Detect
    panel(ox, oy, 40, 150, 920, 700, "Detect  —  is it real, and does it matter?")
    txt(ox + 60, oy + 202, "PAIN POINTS", size=13, color=DANGER)
    bullets(ox, oy, 60, 228, [
        "Noise looks like signal — alerts fire on fluctuation and train people to ignore them.",
        "Statistical significance ≠ business significance. A real 0.4% move is not worth a Monday.",
        "Sparse history breaks naive baselines — new categories have no seasonal profile.",
    ], w=860, lead=34, color=INK)

    txt(ox + 60, oy + 348, "SOLUTION", size=13, color=SUCCESS)
    rect(ox + 58, oy + 374, 884, 66, bg="#eef6f1", stroke=SUCCESS)
    txt(ox + 74, oy + 388,
        "STL decomposition  →  robust MAD z-score  →  PELT changepoint  →  materiality gate\n"
        "with BOTH a statistical leg and a business leg. Both must pass.", size=14, color=INK, w=856)

    flow(ox, oy, 60, 464, 880, [
        ("Coverage", "gate"), ("STL", "decompose"), ("MAD z", "robust"),
        ("PELT", "changepoint"), ("Materiality", "stat ∧ business"),
    ], h=72)
    txt(ox + 60, oy + 556, "OUTCOMES", size=13, color=GREY)
    for i, o in enumerate(["MATERIAL EVENT", "NO MATERIAL FINDING", "SPARSE HISTORY", "INSUFFICIENT DATA"]):
        rect(ox + 58 + i * 222, oy + 582, 208, 42, bg=TINT, stroke=PURPLE)
        txt(ox + 70 + i * 222, oy + 594, o, size=12, color=DEEP, w=190)

    rect(ox + 58, oy + 648, 884, 88, bg=SOFT, stroke=RULE)
    txt(ox + 74, oy + 662,
        "RESULT   ·   0 false positives across 48 clean slices  [S]\n"
        "Injected-event recall 1.000 — but those events were built to be detectable by this method,\n"
        "so the false-positive figure is the meaningful one.", size=13, color=INK, w=856)

    # RIGHT — Attribute
    panel(ox, oy, 990, 150, 890, 700, "Attribute  —  what drove it, and where?")
    txt(ox + 1010, oy + 202, "PAIN POINTS", size=13, color=DANGER)
    bullets(ox, oy, 1010, 228, [
        "Correlation presented as causation — two series moving together is not evidence.",
        "Driver trees approximate; a residual means the decomposition is incomplete.",
        "\"What moved\" without \"where\" is unactionable — the regional total hides the broken slice.",
    ], w=830, lead=34)

    txt(ox + 1010, oy + 348, "SOLUTION", size=13, color=SUCCESS)
    rect(ox + 1008, oy + 374, 854, 84, bg="#eef6f1", stroke=SUCCESS)
    txt(ox + 1024, oy + 388,
        "LMDI index decomposition — residual-free, closes to 0.000000000%\n"
        "Adtributor localises the slice  ·  moving-block bootstrap tests rank stability\n"
        "Difference-in-differences + parallel-trend check licenses the word \"caused\"",
        size=13, color=INK, w=826)

    # live output mock — the hero exhibit
    rect(ox + 1008, oy + 480, 854, 226, bg=WHITE, stroke=INK, sw=2)
    txt(ox + 1026, oy + 494, "LIVE OUTPUT  ·  S1", size=11, color=GREY)
    txt(ox + 1026, oy + 516, "Net Revenue · West × Web/Mobile App", size=13, color=GREY)
    txt(ox + 1026, oy + 540, "↓ 25.0%", size=40, color=INK)
    rect(ox + 1180, oy + 548, 190, 32, bg=TINT, stroke=PURPLE)
    txt(ox + 1194, oy + 556, "MATERIAL MOVEMENT", size=12, color=DEEP)
    txt(ox + 1026, oy + 596, "52,750 INR against a baseline of 211,204 INR  ·  12 Jul → 26 Jul 2026",
        size=12, color=GREY, w=820)
    # diverging bars
    txt(ox + 1026, oy + 626, "Conversion Rate", size=12, color=GREY)
    rect(ox + 1170, oy + 624, 300, 18, bg="#f3d6de", stroke=DANGER)
    txt(ox + 1482, oy + 626, "−57,959", size=12, color=DANGER)
    txt(ox + 1026, oy + 652, "Sessions", size=12, color=GREY)
    rect(ox + 1170, oy + 650, 40, 18, bg="#dcece4", stroke=SUCCESS)
    txt(ox + 1222, oy + 652, "+5,721", size=12, color=SUCCESS)
    txt(ox + 1026, oy + 678, "Average Order Value", size=12, color=GREY)
    rect(ox + 1170, oy + 676, 8, 18, bg="#f3d6de", stroke=DANGER)
    txt(ox + 1190, oy + 678, "−370", size=12, color=DANGER)

    rect(ox + 1008, oy + 722, 854, 108, bg=GOLD, stroke=GOLD)
    txt(ox + 1026, oy + 736,
        "Conversion rate accounts for 109.9% — MORE than the whole movement — because sessions\n"
        "rose and partly offset it. An exact identity closes to zero, so the system explains the\n"
        "figure rather than clipping it.  No language model generates a self-explaining share above 100%.",
        size=13, color=INK, w=826)

    note(ox, oy, 40, 872, W - 80,
         "WIREFRAME NOTE — this slide is diagram-led, not prose-led. Same skeleton both halves: "
         "PAIN (red label) → SOLUTION (green band) → mechanism flow → result strip. The 109.9% gold box is the single takeaway.")


# ==========================================================================
# SLIDE 5 — Solution II
# ==========================================================================
def slide5(ox, oy):
    slide_shell(ox, oy, 5,
                "Nothing ships unverified — and when the evidence conflicts, the system refuses to answer.", 3)

    # LEFT — Verify
    panel(ox, oy, 40, 150, 920, 700, "Verify  —  can every claim be checked?")
    txt(ox + 60, oy + 200, "PAIN POINTS", size=13, color=DANGER)
    bullets(ox, oy, 60, 224, [
        "Fluent prose is unfalsifiable — a confident sentence and a correct one look the same.",
        "Prompt instructions are not controls. \"Don't hallucinate\" is a request, not a mechanism.",
        "A model that can query can fabricate a query result.",
    ], w=860, lead=32)

    flow(ox, oy, 60, 328, 880, [
        ("GATE 1", "sufficiency"), ("FREEZE", "bundle hashed"),
        ("NARRATE", "typed schema"), ("GATE 2", "10 checks"),
        ("DELIVER", "or fail closed"),
    ], h=72)

    # CAN / CANNOT — the payload
    rect(ox + 58, oy + 424, 434, 264, bg="#eef6f1", stroke=SUCCESS)
    rect(ox + 508, oy + 424, 434, 264, bg="#fdeef2", stroke=DANGER)
    txt(ox + 76, oy + 436, "THE MODEL CAN", size=14, color=SUCCESS)
    txt(ox + 526, oy + 436, "THE MODEL CANNOT", size=14, color=DANGER)
    bullets(ox, oy, 76, 470, [
        "Write a sentence from the frozen bundle",
        "Personalise wording to the persona",
        "Explain a decomposition already computed",
    ], w=400, lead=42, size=13)
    bullets(ox, oy, 526, 470, [
        "Calculate any KPI or statistic",
        "Choose the driver or its ranking",
        "Query the warehouse — no `tools` key, absent not empty",
        "State a confidence — Narrative has no such field",
        "Choose what happens next",
    ], w=400, lead=38, size=13)

    rect(ox + 58, oy + 706, 884, 56, bg=SOFT, stroke=RULE)
    txt(ox + 74, oy + 720,
        "10 / 10 corrupted narratives blocked   ·   0 of 6 valid ones wrongly rejected   ·   "
        "9 / 9 injected violations caught  [S]", size=13, color=INK, w=856)

    rect(ox + 58, oy + 776, 884, 62, bg="#fdeef2", stroke=DANGER)
    txt(ox + 74, oy + 788,
        "Gate 2 blocked our OWN fallback template. We had documented it as unfailable by construction —\n"
        "it was unfailable by luck.  A gate that only ever passes what we produce is not a gate.",
        size=13, color=INK, w=856)

    # RIGHT — Refuse & act
    panel(ox, oy, 990, 150, 890, 700, "Refuse & act  —  who decides, and how far may it go?", hbg=DANGER)
    txt(ox + 1010, oy + 200, "PAIN POINTS", size=13, color=DANGER)
    bullets(ox, oy, 1010, 224, [
        "Guessing between two causes pages the wrong team.",
        "A confidence score implies a precision nobody has.",
        "\"Automate\" is ambiguous — request, or execute?",
    ], w=830, lead=32)

    txt(ox + 1010, oy + 330, "THREE WAYS IT STOPS", size=13, color=GREY)
    refusals = [
        ("S2 · CONFLICTING", "South × Apparel −21.9%.\nCompetitive pressure OR stock\navailability — different owners.",
         "Stops, states the question,\nhands it to a person"),
        ("S4 · SPARSE", "New category with 52 of the\n56 days a seasonal baseline\nneeds.", "Declines, and says\nhow long to wait"),
        ("S7 · IMMATERIAL", "Channel rename reads +5.9%\ngrowth. Real, commercially\nmeaningless.", "No alert, no cause,\nno recommendation"),
    ]
    for i, (h_, b_, o_) in enumerate(refusals):
        x = 1008 + i * 290
        rect(ox + x, oy + 356, 274, 210, bg=TINT, stroke=PURPLE)
        txt(ox + x + 14, oy + 368, h_, size=13, color=DEEP, w=250)
        txt(ox + x + 14, oy + 394, b_, size=12, color=INK, w=250)
        txt(ox + x + 14, oy + 470, o_, size=12, color=DANGER, w=250)

    rect(ox + 1008, oy + 584, 854, 74, bg=SOFT, stroke=RULE)
    txt(ox + 1024, oy + 596,
        "The pause is a REAL interrupt on a durable checkpoint — resuming gives the same run with an\n"
        "identical bundle hash. Only HIGH clears the ten-case floor; MEDIUM and LOW report UNCALIBRATED.",
        size=13, color=INK, w=826)

    rect(ox + 1008, oy + 676, 854, 62, bg=GOLD, stroke=GOLD)
    txt(ox + 1024, oy + 690,
        "The button says \"RAISE THE REQUEST.\"  It does not say \"roll back.\"\n"
        "The enterprise fear is not a wrong explanation — it's a correct explanation wired to the wrong action.",
        size=13, color=INK, w=826)

    rect(ox + 1008, oy + 756, 854, 82, bg=DEEP, stroke=DEEP)
    txt(ox + 1024, oy + 770,
        "4 AUTOMATED   ·   2 ROUTED TO A HUMAN   ·   2 DECLINED   —   of 8\n"
        "Across the synthetic demonstration set, built to exercise every terminal state.\n"
        "NOT production workload rates.", size=13, color=WHITE, w=826)

    note(ox, oy, 40, 872, W - 80,
         "WIREFRAME NOTE — the CAN/CANNOT split and the three refusal cards are the two things a judge "
         "should remember. Everything else on this slide supports them.")


# ==========================================================================
# SLIDE 6 — Roadmap, business & risk
# ==========================================================================
def slide6(ox, oy):
    slide_shell(ox, oy, 6,
                "A working prototype today, a pilot that replaces assumptions with measurements, "
                "and the four risks we state before you ask.", 4)

    # roadmap: 3 phases x 4 attributes
    panel(ox, oy, 40, 150, W - 80, 300, "Phased roadmap  —  each phase replaces an assumption with a measurement")
    labels = ["SCOPE", "TECHNICAL", "PROVES", "TRIGGER TO ADVANCE"]
    phases = [
        ("NOW  ·  Round 2 prototype",
         ["6 KPIs · 3 sources · 3 personas\n8 scenarios · 1,336 documents",
          "26-node graph · 11 typed terminals\n574 tests passing",
          "The mechanism works and\nknows its limits",
          "—"]),
        ("V2  ·  Enterprise pilot",
         ["One real KPI family,\none team, one quarter",
          "Enterprise IAM · real calibration\nlive LLM evaluation",
          "BASELINE time-to-explanation —\nthe measurement that unlocks value",
          "Before any real data: IAM.\nSecurity before scale."]),
        ("V3  ·  Production platform",
         ["Multi-tenant, embedded in\nthe tools analysts already use",
          "Enterprise warehouse · per-tenant\nretrieval · workers · gateway",
          "Runs at organisational scale",
          "When it runs on >1 process:\ndurable workflow state"]),
    ]
    txt(ox + 58, oy + 200, "", size=12)
    for r, lab in enumerate(labels):
        txt(ox + 58, oy + 236 + r * 54, lab, size=12, color=GREY, w=200)
    for c, (head, vals) in enumerate(phases):
        x = 300 + c * 530
        rect(ox + x, oy + 194, 510, 34, bg=PURPLE if c == 0 else TINT, stroke=PURPLE)
        txt(ox + x + 12, oy + 202, head, size=13, color=WHITE if c == 0 else DEEP, w=486)
        for r, v in enumerate(vals):
            txt(ox + x + 12, oy + 236 + r * 54, v, size=12, color=INK, w=486)

    # launch plan | value mechanisms
    panel(ox, oy, 40, 472, 900, 264, "Launch plan")
    stages = [("1 · EARLY ACCESS", "Free, select design partners", "Convert synthetic evaluation\ninto real measurement"),
              ("2 · BROADER ROLL-OUT", "Tiered pricing", "Validate calibration on\nobserved outcomes"),
              ("3 · FULL INTEGRATION", "Subscription", "Become the layer above BI,\nnot beside it")]
    for i, (a, b, c) in enumerate(stages):
        x = 58 + i * 292
        rect(ox + x, oy + 520, 274, 34, bg=DEEP, stroke=DEEP)
        txt(ox + x + 12, oy + 528, a, size=12, color=WHITE, w=250)
        txt(ox + x + 12, oy + 566, b, size=13, color=INK, w=250)
        txt(ox + x + 12, oy + 596, c, size=12, color=GREY, w=250)

    panel(ox, oy, 970, 472, 910, 264, "Value mechanisms  —  and what we can / cannot evidence")
    mech = [("Faster diagnosis", "Pipeline verifies in 4–50s [M]", "How much analyst time it displaces"),
            ("Safer decisions", "0/10 false accept · S3 licence denied [S][M]", "— this is the measured one"),
            ("Governed action", "Lever-bound, owner-named, scoped [M]", "Cycle-time reduction in a real org"),
            ("Auditability", "15 lineage records/run, denials audited [M]", "That it satisfies any specific regime")]
    txt(ox + 990, oy + 520, "MECHANISM", size=11, color=GREY)
    txt(ox + 1200, oy + 520, "CAN EVIDENCE", size=11, color=SUCCESS)
    txt(ox + 1580, oy + 520, "CANNOT", size=11, color=DANGER)
    for i, (a, b, c) in enumerate(mech):
        yy = 544 + i * 46
        txt(ox + 990, oy + yy, a, size=13, color=INK, w=200)
        txt(ox + 1200, oy + yy, b, size=12, color=INK, w=370)
        txt(ox + 1580, oy + yy, c, size=12, color=GREY, w=280)
        line(ox + 988, oy + yy + 34, ox + 1872, oy + yy + 34)

    # risks | future
    panel(ox, oy, 40, 758, 1140, 210, "The four risks — stated before you ask", hbg=DANGER)
    risks = [("Synthetic evaluation", "Ground truth known by\nconstruction. Largest open\nrisk. 0 FP / 48 clean slices\nis the figure a generator\ncannot rig."),
             ("No live LLM eval", "No API key. Latency, tokens,\ncost unmeasured and NOT\nestimated. Harness written,\nunrun."),
             ("No authentication", "Persona is a dropdown.\nAuthorisation real and tested\n(32 tests, 0 leaks).\nIdentity is not."),
             ("~2 concurrent users", "Single-writer DB plus\naudit-on-read. \"Scales\nhorizontally\" would be\nfalse.")]
    for i, (h_, b_) in enumerate(risks):
        x = 58 + i * 278
        txt(ox + x, oy + 806, h_, size=13, color=DANGER, w=254)
        txt(ox + x, oy + 832, b_, size=11, color=INK, w=254)

    panel(ox, oy, 1210, 758, 670, 210, "Where it goes next")
    bullets(ox, oy, 1230, 806, [
        "Real calibration — replace 64 synthetic cases with observed outcomes",
        "Cross-KPI causality — movements that propagate, not one metric at a time",
        "Proactive monitoring — from \"explain this\" to \"this will move\"",
    ], w=630, lead=36, size=13)
    txt(ox + 1230, oy + 916,
        "NOT on the roadmap: autonomous agents, agent swarms, letting the model query the warehouse.\n"
        "Not deferred features — the architecture this exists to avoid.", size=12, color=DANGER, w=630)

    band(ox, oy, 990,
         "A dashboard tells you what moved. A language model will tell you why, confidently, whether or not it knows. "
         "This system tells you why, shows the evidence, recommends what to do — and tells you when it cannot.",
         bg=INK, size=18)


# ==========================================================================
def main() -> None:
    builders = [slide1, slide2, slide3, slide4, slide5, slide6]
    for i, b in enumerate(builders):
        ox = (i % COLS) * (W + GAP_X)
        oy = (i // COLS) * (H + GAP_Y)
        txt(ox, oy - 54, f"SLIDE {i + 1}", size=34, color=GREY)
        b(ox, oy)

    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "businessintelligence.ai wireframe generator",
        "elements": _els,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
        "files": {},
    }
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"elements: {len(_els)}  ·  6 slides at {W}x{H}, laid out {COLS} across")


if __name__ == "__main__":
    main()
