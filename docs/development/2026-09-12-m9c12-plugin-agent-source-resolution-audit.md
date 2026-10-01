# 2026-09-12 — M9-C.12: plugin installation and agent source resolution audit

**Milestone:** 9-C.12 — Plugin installation and agent source resolution audit
**Status on completion:** `COMPLETED` — **Outcome A: the working tree is authoritative**
**Supersedes:** None. Corrects the *interpretation* of
`docs/development/2026-09-11-m9c11-fresh-session-agent-registration.md`; that record and
`2026-09-11-m9c10-controlled-scout-handoff-trial.md` remain intact as written.

---

## 1. Purpose

Determine which physical artifact supplies `businessiq:biq-research-scout` when Claude
dispatches the agent: the BusinessIQ working tree, or an installed/cache snapshot.

M9-C.11 surfaced a discrepancy — a working-tree scout definition, a differing installed
cache copy, and runtime install metadata apparently pointing at the cache — while the
working tree continued to be used as the development source. Until that is resolved, no
scout-output experiment can be interpreted: a negative result could mean the protocol
failed, or merely that the edited file was never in the load path.

This milestone is an installation/runtime audit. **No scout was dispatched.** `BIQ-REC/1`
was not tested and no registration marker was attempted.

## 2. The M9-C.11 invalid-marker finding

M9-C.11's probe instructed the scout, for `m9c11-` operations, to emit `BIQ-C11-REGISTERED`
*"on its own line, before your normal output"*. The same file — at lines 65 and 74 of the
marked copy — requires:

> **One bare JSON object and nothing else.** Your entire reply is that object: it starts
> with `{` and ends with `}`.
> … **No prose before the object and none after it**

labelled *"a hard requirement, not a formatting preference"*. The probe's own claim that
*"the return contract … [is] unaffected"* is not satisfiable: a marker line before the
object **is** a return-contract violation, and the envelope has no field to carry it.

Consequently the probe could not produce a positive result even from a correctly loaded
definition. A compliant scout obeying the stronger, repeated bare-JSON rule emits no
marker. **Marker absence from M9-C.11 is not evidence about agent registration and must
not be cited as such.** M9-C.10's 0/8 therefore remained unresolved entering this audit.

A second M9-C.11 check was also vacuous: the marker grep over the subagent transcript
returned 0, but the transcript file
(`…/tasks/a7365f48a42a556f7.output`) is **0 bytes**. Nothing was searched.

## 3. All relevant plugin/agent copies

Every location the runtime could plausibly load from was enumerated. **Exactly two**
physical copies of the plugin exist.

| # | Role | Absolute path | Exists |
|---|---|---|---|
| A | Repository working tree = marketplace source directory | `D:\Prakash\Claude\Plugins\BusinessIQ\BusinessIQ` | Yes |
| B | Installed plugin cache | `C:\Users\Prakash Meghani\.claude\plugins\cache\businessiq\businessiq\0.1.0` | Yes |

Locations checked and found to contain **no** BusinessIQ copy:

