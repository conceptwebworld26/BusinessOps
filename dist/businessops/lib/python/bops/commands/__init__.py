"""The command layer: thin orchestration over everything Milestones 1-6 built.

A command sequences existing components and formats their output. It owns no formula, no
threshold, no classification and no policy — `architecture.md` section 3 and ADR-0012 put
those in the engine, the reference documents and the skills respectively, and this layer
adds nothing to that list.

Three modules, and the split matters:

    registry.py   which command runs what, declared as data
    runner.py     sequencing: pipeline, then the declared domains, then routing
    query.py      `/ask-business-data` — maps a question onto work that already exists
    sections.py   one view of the structured result, formatted once at presentation

`architecture.md` section 18 lists "an analysis domain — new Layer-2 skill + optional
command" and "an output format — new renderer in the engine" as registration-only
extension points requiring no ADR, which is exactly what this package is.
"""

from .registry import (                                              # noqa: F401
    ANALYSIS, BASIS, BY_ID, COMMAND_IDS, COMMANDS, CommandSpec, DATA_QUALITY,
    DEFAULT_SECTIONS, EVIDENCE, KEY_FINDINGS, KPIS, LIMITATIONS, SECTION_ORDER, STATUS,
    as_dict as catalogue_as_dict, mapping_table, require, spec_for,
)
from .runner import (                                                # noqa: F401
    CLARIFICATION_NEEDED, CommandResult, HALTED, OK, UNAVAILABLE, UNSUPPORTED, run,
    run_all,
)
from .sections import render                                         # noqa: F401
from .joins import (                                                 # noqa: F401
    LocalJoin, internal_result, internal_statements, kpi_statements, local_join,
)
from . import query                                                  # noqa: F401

__all__ = [
    "COMMANDS", "COMMAND_IDS", "BY_ID", "CommandSpec", "spec_for", "require",
    "catalogue_as_dict", "mapping_table", "SECTION_ORDER", "DEFAULT_SECTIONS",
    "STATUS", "BASIS", "KEY_FINDINGS", "KPIS", "ANALYSIS", "LIMITATIONS",
    "DATA_QUALITY", "EVIDENCE",
    "run", "run_all", "CommandResult", "OK", "HALTED", "UNAVAILABLE",
    "CLARIFICATION_NEEDED", "UNSUPPORTED",
    "render", "query",
    # the local join (M10.2-R.14): internal analysis + public benchmark, compared here
    "local_join", "internal_statements", "internal_result", "LocalJoin",
]
