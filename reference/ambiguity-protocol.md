# Reference — Ambiguity Protocol

**Owns:** the never-guess rules, and the exact wording for insufficient data and
clarification.
**Consulted by:** every skill that reads data, maps a column, or answers a question.
**Does not own:** quality grading (the quality skill), thresholds
([materiality-policy](materiality-policy.md)).

---

## The rule

**Never guess.** Where meaning is ambiguous, ask. Where data is absent, say so. A
plausible-looking wrong answer is the worst outcome BusinessOps can produce, because it is
acted upon.

Applies to: columns · transactions · customers · products · accounts · metrics · business
terminology · date and number formats · currency · period boundaries · entity matching.

## Insufficient data — required wording

> **Insufficient data to calculate this metric reliably.**

Then name, specifically:

1. Which metric could not be produced.
2. Which **exact field or period** is missing — not "more data".
3. What would unblock it.
4. What *was* computed, if anything.

Never substitute an estimate for a measurement and never present a partial calculation as
complete.

## Ambiguity — required shape

State what is ambiguous, offer the candidates with confidence, recommend one, and ask.
Never resolve it silently.

> Column `Amount` could be either:
> - **Net revenue** (confidence 0.55) — values align with `Total` on 89% of rows
> - **Gross revenue before discount** (confidence 0.41) — header appears next to `Discount`
>
> Which is it? I have not assumed either.

## Confidence thresholds for automatic mapping

| Confidence | Behaviour |
|---|---|
| ≥ 0.90 | Map automatically; state the mapping in the output |
| 0.60 – 0.89 | Map provisionally, but **confirm before** any figure depends on it |
| < 0.60 | **Ask.** Do not map |

## Missing Business Context is a gap, never a guess

Absent context is represented explicitly (`MissingField`), never inferred. Do not conclude
"this looks like a SaaS business" from column names. Either ask, or proceed with relevance
filtering off and say that it is off.

## Never invent

- A KPI whose inputs are absent → `unavailable`, with the field named.
- A KPI irrelevant to the business model → `not_applicable`, with the reason.
- A formula cell with no cached value → a `WARNING`. **Never compute a replacement.**
- A source that does not exist → *"no reliable source found"*.
- A period with no data → a gap in the series, not an interpolation.

## Ask once, precisely

Batch clarifications into one specific set of questions rather than a stream. Include what
you have already determined, so the user answers only what remains genuinely open.
