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
#
# The neutrals below were retuned against a Stitch visual reference (a light
# grey page carrying a centred white worksheet). **The semantic colours were
# deliberately NOT retuned.** The reference proposes a brighter red (#dc2626)
# and green (#16a34a); adopting them would make red louder, which is precisely
# what the COVID-dashboard reasoning in this file's docstring argues against.
# Surfaces and spacing carry the visual change; meaning-bearing colour does not
# move.
# --------------------------------------------------------------------------
INK = "#12161f"
INK_SOFT = "#4a5568"
INK_FAINT = "#8b95a5"
RULE = "#e4e4e7"
CANVAS = "#ffffff"
CANVAS_SOFT = "#fafafa"

#: The page behind the worksheet. A worksheet needs a desk to sit on.
PAGE = "#f5f5f7"
#: Hairline used inside cards, one step lighter than RULE.
RULE_SOFT = "#eeeef1"

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


#: Font stacks. Inter and JetBrains Mono are named first so the reference
#: typefaces are used where a machine has them, and the stack falls back to
#: system faces otherwise. Nothing is fetched from a remote host: a decision
#: workspace that renders differently depending on whether a CDN answered is
#: worse than one that renders in Segoe UI every time.
SANS = ('Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, '
        'sans-serif')
MONO = ('"JetBrains Mono", ui-monospace, "SF Mono", "Cascadia Mono", Menlo, '
        'Consolas, monospace')

#: One elevation, used sparingly. The worksheet lifts off the page; nothing
#: else does.
SHADOW_CARD = "0 1px 2px rgba(18,22,31,.04), 0 8px 32px -12px rgba(18,22,31,.10)"


