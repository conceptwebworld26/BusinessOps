# Reference — Evidence Ledger

**Owns:** the seven provenance classes, confidence levels, citation and traceability rules.
**Consulted by:** every skill that emits a claim; every command before producing output.
**Does not own:** how sources are tiered or retrieved
([research-policy](research-policy.md)), how claims are rendered
([output-standards](output-standards.md)).

---

## The seven provenance classes

Every assertion in every output carries **exactly one** class.

| # | Class | Means | Must be presented with |
|---|---|---|---|
| 1 | User-provided data | Read from a file the user supplied | source file, sheet, **reader tier** |
| 2 | Connected-system data | Pulled from an MCP-connected system | system name, pull timestamp |
| 3 | External sourced | Retrieved from public research | source, publication date, source tier |
| 4 | Calculated metric | Computed by the engine from 1 or 2 | formula and the inputs used |
| 5 | Analytical interpretation | Claude's reading of 1–4 | explicit framing as interpretation |
| 6 | Estimate / assumption | Modelled or assumed | flagged, and entered in the assumption register |
| 7 | Recommendation | A proposed action (the claim's statement) | evidence, rationale, expected benefit, risks, dependencies, confidence — **all six**; see *Recommendations* below |

## The two rules that matter most

**1 — Evidential and generative material must look different.**
Classes 1–4 are evidential; 5–7 are generative. A reader must be able to tell at a glance
which is which. Never blend a measured figure and an inference into one sentence in one
voice.

**2 — Every major conclusion traces to at least one class 1–4 entry.**
A conclusion resting only on classes 5–7 is an opinion. Either find the evidence, or
present it explicitly as an opinion with low confidence.

## Confidence

| Level | When |
|---|---|
| `HIGH` | Multiple tier A/B sources agree, or a class-4 calculation on `PASS`-quality data |
| `MEDIUM` | A single adequate source, or a calculation on `WARNING`-quality data |
| `LOW` | Thin, dated, conflicting, or heavily assumption-dependent |

Confidence is **stated**, never implied by tone. Confident prose over `LOW`-confidence
evidence is a defect.

## Citations cannot be fabricated

Citations are captured **at retrieval time** and carried through as data. A citation that
was never captured does not exist and cannot be emitted. Where no adequate source exists,
the answer is *"no reliable source found for this"* — never a plausible-looking reference.

## Disclosure entries

Every external query records what left the machine: the disclosure tier, the exact
transmitted text, and the approval if one was given. This makes the privacy boundary
auditable after the fact. See [research-policy](research-policy.md).

## Recommendations (class 7)

Decided in ADR-0031 and enforced by the strategy engine from M10.3.2; the canonical field
names are `action`, `evidence`, `rationale`,
`expected_benefit`, `risks`, `dependencies`, `confidence`, with no aliases.

- **Evidence is identifiers, not prose.** `evidence` lists synthesis statement ids that resolve
  in one genuine strict synthesis set. At least one must be class 1, 3 or 4, or an
  interpretation whose verified chain reaches one. Statements graded `unsupported` or
  `insufficient_evidence` are not evidence.
- **Assumptions supplement, never justify.** A class-6 assumption appears only as a dependency,
  never as evidence. A recommendation never rests on another recommendation.
- **Confidence is derived, never supplied** — the weakest confidence of the cited statements and
  assumptions, with their reasons pooled. A conflict, an assumption or unavailable provenance
  therefore makes a recommendation `LOW`.
- **Figures are quoted, never produced.** A figure in a recommendation must already appear in a
  cited statement.
- **No priority, rank or score.** Several recommendations may be issued; their order is not a
  ranking.
- Recommendations live beside the synthesis set, never inside it, and are never executed by
  BusinessOps.

## Data-quality caveats travel with the claim

A figure computed from `WARNING`-grade data carries that caveat wherever it appears —
including into a summary. Caveats are not dropped during summarisation.

## The class list is closed

Seven classes, deliberately. An open list drifts into a taxonomy nobody applies
consistently. Adding one requires an ADR (architecture.md section 18).
