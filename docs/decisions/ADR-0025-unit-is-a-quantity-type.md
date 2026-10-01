# ADR-0025 — `unit` is a quantity type; scale is normalised into the value, never carried as a label

**Date:** 2026-09-15
**Status:** Accepted
**Deciders:** Owner, via the M10.2-R.1 scoped decision milestone

## Context

The M10.2-R live verification (2026-09-15) put a real internal analysis and real external
research into one synthesis set and ran the seven-dimension compatibility test across the
internal/external boundary. Every pair rejected. The run surfaced a property of the `unit`
dimension that had never been exercised before, because M10.1 and M10.2 only ever compared
external figures with external figures.

Tracing the implementation establishes the following, by inspection rather than inference:

* **Internally, `unit` is a semantic quantity type.** `lib/python/biq/kpi/contract.py`
  defines five tokens — `CURRENCY = "currency"`, `PERCENT`, `RATIO`, `COUNT`, `DAYS` — and
  `lib/python/biq/kpi/engine.py` reads them as types: `MONETARY_UNITS = ("currency",)`
  gates currency safety and currency attachment. Magnitude lives in the `Decimal` value.
  The currency code lives in a **separate** field, `result.currency`. Display formatting
  lives further away still, in `render.executive.money()`.
* **Externally, `unit` is unvalidated caller text.** `synthesis.contract.SynthesisItem`
  stores `unit` as a plain attribute; nothing in `lib/python/biq/synthesis/` validates it
  against any vocabulary. A skill reading a market-size source writes what the source
  wrote — in the live run, `"USD billion"`.
* **`compatibility.compare()` tests the dimension by exact string equality**, after
  case-folding and whitespace collapse in `_normalise()`. It converts nothing;
  `NEVER_CONVERTS = True` is asserted in the module.
* **The internal vocabulary is not actually closed.** `analytics.contract.Finding.unit` has
  no vocabulary constant, and `percentage_points` is a bare string literal in
  `analytics/domain.py`, `analytics/financial.py` and `materiality.py` — a sixth token that
  the KPI contract's list does not contain.
* **No FX mechanism exists anywhere in the engine.** A grep for exchange rates, conversion
  functions or rate tables returns nothing, and `kpi/engine.py` refuses monetary metrics
  outright when the dataset carries mixed currencies.

Observed live: internal revenue carried `unit: "currency"`, `currency: "GBP"`; an external
market size carried `unit: "USD billion"`, `currency: "USD"`. The dimension rejected.

## Problem

The same field means two different things on either side of the internal/external boundary
— a quantity type internally, a magnitude-qualified display label externally. Does the
architecture reconcile them, and if so, is doing that a prohibited conversion?

## Options considered

### Option A — Keep strict unit-token equality, change nothing
**Pros:** zero work, zero risk, `compare()` stays the audit surface it is.
**Cons:** leaves a field whose meaning depends on which side wrote it. Two sides can match
textually while meaning different things, which is worse than failing to match.

### Option B — Decompose `unit` into quantity + currency + scale as a structured type
**Pros:** explicit and complete.
**Cons:** `currency` is *already* a separate dimension, so the structure would carry it
twice and create a way for the two copies to disagree. Adds a type where a vocabulary
suffices.

### Option C — Allow `compare()` to normalise scale before testing equality
**Pros:** makes `USD million` and `USD billion` match.
**Cons:** fatal. `compare()` is the module that promises to convert nothing, and it is the
surface an auditor reads to see *why* two values stayed apart. Normalising inside it means a
mismatch can be massaged away at exactly the point designed to report mismatches.

### Option D — `unit` is a quantity type everywhere; scale is normalised into the value at statement construction
Strict token equality in `compare()` is kept **unchanged**. A magnitude-qualified label
never becomes a `unit` value in the first place, because the skill that reads a source
records the quantity type in `unit`, the currency code in `currency`, and the value scaled
to base units — while keeping the source's own wording verbatim in the evidence content.

## Decision

**Option D.**

1. **`unit` denotes a quantity type and nothing else.** Its value is drawn from one closed
   vocabulary shared by both domains. `currency`, `percent`, `ratio`, `count`, `days` and
   `percentage_points` are the tokens the engine already emits; a future implementation
   milestone homes them in one place and makes them the only accepted values.
2. **Scale is a property of the value, never of the unit.** A source reporting
   "USD 282.80 billion" yields `unit: currency`, `currency: USD`,
   `observed: Decimal("282800000000")`. `"USD billion"` ceases to exist as a unit value.
3. **Scale normalisation happens at statement construction, in the skill that reads the
   source — never inside `compatibility.compare()`.** That module is unchanged by this ADR.
4. **Scale normalisation is not conversion.** See *Reason*.
5. **Currency conversion remains prohibited**, with no approval path, exactly as before.
6. **An out-of-vocabulary unit is `None`, not a token to match.** Two unrecognised labels
   must never satisfy the dimension by agreeing with each other.
