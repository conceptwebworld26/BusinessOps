# 2026-09-08 — Milestone 1: Foundation

**Milestone:** 1 — Foundation
**Status on completion:** `REVIEW` — awaiting Milestone 1 review
**Supersedes:** None. Follows
[2026-09-08-architecture-review-corrections.md](2026-09-08-architecture-review-corrections.md).

## 1. Prompt / task performed

Architecture Revision 2 approved. Implement **Milestone 1 — Foundation only**: plugin and
marketplace manifests, core project documentation, `.gitignore`, configuration foundation
and precedence resolver, the first-class Business Context component, the six `reference/`
policy documents, the runtime/dependency foundation for the four-tier Excel reader, the
testing foundation, and the first always-on token measurement. Explicitly **not** Milestone 2
or later: no full Excel reader, no KPI engine, no forecasting, no anomaly detection, no
analytics skills, no external research, no synthesis skills, no production commands, no MCP
connector layer, no deployment, no push.

## 2. Objective

Build and verify the infrastructure Milestone 2's vertical slice will stand on, treating the
approved Revision 2 architecture as binding.

## 3. Changes made

### Manifests

`.claude-plugin/plugin.json` relies on auto-discovery for commands, skills, MCP and hooks;
omits `agents` entirely (no agents until M11 — and a directory path there is rejected by the
validator per ADR-0001); declares `experimental.evals`. `.claude-plugin/marketplace.json`
points at the repo root so the repository installs directly from GitHub.

**Validator finding.** `claude plugin validate .claude-plugin/plugin.json --strict` fails on
a single advisory: *"CLAUDE.md at the plugin root is not loaded as project context."* The
JSON report confirms the manifest itself has **zero errors and zero warnings** — the warning
attaches to `CLAUDE.md`, not the manifest.

This was assessed as **not an architectural conflict**. The repository is deliberately both
the plugin and its own development project; `CLAUDE.md` is development governance
(`CLAUDE.md` section 11 ownership table) and was never intended to ship as plugin context.
Deleting or relocating approved governance to silence a cosmetic advisory would be the wrong
trade, so `CLAUDE.md` is retained and the advisory documented in `architecture.md` section 2
and registered as R-08. `claude plugin validate .` resolves to the marketplace manifest and
passes `--strict` cleanly.

### `.gitignore`

Rewritten to cover secrets, `.businessiq/`, `businessiq-output/`, Python, Node, editor and
OS artifacts, and test/eval **output** only.

**Bug found and fixed during implementation.** The first draft used trailing comments
(`.businessiq/    # confidential`). Git treats the whole line as the pattern, so those
exclusions would silently not have matched — precisely the failure that would have leaked
confidential Business Context into version control. Rewritten with comments on their own
lines, every pattern verified with `git check-ignore`, and a regression test
(`test_gitignore_has_no_trailing_comments`) added so it cannot recur.

### Configuration

`config/businessiq.defaults.json` carries the approved defaults verbatim. `biq/config.py`
implements the precedence chain **command argument → project business context → user
business context → shipped defaults**, recording *which layer supplied each value* — needed
so BusinessIQ can tell a user a threshold came from their project context rather than a
default, and so the evidence ledger can cite it. Only the configuration-bearing parts of a
Business Context participate; identity fields cannot leak into config.

### Business Context (ADR-0011)

`lib/schemas/business_context.schema.json` covers identity, reporting and analysis, with
every field optional and an `x-privacy` annotation per field. `config/vocabulary.json`
supplies the controlled vocabulary: 10 business models (each with KPI relevance hints), 16
industries, 7 size bands, plus format and taxonomy vocabularies.

`biq/context/loader.py` provides validation (structural + vocabulary, all problems reported
at once), file loading, three-layer precedence with project-local winning, explicit
`MissingField` markers, `require()` raising `MissingContextError` naming the specific absent
fields, `relevance_filtering_enabled()`, and `detect_contradictions()`.

`biq/context/privacy.py` reads classification **from the schema** rather than duplicating it,
so the rule has one home. Unannotated fields default to `internal`, never `public`.

