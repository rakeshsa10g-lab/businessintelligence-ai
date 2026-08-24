"""Visual language for the decision workspace.

One idea holds this file together: **colour carries meaning, never emphasis.**

The Growth.Design COVID-dashboard study found that red amplifies affect out of
proportion to the underlying risk, and that a dashboard which shouts at every
reading trains its reader to stop listening. A −25% revenue movement is serious
and also routine. So the movement figure is neutral ink, magnitude is carried by
the number itself, and red is spent only where it means *this contradicts the
explanation* or *this failed verification*.

Five semantic classes exist because Part 5 of the brief requires that a reader
never confuses a measured number with a generated sentence. They are visually
distinct by border and label, not by decoration.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# palette — deliberately small
# --------------------------------------------------------------------------
INK = "#12161f"
INK_SOFT = "#4a5568"
INK_FAINT = "#8b95a5"
RULE = "#e2e6ec"
CANVAS = "#ffffff"
CANVAS_SOFT = "#f7f8fa"

#: The single accent. Used for the primary action and nothing else.
ACCENT = "#1f4788"
ACCENT_SOFT = "#eef2f9"

#: Semantic states. Each appears in exactly one situation.
SUPPORT = "#2f6f4e"          # corroborating evidence, passed checks
SUPPORT_SOFT = "#eef5f1"
CONTRA = "#a33a3a"           # contradicting evidence, hard violations
CONTRA_SOFT = "#faeeee"
CAUTION = "#8a6d1f"          # uncalibrated, degraded, withheld
CAUTION_SOFT = "#fbf5e6"

#: The five epistemic classes of Part 5.
CLASS_COLOURS = {
    "fact":           ("#12161f", "#eef0f3", "OBSERVED FACT"),
    "analysis":       ("#1f4788", "#eef2f9", "ANALYTICAL RESULT"),
    "evidence":       ("#2f6f4e", "#eef5f1", "RETRIEVED EVIDENCE"),
    "hypothesis":     ("#6b4e9e", "#f2eef8", "HYPOTHESIS"),
    "recommendation": ("#8a5a1f", "#f9f1e6", "RECOMMENDATION"),
}


def css() -> str:
    """Global stylesheet. Injected once per session."""
    return f"""