def css() -> str:
    """Global stylesheet. Injected once per session."""
    return f"""
<style>
  /* ---- reset Streamlit's defaults toward a document, not an app ---- */
  #MainMenu, footer, header {{ visibility: hidden; }}

  /* The page is a desk; the block container is a worksheet resting on it. */
  .stApp {{ background:{PAGE}; }}
  .block-container {{
      max-width: 900px;
      padding: 2.2rem 3rem 3.5rem 3rem;
      background:{CANVAS};
      border:1px solid {RULE};
      border-radius:16px;
      box-shadow:{SHADOW_CARD};
      margin-top:1.4rem; margin-bottom:2.5rem;
  }}
  html, body, [class*="css"] {{
      font-family: {SANS};
      color: {INK};
      -webkit-font-smoothing: antialiased;
  }}

  /* ---- masthead: compact bar, brand left, live context right ---- */
  .bi-mast {{
      display:flex; align-items:center; justify-content:space-between;
      border-bottom:1px solid {RULE}; padding-bottom:.85rem; margin-bottom:1.8rem;
      gap:1rem; flex-wrap:wrap;
  }}
  .bi-mast .bi-brand {{
      font-size:.95rem; font-weight:650; letter-spacing:-.015em; color:{INK};
  }}
  .bi-mast .bi-ctx {{
      font-size:.74rem; color:{INK_SOFT}; display:flex; align-items:center;
      gap:.55rem;
  }}
  .bi-mast .bi-ctx-tag {{
      font-size:.62rem; font-weight:700; letter-spacing:.08em;
      text-transform:uppercase; color:{INK_FAINT};
      background:{CANVAS_SOFT}; border:1px solid {RULE};
      padding:.22rem .5rem; border-radius:5px;
  }}

  /* ---- section headings: quiet, structural, ruled ---- */
  .bi-sec {{
      font-size:.68rem; font-weight:700; letter-spacing:.1em;
      text-transform:uppercase; color:{INK_FAINT};
      margin:2.3rem 0 .85rem 0; padding-bottom:.5rem;
      border-bottom:1px solid {RULE_SOFT};
  }}

  /* ---- level 1: the movement ----
     Tabular figures, because this is an instrument reading. Kept large: the
     Amber Alert finding that recognition beats recollection is why it is the
     biggest element on the page, and the visual reference's smaller metric
     size would trade that away for tidiness. */
  .bi-kpi {{
      font-size:.66rem; color:{INK_FAINT}; margin-bottom:.5rem;
      letter-spacing:.1em; text-transform:uppercase; font-weight:700;
  }}
  .bi-move {{
      font-family:{MONO};
      font-size:2.7rem; font-weight:600; line-height:1.0;
      letter-spacing:-.03em; color:{INK}; margin:0;
      font-variant-numeric: tabular-nums;
  }}
  .bi-window {{
      font-family:{MONO}; font-size:.8rem; color:{INK_SOFT};
      margin-top:.55rem; font-variant-numeric: tabular-nums;
  }}

  /* ---- chips ---- */
  .bi-chip {{
      display:inline-block; padding:.28rem .7rem; border-radius:999px;
      font-size:.64rem; font-weight:700; letter-spacing:.08em;
      text-transform:uppercase; border:1px solid transparent;
      white-space:nowrap;
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

  /* ---- epistemic classes (Part 5) — unchanged in meaning ---- */
  .bi-claim {{
      border-left:3px solid; padding:.7rem .95rem; margin:.5rem 0;
      border-radius:0 8px 8px 0; font-size:.88rem; line-height:1.6;
  }}
  .bi-claim .bi-tag {{
      display:block; font-size:.6rem; font-weight:700; letter-spacing:.1em;
      opacity:.8; margin-bottom:.3rem;
  }}

  /* ---- cards ---- */
  .bi-card {{
      border:1px solid {RULE}; border-radius:10px; padding:1rem 1.1rem;
      background:{CANVAS}; margin-bottom:.7rem;
  }}
  .bi-card-head {{ font-size:.85rem; font-weight:650; color:{INK};
                   margin-bottom:.3rem; letter-spacing:-.01em; }}
  .bi-card-meta {{ font-size:.7rem; color:{INK_FAINT}; letter-spacing:.01em; }}
  .bi-card-body {{
      font-size:.84rem; color:{INK_SOFT}; line-height:1.6; margin-top:.55rem;
      background:{CANVAS_SOFT}; border:1px solid {RULE_SOFT};
      border-radius:7px; padding:.6rem .75rem;
  }}

  /* ---- reliability block ---- */
  .bi-rel {{ border:1px solid {RULE}; border-left:3px solid {ACCENT};
            border-radius:0 10px 10px 0; padding:1rem 1.1rem;
            background:{CANVAS}; }}
  .bi-rel-band {{ font-size:1.02rem; font-weight:700; letter-spacing:-.015em; }}
  .bi-rel-basis {{ font-size:.83rem; color:{INK_SOFT}; margin-top:.32rem;
                   line-height:1.55; }}
  .bi-rel-caveat {{ font-size:.72rem; color:{INK_FAINT}; margin-top:.45rem;
                    font-style:italic; line-height:1.5; }}

  /* ---- the action card: the one place with real presence ---- */
  .bi-action {{
      border:1px solid {RULE}; border-radius:14px; padding:1.5rem 1.6rem;
      background:{CANVAS_SOFT}; margin-top:.3rem;
  }}
  .bi-rail {{
      border-left:1px solid {RULE}; padding-left:1.3rem; height:100%;
  }}
  .bi-rail-k {{
      font-size:.6rem; font-weight:700; letter-spacing:.09em;
      text-transform:uppercase; color:{INK_FAINT}; margin-bottom:.15rem;
  }}
  .bi-rail-v {{ font-size:.82rem; color:{INK}; margin-bottom:.95rem;
                line-height:1.45; }}
  .bi-rail-v.mono {{ font-family:{MONO}; font-weight:600;
                     font-variant-numeric: tabular-nums; }}

  /* ---- abstention: quieter than a finding, on purpose ---- */
  .bi-abstain {{
      border:1px solid {RULE}; border-radius:12px; padding:1.6rem 1.7rem;
      background:{CANVAS_SOFT};
  }}
  .bi-abstain-title {{ font-size:1.12rem; font-weight:650; color:{INK};
                       margin-bottom:.5rem; letter-spacing:-.015em; }}
  .bi-abstain-body {{ font-size:.88rem; color:{INK_SOFT}; line-height:1.65; }}

  /* ---- key/value rows for audit ---- */
  .bi-kv {{ display:flex; padding:.38rem 0; border-bottom:1px solid {RULE_SOFT};
            font-size:.79rem; }}
  .bi-kv .k {{ width:230px; color:{INK_FAINT}; flex-shrink:0; }}
  .bi-kv .v {{ color:{INK}; font-family:{MONO};
               font-size:.75rem; word-break:break-all; }}

  /* ---- primary action ---- */
  .stButton > button[kind="primary"] {{
      background:{ACCENT}; border:1px solid {ACCENT}; font-weight:600;
      border-radius:9px; padding:.6rem 1.4rem; letter-spacing:.01em;
  }}
  .stButton > button[kind="secondary"] {{
      border-radius:9px; border:1px solid {RULE};
  }}

  /* ---- tabs: questions, not modules ---- */
  .stTabs [data-baseweb="tab-list"] {{ gap:1.9rem; border-bottom:1px solid {RULE}; }}
  .stTabs [data-baseweb="tab"] {{
      font-size:.7rem; font-weight:700; padding:.5rem 0; color:{INK_FAINT};
      letter-spacing:.09em; text-transform:uppercase;
  }}
  .stTabs [aria-selected="true"] {{ color:{INK}; }}

  /* ---- sidebar: a quiet control rail, not a second workspace ---- */
  section[data-testid="stSidebar"] {{
      background:{CANVAS}; border-right:1px solid {RULE};
  }}
  section[data-testid="stSidebar"] .block-container {{
      background:transparent; border:0; box-shadow:none;
      border-radius:0; margin:0; padding-top:1.5rem;
  }}

  /* ---- progress ---- */
  .bi-step {{ font-size:.85rem; color:{INK_SOFT}; padding:.18rem 0; }}
  .bi-step .done {{ color:{SUPPORT}; font-weight:700; }}

  /* ---- expanders: recede until wanted ---- */
  .streamlit-expanderHeader, [data-testid="stExpander"] summary {{
      font-size:.8rem; color:{INK_SOFT};
  }}
  [data-testid="stExpander"] {{
      border:1px solid {RULE}; border-radius:10px; background:{CANVAS};
  }}
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
