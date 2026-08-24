"""The chokepoint test (Architecture Part 8.2, ADR-011).

This is the difference between claiming governance and having it. If a second
data-access path ever appears, this fails before anything else does.

Scope: the *runtime* packages. Two things are deliberately outside it:

  data/generate.py  — a build-time tool that creates the database. It runs
                      once, offline, and nothing at runtime imports it. The
                      second test below proves that isolation rather than
                      assuming it.
  tests/            — fixtures need read-only access to assert on the data.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RUNTIME_PACKAGES = [
    "semantic",
    "security",
    "detection",
    "attribution",
    "retrieval",
    "evidence",
    "llm",
    "trust",
    "recommend",
    "graph",
    "telemetry",
    "feedback",
    "ui",
]

GATEWAY = ROOT / "semantic" / "gateway.py"

# any of these in a runtime module means a second path to the database
FORBIDDEN = [
    re.compile(r"\bduckdb\s*\.\s*connect\b"),
    re.compile(r"\bconn\s*\.\s*execute\b"),
    re.compile(r"\bcon\s*\.\s*execute\b"),
]

# security/audit.py receives the gateway's connection as an argument and never
# opens one. It is part of the single write path, not a second read path, and
# test_audit_writer_cannot_open_a_connection below pins that down.
AUDIT = ROOT / "security" / "audit.py"
ALLOWED_EXECUTORS = {GATEWAY, AUDIT}


def _runtime_python_files() -> list[Path]:
    files: list[Path] = []
    for pkg in RUNTIME_PACKAGES:
        d = ROOT / pkg
        if d.exists():
            files.extend(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)
    return files


def test_only_the_gateway_opens_duckdb():
    """No runtime module may call duckdb.connect() except the gateway."""
    offenders = []
    for path in _runtime_python_files():
        if path in ALLOWED_EXECUTORS:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            if pattern.search(text):
                offenders.append(f"{path.relative_to(ROOT)} :: {pattern.pattern}")
    assert not offenders, (
        "Direct database access outside the gateway:\n  " + "\n  ".join(offenders)
    )


def test_gateway_is_the_only_module_importing_duckdb():
    """Importing duckdb at all outside the gateway is a smell worth failing on."""
    offenders = []
    for path in _runtime_python_files():
        if path == GATEWAY:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(a.name.split(".")[0] == "duckdb" for a in node.names):
                    offenders.append(str(path.relative_to(ROOT)))
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] == "duckdb":
                    offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"duckdb imported outside the gateway: {sorted(set(offenders))}"


def test_generator_is_not_reachable_from_runtime_code():
    """The build-time generator must never be imported by runtime code.

    This is what makes the generator's own database access safe to exempt.

    `data.spec` is explicitly fine to import: it is inert constants (dates,
    dimension names, the injected-event catalogue) with no database access —
    asserted separately below. `data.generate` is the module that writes, and
    that is the one that must stay unreachable.
    """
    offenders = []
    for path in _runtime_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom):
                base = node.module or ""
                names = [f"{base}.{a.name}" if base else a.name for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for n in names:
                if n == "data.generate" or n.startswith("data.generate."):
                    offenders.append(f"{path.relative_to(ROOT)} imports {n}")
    assert not offenders, (
        "Runtime code imports the build-time generator:\n  " + "\n  ".join(offenders)
    )


def test_data_spec_is_inert():
    """data/spec.py is importable by runtime code only because it does nothing."""
    spec_path = ROOT / "data" / "spec.py"
    text = spec_path.read_text(encoding="utf-8")
    assert "duckdb" not in text
    assert "execute" not in text
    tree = ast.parse(text)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    allowed = {"date", "datetime"}
    bad = [
        n.func.id
        for n in calls
        if isinstance(n.func, ast.Name) and n.func.id not in allowed
    ]
    assert not bad, f"data/spec.py performs work at import time: {sorted(set(bad))}"


def test_gateway_exposes_exactly_one_query_entrypoint():
    """Guard against a convenience helper quietly becoming a second path."""
    tree = ast.parse(GATEWAY.read_text(encoding="utf-8"))
    public = [
        n.name
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
    ]
    assert "guarded_query" in public
    # connect/close/audit_trail are lifecycle and read-only helpers, not query paths
    assert set(public) <= {
        "connect",
        "close",
        "guarded_query",     # the metric read path
        "audit_trail",       # read-only, the audit log
        "schema_changes",    # read-only, semantic metadata for preprocess
        "documents",         # read-only, the Stage 5 evidence corpus
    }, f"unexpected public functions in gateway: {public}"


def test_audit_writer_cannot_open_a_connection():
    """audit.py may execute SQL, but only on a connection handed to it."""
    text = AUDIT.read_text(encoding="utf-8")
    assert "duckdb.connect" not in text
    assert "import duckdb" not in text


def test_audit_writer_only_touches_the_audit_log():
    """Constrain the second executor so it cannot become a general query path."""
    text = AUDIT.read_text(encoding="utf-8").lower()
    for table in ("fact_orders", "fact_sessions", "crm_notes", "support_tickets"):
        assert table not in text, f"audit.py references {table}"


# ==========================================================================
# Stage 12 audit — the audit trail must correlate to a run
# ==========================================================================
def test_the_audit_run_id_is_per_context_not_a_module_global():
    """Stage 12 finding: one id covered the whole process.

    The previous implementation set a module-level `_CURRENT_RUN_ID` lazily on
    first use and never reset it. Measured before the fix: two graph runs
    produced 21 audit rows under a single id, and that id matched neither run
    — the column existed but correlated nothing.

    A ContextVar also fixes a concurrency problem the global had: Streamlit
    serves each session on its own thread, so two analysts running at once
    would have interleaved under whichever id was written last.
    """
    from contextvars import ContextVar

    from security import audit

    assert not hasattr(audit, "_CURRENT_RUN_ID"), (
        "the module-level global is back; it cannot isolate threads"
    )
    assert isinstance(audit._RUN_ID, ContextVar)
    assert hasattr(audit, "set_run_id")


def test_two_threads_do_not_share_an_audit_run_id():
    """The concurrency half of the finding, exercised rather than argued."""
    import threading

    from security import audit

    seen = {}

    def worker(name):
        audit.set_run_id(f"RUN-{name}")
        seen[name] = audit.current_run_id()

    threads = [threading.Thread(target=worker, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert seen == {"a": "RUN-a", "b": "RUN-b"}, (
        f"threads bled into each other's run id: {seen}"
    )


def test_gateway_reads_are_attributed_to_the_graph_run_id(tmp_path):
    """End to end: an audit row must join to the run the user is shown."""
    from datetime import date, datetime

    from graph.build import compile_graph
    from graph.run import InsightRequest, run_insight
    from retrieval.embeddings import load_index
    from semantic import gateway
    from semantic.types import Window

    started = datetime.now()
    result = run_insight(
        InsightRequest(
            persona_id="meera", kpi_id="net_revenue",
            window=Window(start=date(2026, 1, 1), end=date(2026, 8, 17)),
            slice_filter={"channel": ["Marketplace"]},
            cause_date=date(2026, 6, 14), scenario_id="S7",
        ),
        graph=compile_graph(in_memory=True), index=load_index(),
        history_days=229,
    )

    con = gateway.connect()
    ids = {r[0] for r in con.execute(
        "SELECT DISTINCT run_id FROM audit_log WHERE ts >= ?",
        [started]).fetchall()}

    assert ids, "the run wrote no audit rows at all"
    assert ids == {result.run_id}, (
        f"audit rows carry {ids}, but the run the user sees is "
        f"{result.run_id!r} — the trail cannot be joined to the run"
    )