<style>
  /* ---- reset Streamlit's defaults toward a document, not an app ---- */
  #MainMenu, footer, header {{ visibility: hidden; }}
  .block-container {{
      padding-top: 2.2rem; padding-bottom: 4rem;
      max-width: 1080px;
  }}
  html, body, [class*="css"] {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter,
                   system-ui, sans-serif;
      color: {INK};
  }}

  /* ---- masthead ---- */
  .bi-mast {{
      display:flex; align-items:baseline; justify-content:space-between;
      border-bottom:1px solid {RULE}; padding-bottom:.7rem; margin-bottom:1.6rem;
  }}
  .bi-mast .bi-brand {{
      font-size:.95rem; font-weight:650; letter-spacing:-.01em; color:{INK};
  }}
  .bi-mast .bi-ctx {{ font-size:.78rem; color:{INK_FAINT}; }}

  /* ---- section headings: quiet, structural ---- */
  .bi-sec {{
      font-size:.7rem; font-weight:700; letter-spacing:.09em;
      text-transform:uppercase; color:{INK_FAINT};
      margin:2.1rem 0 .7rem 0;
  }}

  /* ---- level 1: the movement ---- */
  .bi-kpi {{ font-size:.85rem; color:{INK_SOFT}; margin-bottom:.15rem;
             letter-spacing:.01em; }}
  .bi-move {{
      font-size:3.1rem; font-weight:680; line-height:1.02;
      letter-spacing:-.035em; color:{INK}; margin:0;
  }}
  .bi-window {{ font-size:.85rem; color:{INK_SOFT}; margin-top:.35rem; }}

  /* ---- chips ---- */
  .bi-chip {{
      display:inline-block; padding:.2rem .55rem; border-radius:3px;
      font-size:.68rem; font-weight:700; letter-spacing:.07em;
      text-transform:uppercase; border:1px solid transparent;
  }}
  .bi-chip-material {{ background:{ACCENT_SOFT}; color:{ACCENT};
                       border-color:#c9d6ea; }}
  .bi-chip-quiet    {{ background:{CANVAS_SOFT}; color:{INK_FAINT};
                       border-color:{RULE}; }}
  .bi-chip-support  {{ background:{SUPPORT_SOFT}; color:{SUPPORT};
                       border-color:#cfe2d7; }}
  .bi-chip-contra   {{ background:{CONTRA_SOFT}; color:{CONTRA};
                       border-color:#eccfcf; }}
  .bi-chip-caution  {{ background:{CAUTION_SOFT}; color:{CAUTION};
                       border-color:#e8dcb8; }}

  /* ---- epistemic classes (Part 5) ---- */
  .bi-claim {{
      border-left:3px solid; padding:.55rem .8rem; margin:.4rem 0;
      border-radius:0 3px 3px 0; font-size:.9rem; line-height:1.5;
  }}
  .bi-claim .bi-tag {{
      display:block; font-size:.6rem; font-weight:700; letter-spacing:.1em;
      opacity:.75; margin-bottom:.22rem;
  }}

  /* ---- cards ---- */
  .bi-card {{
      border:1px solid {RULE}; border-radius:5px; padding:.85rem 1rem;
      background:{CANVAS}; margin-bottom:.55rem;
  }}
  .bi-card-head {{ font-size:.82rem; font-weight:650; color:{INK};
                   margin-bottom:.2rem; }}
  .bi-card-meta {{ font-size:.72rem; color:{INK_FAINT}; }}
  .bi-card-body {{ font-size:.85rem; color:{INK_SOFT}; line-height:1.55;
                   margin-top:.35rem; }}

  /* ---- reliability block ---- */
  .bi-rel {{ border:1px solid {RULE}; border-left:3px solid {ACCENT};
            border-radius:0 5px 5px 0; padding:.85rem 1rem;
            background:{CANVAS}; }}
  .bi-rel-band {{ font-size:1.05rem; font-weight:700; letter-spacing:-.01em; }}
  .bi-rel-basis {{ font-size:.83rem; color:{INK_SOFT}; margin-top:.28rem;
                   line-height:1.5; }}
  .bi-rel-caveat {{ font-size:.72rem; color:{INK_FAINT}; margin-top:.4rem;
                    font-style:italic; }}

  /* ---- abstention: quieter than a finding, on purpose ---- */
  .bi-abstain {{
      border:1px solid {RULE}; border-radius:5px; padding:1.4rem 1.5rem;
      background:{CANVAS_SOFT};
  }}
  .bi-abstain-title {{ font-size:1.15rem; font-weight:650; color:{INK};
                       margin-bottom:.4rem; }}
  .bi-abstain-body {{ font-size:.9rem; color:{INK_SOFT}; line-height:1.6; }}

  /* ---- key/value rows for audit ---- */
  .bi-kv {{ display:flex; padding:.32rem 0; border-bottom:1px solid #f0f2f5;
            font-size:.8rem; }}
  .bi-kv .k {{ width:230px; color:{INK_FAINT}; flex-shrink:0; }}
  .bi-kv .v {{ color:{INK}; font-family:ui-monospace, "SF Mono", Menlo,
               Consolas, monospace; font-size:.76rem; word-break:break-all; }}

  /* ---- primary action ---- */
  .stButton > button[kind="primary"] {{
      background:{ACCENT}; border:1px solid {ACCENT}; font-weight:600;
      border-radius:4px;
  }}

  /* ---- tabs: questions, not modules ---- */
  .stTabs [data-baseweb="tab-list"] {{ gap:1.6rem; border-bottom:1px solid {RULE}; }}
  .stTabs [data-baseweb="tab"] {{
      font-size:.83rem; font-weight:550; padding:.4rem 0; color:{INK_FAINT};
  }}
  .stTabs [aria-selected="true"] {{ color:{INK}; }}

  /* ---- progress ---- */
  .bi-step {{ font-size:.86rem; color:{INK_SOFT}; padding:.16rem 0; }}
  .bi-step .done {{ color:{SUPPORT}; font-weight:700; }}
</style>
"""


def chip(text: str, kind: str = "quiet") -> str:
    return f'<span class="bi-chip bi-chip-{kind}">{text}</span>'


def claim(text: str, kind: str) -> str:
    """Render one epistemic class (Part 5).

    The label is always drawn. A reader should be able to tell a measured
    number from a generated sentence without having learned a colour code.
    """
    fg, bg, label = CLASS_COLOURS[kind]
    return (
        f'<div class="bi-claim" style="border-color:{fg};background:{bg};">'
        f'<span class="bi-tag" style="color:{fg};">{label}</span>{text}</div>'
    )


def kv(key: str, value: str) -> str:
    return f'<div class="bi-kv"><div class="k">{key}</div><div class="v">{value}</div></div>'


def humanise(text: str) -> str:
    """Strip implementation vocabulary out of user-facing sentences.

    Hypothesis statements are assembled from slice dictionaries, so they arrive
    as `channel=Web/Mobile App x region=West`. That is precise and it is also
    the builder's notation. Part 18 keeps that vocabulary in Method and Audit;
    on the decision screen it reads as a leaked internal.
    """
    import re

    if not text:
        return text
    # The value group excludes `(` and `)` as well as `,` and `x`. Without
    # that, a value can swallow across a closing paren into the NEXT
    # `key=value` pair entirely — found on the S2 analyst question, a
    # two-hypothesis comparison in parentheses, where the regex consumed from
    # the middle of the first clause to the middle of the second because
    # nothing stopped it at the `)` boundary between them.
    out = re.sub(r"(\w+)=([^,x()]+?)(?=\s*(?:,|\bx\b|\)|$))",
                 lambda m: m.group(2).strip(), text)
    out = out.replace(" x ", " and ")
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()