- `~\.claude\plugins\marketplaces\` — holds `claude-code-plugins`, `claude-plugins-official`,
  `knowledge-work-plugins` only. A `directory`-source marketplace is not cloned here; its
  `installLocation` *is* the source directory.
- `~\.claude\plugins\.install-manifests\` — no `businessiq@businessiq.json`.
- `~\.claude\plugins\data\` — no businessiq entry.
- `~\.claude\plugins\plugin-catalog-cache.json` — no businessiq key or value (remote
  marketplace catalogue only).
- Project-level `.claude\` — **does not exist** in the repository, so no project agent
  override.
- A recursive search for `biq-research-scout.md` under `~\.claude` returned copy B only.

### Hashes, sizes and times

| Artifact | SHA-256 | Size | mtime |
|---|---|---|---|
| A `agents\biq-research-scout.md` | `04f0b30da8efcf4f4cf2644ee351dfd42d7d7f641c21ee2fc37d6d48b440d244` | 9 845 | 2026-09-12 18:03:56 |
| B `agents\biq-research-scout.md` | `f867a4b1dc5089bd6f257b081d908f3bdb325f9278d0efc2f5e4e68b57210354` | 8 384 | 2026-09-10 22:33:44 |
| A `.claude-plugin\plugin.json` | `8b90e9e6f8958b1c1947f27ee5254d7f6bc00f29f5f74025bf77e0e41cd40d93` | — | — |
| B `.claude-plugin\plugin.json` | `8b90e9e6f8958b1c1947f27ee5254d7f6bc00f29f5f74025bf77e0e41cd40d93` | — | — |

A's mtime of 18:03:56 is this audit's own M9-C.11 restore, verified byte-identical to the
staged pristine copy. The two manifests are **byte-identical**.

### Component inventory divergence

| | A working tree | B cache |
|---|---|---|
| `skills\` | **7** | **6** |
| `commands\` | 10 | 10 |
| `agents\` | 1 | 1 |

`skills\biq-company-analysis\` exists **only in A**. Its `SKILL.md` was created
**2026-09-11 12:44:33** — 13 h 58 m after the cache snapshot.

### Install / source metadata

- `settings.json` → `enabledPlugins["businessiq@businessiq"] = true`;
  `extraKnownMarketplaces.businessiq.source = { source: "directory", path:
  "D:\\Prakash\\Claude\\Plugins\\BusinessIQ\\BusinessIQ" }`.
- `known_marketplaces.json` → businessiq `installLocation` =
  `D:\Prakash\Claude\Plugins\BusinessIQ\BusinessIQ` (the working tree itself).
- `installed_plugins.json` → businessiq `installPath` = copy B, `version` `0.1.0`,
  `scope` `user`, `gitCommitSha` `8d52b0e24343f2e9b9f586207d2ea841dce61289`,
  `installedAt` `2026-09-10T17:16:38.171Z` (= 2026-09-10 22:46:38 IST).

No credentials, tokens or authentication material were read or are reproduced here; only
plugin identity and path keys were extracted from settings.

## 4. Runtime registration metadata

| Question | Finding |
|---|---|
| Plugin installation path | Copy B (cache), per `installed_plugins.json` |
| Marketplace / source path | Copy A (working tree), per `known_marketplaces.json` + `settings.json` |
| Agent definition path exposed? | **No.** No runtime surface reports a per-agent file path |
| Runtime stores a snapshot? | Yes — copy B, created by a single copy event at install |
| Registry points to installed copy or working tree? | **Working tree** — see §5 |
| Is a directory marketplace expected to be live? | Yes. It is referenced in place, not cloned; `installLocation` is the source directory |
| Observable reload mechanism? | `claude plugin update <plugin>` — documented as *"(restart required to apply)"*; `claude plugin marketplace update [name]` |

`claude plugin details businessiq@businessiq` reports `Agents (1) biq-research-scout`,
`Skills (17)`, `Hooks (0)`, `MCP servers (0)`, always-on ~3 100 tok. The 17 skills include
all seven `biq-*` interpretation skills — i.e. the CLI resolves the **A** inventory.

## 5. Runtime registry evidence — which copy is actually used

The decisive evidence is a **positive existence test**, not an inference from filenames.

1. `skills\biq-company-analysis\SKILL.md` exists only in copy A, created 2026-09-11 12:44.
2. Copy B has no such directory and has not been written since 2026-09-10 22:46.
3. This session began **2026-09-12 18:00:15**.
4. This session's model-facing roster **contains `businessiq:biq-company-analysis`**, and
   its description matches copy A's `SKILL.md` frontmatter verbatim (911 characters).

Copy B cannot supply a component it does not contain. Therefore the runtime resolved
BusinessIQ's components from **copy A, the working tree**. The cache is stale and was not
the load path.

Corroboration: `claude plugin details` independently enumerates the A inventory.

### Candidate discriminators examined and rejected

Recorded so they are not mistaken for evidence later:

- **`plugin.json` description appearing shorter in `claude plugin details`** — display
  truncation at ~200 characters. Both manifests hash to `8b90e9e6…`. Not evidence.
- **`retrieval-slice` counted by the CLI (17 skills) but absent from the model roster
  (16)** — explained by `disable-model-invocation: true` in `commands\retrieval-slice.md`.
  The command is present in *both* copies. Not a source divergence.
- **Marker grep over the M9-C.11 subagent transcript** — file is 0 bytes; vacuous.

### Scout-specific limitation

The runtime exposes no per-agent file path, and the scout's frontmatter (`name`,
`description`, `tools`, `model`, `color`) is **byte-identical** across A and B. The scout
alone therefore cannot be discriminated by inspection. That the scout resolves from A is
**inferred** from single-plugin-root resolution: the same plugin root that provably
supplied a working-tree-only skill also supplies the agent. This is strong but not
directly proven — see §11.

## 6. Semantic differences between the two scout definitions

Diff is 30 changed lines, confined to two regions. **Frontmatter is identical** — same
`name`, same `description`, same `tools: WebSearch, WebFetch`, same `model`, same `color`.

| Aspect | A working tree | B cache |
|---|---|---|
| Original M9-B contract | Superseded | **Present** (`"One JSON object and nothing else."`) |
| M9-C.1 / M9-C.7 return-contract hardening | **Present** | Absent |
| Tool grant / permissions | `WebSearch, WebFetch` | **Identical** |
| Description / frontmatter | — | **Identical** |
| `BIQ-REC/1` protocol | Absent (C.10 reverted) | Absent |
| `BIQ-C11` marker | Absent (restored) | Absent |

The A-only additions are the fail-closed output contract: bare object only, no Markdown
fences, no prose before or after, no commentary between records, documented fields only;
the explicit statement that surrounding prose **fails closed and yields no evidence**
(with its rationale — tolerating text around JSON is how a retrieved page's own JSON could
be selected); the "no out-of-band channel" rule directing all remarks into `status` or a
record's `content`; and one added failure-conditions row for wanting a field the envelope
lacks.

So the cache carries the **pre-M9-C.1** contract. No permission, tool-grant, description
or gate difference exists between the copies — the divergence is entirely the output
contract and its rationale.

## 7. Installation / cache behaviour

Every directory in copy B carries mtime `2026-09-10 22:46:37`–`22:46:38`, while individual
files retain their source mtimes (e.g. the scout at `22:33:44`, `architecture.md` at
`2026-09-08 12:38`). That is the signature of a **single recursive copy-with-preserved-mtimes
performed at install** (`installedAt` 22:46:38 IST), not of an incrementally maintained
mirror.

Copy B has not been written since. The working tree changed materially over the following
two days — the M9-C.1 contract hardening, the `biq-company-analysis` skill, M9-C.6/C.7
work — and none of it propagated. **The cache does not auto-refresh, and for this
directory-source plugin it is vestigial:** install bookkeeping that the component loader
does not read.

## 8. Reload semantics

| Mechanism | Status |
|---|---|
| `claude plugin update <plugin>` | Exists. Help states **"(restart required to apply)"** |
| `claude plugin marketplace update [name]` | Exists — refreshes marketplace(s) from source |
| `claude plugin install` / `uninstall` / `enable` / `disable` / `prune` | Exist; not needed and not run |
| Automatic cache refresh on source change | **Not observed** (§7) |
| In-session plugin reload | **None found** in the CLI surface |

Because the marketplace source is a directory read in place, a development edit needs **no
update, reinstall or marketplace refresh to reach the load path** — it is already there.
What it needs is a **session restart**, so the registry re-reads it. The harness's own
*"restart required to apply"* wording is consistent with that.

**Nothing was executed.** No update, reinstall, marketplace refresh, enable/disable or
prune was run; no cache file was patched; the repository's plugin state is untouched.

## 9. Reconciliation with M9-B through M9-C.11

**M9-B's finding stands.** `2026-09-10-m9b-scout-transport-investigation.md` recorded that
agents supplied by an installed plugin appear in the session's registry, and
`2026-09-10-m9b-live-verification-closure.md` confirmed registry presence and the tool
grant. Nothing here contradicts either. This audit **adds** the source half that M9-B did
not establish: registration reads the working tree, not a snapshot.

**M9-C.10 (0/8).** Source divergence is now eliminated as an explanation — the edit was in
the load path all along. What remains is exactly C.10's own stated hypothesis: the
definition is bound when the session registers it, and C.10's edit was made mid-session.
C.10's reasoning was right; its evidence was one explanation short of complete, and it
could not have closed that gap with the information then available.

**M9-C.11.** Two independent defects, and its negative result carries no weight:

- the probe contradicted the bare-JSON contract in the same file (§2), so a loaded
  definition could not have produced a marker; and
- the edit was mid-session regardless — this session started 18:00:15, the marked file was
  applied 18:03:56, the dispatch ran ≈18:05.

**Explicitly identified as based on incomplete evidence:**

- M9-C.11's record states *"a genuinely fresh session cannot be created from inside a
  running one"* and concluded *"M9-C.12 should not run until that check returns a marker."*
  The gate was reasonable but not load-bearing: the source question was answerable by
  **non-invasive inspection with no dispatch at all**, which is how it was resolved.
- M9-C.11's confound list admitted the cache might be authoritative. **That is now
  closed** in favour of the working tree.
- The cumulative "nine dispatches show no response to an edited definition" tally is
  weaker than it reads: every one of those dispatches was mid-session, and eight of the
  nine used an instrument (M9-C.9/C.10 prompt-embedded formats, M9-C.11's pre-envelope
  marker) that the contract independently suppresses.

No prior record was edited or overwritten.

## 10. Outcome

**Outcome A — the working tree is demonstrably authoritative.**

Source-resolution chain:

```
settings.json  enabledPlugins["businessiq@businessiq"] = true
  └─ extraKnownMarketplaces.businessiq = { source: "directory",
                                           path: D:\…\BusinessIQ }
      └─ known_marketplaces.json  installLocation = D:\…\BusinessIQ   ← read in place
          └─ components loaded from the working tree
              ├─ skills\  (7, incl. biq-company-analysis — proves A)
              ├─ commands\ (10)
              └─ agents\biq-research-scout.md   ← dispatched definition
                                                   (inferred, same root)