`biq/jsonschema_mini.py` is a stdlib JSON Schema subset validator — pulling in `jsonschema`
would have breached the stdlib-first rule for a config-validation convenience. It reports
`unsupported_keywords()` so a schema cannot quietly lose enforcement, and a test asserts the
Business Context schema uses only enforced keywords.

### Reference documents

Six documents, 431 lines. Each opens with what it **owns**, who **consults** it, and what it
**does not own** with links — the mechanism that keeps rules single-homed under ADR-0012.

### Runtime foundation (ADR-0008)

`biq/runtime/tiers.py` resolves the highest available tier. Two invariants are enforced by
construction: `resolve()` is pure inspection and **never installs**; `bootstrap()` raises
`ConsentRequiredError` unless `consent is True`. `allow_bootstrap: "always"` is deliberately
**not** supported, because ADR-0010 makes approval per-action and non-transferable — a config
value cannot pre-authorise an install. `consent_request()` returns the full disclosure
(package, location, scope, network, undo, consequence of declining). The resolved tier is a
serialisable record with `degraded` and `quality_warning()`.

`bootstrap_possible()` deliberately does **not** test network reachability — that would make
an external request during what the caller believes is local inspection.

### Testing

`tests/run_tests.py` discovers `unit/`, `integration/` and `negative/`, supports verbose and
single-module runs. 120 tests across four modules.

## 4. Files created

```
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
README.md
LICENSE
CONNECTORS.md
config/businessiq.defaults.json
config/vocabulary.json
lib/schemas/business_context.schema.json
lib/python/biq/__init__.py
lib/python/biq/errors.py
lib/python/biq/jsonschema_mini.py
lib/python/biq/config.py
lib/python/biq/context/__init__.py
lib/python/biq/context/loader.py
lib/python/biq/context/privacy.py
lib/python/biq/runtime/__init__.py
lib/python/biq/runtime/tiers.py
reference/analysis-framework.md
reference/evidence-ledger.md
reference/materiality-policy.md
reference/output-standards.md
reference/ambiguity-protocol.md
reference/research-policy.md
tests/run_tests.py
tests/unit/__init__.py
tests/unit/test_manifest.py
tests/unit/test_config.py
tests/unit/test_business_context.py
tests/unit/test_runtime_tiers.py
tests/unit/test_jsonschema_mini.py
docs/development/2026-09-08-foundation.md   (this file)
```

## 5. Files modified

| File | Change |
|---|---|
| `.gitignore` | Rewritten (was 8 generic lines) |
| `architecture.md` | Status banner → Revision 2 approved / M1 implemented; two implementation clarifications added (validator advisory, measured token figure). **No architectural change** |
| `project_plan.md` | M0 → `COMPLETED`; M1 task table with evidence → `REVIEW`; R-04 updated; R-08 added |
| `docs/README.md`, `docs/development/README.md` | Index entries |

**No ADR body was modified.**

## 6. Files deleted

None in the repository. Outside it, a temporary measurement probe was copied to
`~/.claude/skills/businessiq-m1-probe`, measured, and removed (verified: only the user's
pre-existing skills remain). Transient `__pycache__` directories and an unused empty
`tests/fixtures/` were cleaned up.

## 7. Features implemented

| Feature | Location | Reachable |
|---|---|---|
| Plugin + marketplace manifests | `.claude-plugin/` | Yes — plugin installs |
| Config precedence with per-key provenance | `biq/config.py` | Engine API |
| Business Context validation + vocabulary | `biq/context/loader.py` | Engine API |
| Explicit missing-context representation | `MissingField`, `require()` | Engine API |
| Context/data contradiction detection | `detect_contradictions()` | Engine API |
| Privacy classification + Tier 0 subset | `biq/context/privacy.py` | Engine API |
| Reader tier resolution + recording | `biq/runtime/tiers.py` | Engine API |
| Consent-gated bootstrap | `bootstrap()` | Engine API |
| Stdlib JSON Schema validator | `biq/jsonschema_mini.py` | Engine API |
| Six policy references | `reference/` | Read on demand |
| Test harness | `tests/run_tests.py` | `python tests/run_tests.py` |

