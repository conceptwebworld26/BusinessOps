"""The M12-B connector layer (ADR-0037, clarified by ADR-0038).

Four modules, each one concern, importing downward only:

    contract    the closed vocabularies: capability placeholders, interaction classes, the 19
                failure codes, result statuses and every fixed sentence a result may carry
    registry    the fixed connector registry and deterministic capability resolution
    binding     the Connector Gate record form and the declaration / measurement / grant
                agreement check, reading BusinessOps's own repository files only
    catalogue   one value-free discovery operation: evaluation order, the sealed consumed-once
                brief, the fail-closed `BOPS-CAT/1` reply parser and the catalogue result

**What this package is not.** It is not an MCP client, a proxy or a dispatcher: Python can
neither see nor call an MCP tool (ADR-0015), and nothing here tries. It reads no record, writes
to no connected system, authenticates nothing, holds no credential and reads no platform or
user configuration. It produces no evidence and no synthesis input. Connected-system record
reads are M12-C, `BLOCKED` (ADR-0037 section M), and every request for one is refused.

**Nothing in the file workflow imports this package.** Every connector is optional (ADR-0038
section 1): the Data Layer, the engines, the commands and synthesis run identically whether the
registry is empty, a connector is registered, or an operation failed.
"""