installed_plugins.json  installPath = …\cache\businessiq\businessiq\0.1.0
  └─ snapshot taken 2026-09-10 22:46:38, never refreshed — NOT the load path
```

Per Outcome A: the agent was **not modified**, the cache was **not patched**, and no
production architecture was changed. Why C.10 and C.11 saw nothing is answered in §9 —
session registration timing is now the **only** surviving explanation, source divergence
having been eliminated.

## 11. Confidence

| Claim | Level |
|---|---|
| Copies A and B are the only physical copies | **Proven** — exhaustive enumeration (§3) |
| Plugin components load from A, the working tree | **Proven** — positive existence test; the session holds a component B lacks (§5) |
| Cache B is stale and not the component load path | **Proven** — B last written 2026-09-10 22:46; §5, §7 |
| No permission / tool-grant / frontmatter divergence between copies | **Proven** — byte-identical frontmatter (§6) |
| The **scout agent specifically** resolves from A | **High confidence, inferred.** No per-agent path is exposed and the scout's frontmatter is identical in both copies; rests on single-plugin-root resolution |
| Registration binds at session start | **Strongly supported, not proven.** Corroborated by *"restart required to apply"*, C.10's 8/8 consistency and C.11's consistency; the runtime exposes no registry snapshot timestamp |
| M9-C.11's marker absence says anything about registration | **Disproven** — invalid instrument (§2) |
| `BIQ-REC/1` viability | **Untested.** Unchanged since M9-C.9's deterministic evidence |

## 12. Recommended next step

**M9-C.13 — fresh-session `BIQ-REC/1` protocol trial.** The working tree is the load path,
so the procedure is a working-tree edit plus an operator-initiated restart; no cache
patching, and no `claude plugin update`.

1. Apply `BIQ-REC/1` to `agents\biq-research-scout.md` in the working tree (the reverted
   M9-C.10 change, 43 additive lines). Stage the pristine copy outside the repo first.
2. **Operator restarts Claude Code.** This cannot be done from inside a session.
3. **Use the protocol itself as the registration check — do not add a marker.** This is
   the correction M9-C.11 needs: `BIQ-REC/1` *is* an observable shape change, so a single
   dispatch answers both questions at once. A reply in `BIQ-REC/1` line format proves the
   edited definition is registered *and* administers the candidate. Any separate probe that
   emits text outside the envelope is suppressed by the contract, as §2 shows.
4. Spend the remaining dispatches only if that first reply shows the new shape; otherwise
   stop — the definition is not registered and the trial is invalid again.
5. Restore the pristine definition and verify by SHA-256 at the end.

No ADR is warranted. This audit recorded a platform property and decided nothing
load-bearing: no contract, permission, gate, provenance or architecture change was made.