**No user-facing slash command exists yet** — commands are M7 onward.

## 8. Tests performed

```
python tests/run_tests.py
python tests/run_tests.py unit.test_runtime_tiers
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/plugin.json --json
claude plugin validate .claude-plugin/marketplace.json --strict
claude plugin validate . --strict
git check-ignore -q <9 representative paths>
claude plugin details businessiq-m1-probe        (temporary, removed)
PYTHONPATH=lib/python python <behaviour demonstration>
```

## 9. Test results

```
BusinessIQ test suite
  python : 3.13.1
Ran 120 tests in 0.042s
OK
ran 120 | failures 0 | errors 0 | skipped 0
```

Per module: manifest/layout 12 · config 21 · business context 41 · runtime tiers 29 ·
jsonschema 17.

**Two failures occurred during development and were fixed:**

1. `test_no_secrets_in_defaults` — false positive: the scan matched the word "secrets" in the
   file's own `$comment` ("never put secrets here"). Fixed by stripping `$`-prefixed
   annotations before scanning, so the test checks real keys and values.
2. `test_governance_documents_exist` — genuine: `README.md` did not exist yet. Fixed by
   writing it.

Validation:

| Command | Result |
|---|---|
| `validate .claude-plugin/plugin.json` | ✔ Passed with warnings — manifest itself 0 errors / 0 warnings |
| `validate .claude-plugin/plugin.json --strict` | ✘ Fails on the CLAUDE.md advisory alone (R-08) |
| `validate .claude-plugin/marketplace.json --strict` | ✔ Passed |
| `validate . --strict` | ✔ Passed (resolves to the marketplace manifest) |
| `git check-ignore` × 9 | ✔ Confidential ignored; source/tests/docs/config tracked |

## 10. Issues discovered

| ID | Issue | Resolution |
|---|---|---|
| — | `.gitignore` trailing comments would have silently broken the confidential-path exclusions | **Fixed**, verified, regression test added |
| — | Secret-scan test false positive on its own documentation comment | **Fixed** |
| R-08 | `--strict` warns that root `CLAUDE.md` is not shipped plugin context | **Accepted** — by design; documented |

## 11. Decisions made

No new ADRs. Every decision followed approved architecture. Three implementation choices are
worth recording, all within approved scope:

1. **Stdlib JSON Schema validator instead of `jsonschema`** — adding a dependency for config
   validation would breach `CLAUDE.md` section 4, which permits exactly one managed
   dependency (the Tier-2 reader).
2. **`allow_bootstrap: "always"` deliberately unsupported** — ADR-0010 makes approval
   per-action and non-transferable, so no config value may pre-authorise an install.
3. **Privacy classes read from the schema**, not duplicated in code — ADR-0012's
   one-home-per-rule requirement.

## 12. Architecture changes

**None.** Two clarifications added to `architecture.md` (the validator advisory; the measured
token figure). No layer, component, tier, boundary or gate changed.

## 13. Project-plan updates

M0 → `COMPLETED` (Revision 2 approved). M1 → `REVIEW` with a per-task evidence table.
`.mcp.json` recorded as deferred to M12 with reason. R-04 updated to note the Tier-3 warning
path is now wired; R-08 registered.

## 14. Documentation updates

`README.md`, `CONNECTORS.md`, `LICENSE` created; six `reference/` documents created;
`architecture.md`, `project_plan.md`, `docs/README.md`, `docs/development/README.md` updated;
this record created. Historical records untouched; no ADR body modified.

## 15. Remaining work

Milestones 2–14. Next, subject to review: **Milestone 2 — Vertical Slice**, which needs a
synthetic demo dataset, minimal ingestion at Tiers 1 and 3, minimal semantic mapping, four
quality check families, five KPIs including one `not_applicable`, one analysis skill, one
command, and end-to-end provenance with both a passing and a deliberately-broken-data test.

## 16. Git commit reference

Branch `main`. **No commit made** — `CLAUDE.md` section 10 requires commits only on request.
Nothing pushed, no history rewritten. All Milestone 1 files are uncommitted in the working
tree alongside the Milestone 0 governance files.
