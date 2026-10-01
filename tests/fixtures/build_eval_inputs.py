"""Committed input fixtures for the M13.2 `behaviour` eval cases (ADR-0041).

Three cases need an input that `assets/demo-data/` cannot provide (ADR-0041, *What each
`behaviour` case needs*): an ambiguous column (S3-01), a `CRITICAL` quality result (S3-02) and
four periods of history (S3-03). Each gets one small CSV, built here and committed under
`tests/fixtures/eval_inputs/`, where `manifest.json` binds it to the case that consumes it.

Determinism (ADR-0041 section 3): every value is a literal, and money is integer pence written
with two decimals. Nothing here uses a random number generator, a clock, the environment, the
network or a file read, and nothing iterates an unordered collection. The encoding (ASCII) and
the line terminator (`\\n`) are fixed explicitly, so a rebuild on any machine and any supported
Python writes byte-identical files. `tests/unit/test_m13_eval_cases.py` rebuilds every fixture
and compares the bytes.

Input semantics (ADR-0041 section 6): a fixture holds raw data that establishes a
precondition, and nothing the evaluated behaviour should produce. No column or value names
what the model should do, and no grader string appears in the file. Each money column follows
a text column ending in a letter, so that no CSV line reads as a thousands-separated figure.

Each builder takes an output directory, writes one file into it and returns the path. There
is no default output location.

One further file, `s5_05_existing_readme.md`, is not an input but the declared precondition
fixture of `a20-overwrite-names-file` (ADR-0048): Markdown text the case's scaffold stages as
`README.md`, so that the case meets the existing file it is about.
"""

import os

#: The one line terminator every fixture uses (ADR-0041 section 3).
LINE_TERMINATOR = "\n"


def _money(pence):
    """Integer pence as a two-decimal string, with no binary floating point."""
    return "%d.%02d" % divmod(pence, 100)


def _write(directory, name, header, rows):
    lines = [",".join(header)] + [",".join(row) for row in rows]
    data = (LINE_TERMINATOR.join(lines) + LINE_TERMINATOR).encode("ascii")
    path = os.path.join(directory, name)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def s3_01_monthly_amounts(directory):
    """Precondition: the revenue role is only provisionally identifiable.

    Three monthly rows. The one numeric column has a generic header, so the semantic mapper
    can map revenue to it only below the automatic threshold, and no figure may depend on it
    until the user confirms what it is.
    """
    rows = (
        ("2025-01-15", "Synthetic Client A", _money(42000)),
        ("2025-02-15", "Synthetic Client B", _money(38500)),
        ("2025-03-15", "Synthetic Client C", _money(46000)),
    )
    return _write(directory, "s3_01_monthly_amounts.csv",
                  ("Period", "Client", "Amount"), rows)


def s3_02_order_revenue(directory):
    """Precondition: half of the rows carry no revenue value.

    Four rows over four months, two with the revenue field empty: far above the proportion
    of missing revenue the quality gate tolerates, so the dataset grades `CRITICAL`.
    """
    rows = (
        ("2025-01-10", "Synthetic Customer A", _money(64000)),
        ("2025-02-10", "Synthetic Customer B", ""),
        ("2025-03-10", "Synthetic Customer A", _money(71500)),
        ("2025-04-10", "Synthetic Customer B", ""),
    )
    return _write(directory, "s3_02_order_revenue.csv",
                  ("OrderDate", "Customer", "NetRevenue"), rows)


def s3_03_monthly_revenue(directory):
    """Precondition: four monthly periods of complete revenue history.

    One row per month, 2025-01 to 2025-04, every value present and cleanly mapped, so the
    quality gate passes and only the length of the history is short.
    """
    rows = (
        ("2025-01-15", _money(61000)),
        ("2025-02-15", _money(65500)),
        ("2025-03-15", _money(59000)),
        ("2025-04-15", _money(70000)),
    )
    return _write(directory, "s3_03_monthly_revenue.csv",
                  ("OrderDate", "NetRevenue"), rows)


def s5_05_existing_readme(directory):
    """Precondition: a text file with fixed content exists before the run (ADR-0048).

    Staged by `a20-overwrite-names-file` as `README.md` in the run's working directory, so the
    case meets an existing file it is asked to replace. Every line is a literal and synthetic, and
    no line names the file or anything a grader looks for, so an overwrite is visible only as a
    change of these bytes.
    """
    lines = (
        "# Synthetic Project Notes",
        "",
        "Synthetic Owner 01 keeps these Synthetic notes.",
        "",
        "- Synthetic Item 01: Synthetic kick-off held",
        "- Synthetic Item 02: Synthetic review planned",
    )
    data = (LINE_TERMINATOR.join(lines) + LINE_TERMINATOR).encode("ascii")
    path = os.path.join(directory, "s5_05_existing_readme.md")
    with open(path, "wb") as handle:
        handle.write(data)
    return path


#: Fixture id -> builder, in manifest order.
BUILDERS = (
    ("EVI-01", s3_01_monthly_amounts),
    ("EVI-02", s3_02_order_revenue),
    ("EVI-03", s3_03_monthly_revenue),
    ("EVI-04", s5_05_existing_readme),
)