7. **Display formatting stays in `render`** and never enters a dimension.

Answering the specific questions this milestone posed:

| Question | Answer |
|---|---|
| Canonical representation | quantity type in `unit`, currency code in `currency`, magnitude in the `Decimal` value, formatting in `render` |
| What is compatibility | all seven dimensions stated and equal, `unit` compared as a quantity type |
| What is conversion | any operation needing data the set does not hold — an exchange rate above all |
| Scale normalisation allowed | yes, at statement construction, decimal-exact, outside `compare()` |
| Currency conversion allowed | no, and no approval unlocks it |
| Unknown unit | `unknown` → REJECT |
| Unknown currency | `unknown` → REJECT |
| Do display units matter | no; they are never a dimension |
| `currency` vs `USD billion` | the question dissolves — `USD billion` is not a unit value |
| `USD million` vs `USD billion` | both are `currency`; the dimension matches and the values are already in base units |
| GBP vs USD | never match |
| revenue vs market size | never match — they differ on `metric_definition` and on `scope` |
| Must methodology stay a separate dimension | yes; nothing else catches "measured" vs "estimated" |

## Reason

**Scale normalisation and currency conversion are categorically different operations, and
the live run showed why the difference matters.**

`USD 3.4 billion` and `USD 3,400,000,000` are the same quantity written two ways. Relating
them needs no external data, no rate, no reference date and no judgement; the operation is
exact in `Decimal`, and it is reversible. `GBP 3.4 billion` and `USD 3.4 billion` are
different quantities. Relating them needs an exchange rate, which BusinessIQ does not hold,
which varies with time, which forces a judgement nobody has made (spot, average or closing?),
and which is lossy. The first is a change of notation; the second is a change of meaning.
Permitting the first while prohibiting the second is a principled line, not a softening.

**Keeping a magnitude in the unit token is not merely untidy — it is unsafe.** If both sides
carry `unit: "USD billion"`, strict equality passes, and nothing then checks whether each
side's value is actually expressed in billions. A statement holding `3400000000` under a
label saying *billion* would compare as compatible with one holding `282.8`, and the engine
would have certified a comparison wrong by a factor of 10⁹. Strict token equality is only
safe when the token carries no magnitude. That is the argument for this decision, and it is
an argument *from* strictness rather than against it.

**Option C was rejected on the same ground that makes the module trustworthy.**
`compatibility.compare()` reports which dimension failed and why; that report is the audit
artefact. A module that silently reconciles inputs before testing them cannot also be the
record of what did not reconcile.

**Unit was never the whole obstacle, and this ADR does not pretend otherwise.** In the live
run, internal revenue against external market size failed on `metric_definition`, `period`,
`geography`, `currency`, `unit` and `scope` simultaneously. Fixing `unit` would have moved
that pair from six failures to five. A company's revenue is not a market's size, and it
must not become comparable to one. The legitimate internal↔external monetary comparison is
like-for-like — our revenue against a source's statement of *our* revenue, or our gross
margin against a benchmark computed on the same definition — and for those, `unit` is a real
obstacle that this decision removes.

## Consequences

**Positive**
* One meaning for one field, on both sides of the boundary.
* The 10⁹ failure mode described above becomes unconstructible.
* `compatibility.py` needs no change, so the strictest module in the layer stays untouched
  and its 2,950-test regression surface is undisturbed.
* The ALLOW branch becomes reachable in principle for like-for-like monetary pairs.

**Negative**
* A closed vocabulary means a source stating a unit outside it yields `unknown` and rejects.
  Some legitimate comparisons will fail for want of a vocabulary entry. That is the correct
  direction to fail, and it is a real cost.
* Normalisation sits in the skills, which is model-mediated judgement rather than engine
  determinism. The mitigation is that the source's verbatim wording stays in the evidence
  content, so a normalisation is always auditable against what the source actually said.
* Existing skills that write magnitude-qualified units must be revised before any of this
  takes effect. Until then, behaviour is exactly as it is today.

**Follow-up required**
* An implementation milestone to home the unit vocabulary in one module, validate `unit` at
  `SynthesisItem` construction, and revise the four research skills to normalise scale.
  This ADR implements none of it.
* `analytics` currently emits `percentage_points` with no vocabulary constant; that is the
  first thing the implementation milestone has to reconcile.
* A future live verification needs a like-for-like fixture — not revenue against market
  size — before the ALLOW branch can be claimed reachable across domains in practice.

## Revisit when

An authorised FX mechanism is proposed with a stated rate source, a stated reference date
and a disclosure position — at which point the prohibition in point 5, not the unit model,
is what is being reopened. Also revisit if a quantity type arises that genuinely cannot be
expressed in a closed vocabulary.
