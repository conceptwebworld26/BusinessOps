---
name: bops-anomaly-detection
description: Use when interpreting a computed anomaly scan — which periods deviated from their own historical baseline, in revenue, cost, gross profit, margin, order volume or customer activity, how far, against which baseline, and which parts of the data sit under the deviation. Reads the BusinessOps anomaly scan; it never reads spreadsheets, computes deviations, explains a cause, or concludes that anything is fraud. Trigger phrases include "anything unusual", "what stands out", "unexpected drop", "spike in costs", "which month looks odd".
---

# Anomaly Detection

Turn a computed anomaly scan into a short list of places worth looking — and stop precisely
where the evidence stops.

## What this skill does and does not do

| Does | Does not |
|---|---|
| Report which periods deviated and against which baseline | Recompute a deviation or set a threshold |
| State the observed value, the baseline and the size of the gap | Assert why the gap exists |
| Name the parts of the data underneath the deviation | Treat attribution as explanation |
| Separate "unusual" from "material anomaly" | Present every flag as equally important |
| Say when a scan found nothing | Manufacture a finding to fill the section |
| Say an anomaly may warrant investigation | Say or imply fraud, theft, or wrongdoing |

**You never calculate.** Every figure comes from `lib/python/bops/anomaly/`. If a period is
not in the scan, it was not flagged, and inventing one is a defect.

## The fraud boundary — non-negotiable

An anomaly is a number that differs from a baseline. It is **not** evidence of fraud,
manipulation, theft, or misconduct, and M8 contains no capability that could establish any
of those. The engine lists the forbidden vocabulary in `anomaly.FRAUD_LANGUAGE` and the
tests assert that no emitted statement contains it.

The strongest permitted framing is the engine's own:

> This is a deviation from the historical baseline and may warrant investigation. It does
> not establish a cause, and it is not evidence of fraud or of any wrongdoing.

If a user asks whether a figure indicates fraud, say that the analysis cannot answer that,
describe what was actually observed, and stop.

## Inputs

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import pipeline
result = pipeline.run('<path>')
scan = pipeline.detect_anomalies(result)
print(scan.status, len(scan.observations), len(scan.flagged()), len(scan.limitations))
"
```

The returned `AnomalySet` carries `observations` (every checked period, not only the
flagged ones), `scanned_metrics`, `sensitivity`, and per observation: `baseline`,
`deviation`, `deviation_pct`, `score`, `threshold`, `status`, `materiality`, `method` and
`contributors`.

## Method

**1. Say what was scanned before what was found.** `scanned_metrics` shows which metrics ran
and which were unavailable. A scan of six metrics that flags nothing is a real, reassuring
result; report it as one.

**2. Always state the baseline.** "Revenue was 29% below baseline" is unreadable without
"the baseline being what the trailing trend, corrected for the model's own recent error,
led you to expect". A deviation without its baseline is an assertion.

**3. Rank by materiality, not by score.** A `material_anomaly` cleared both the detector
threshold and the user's configured materiality policy. A merely `unusual` period cleared
only the first, and belongs lower or in a list.

The score is in **multiples of the detector's typical prediction error** — a ratio of two
measured quantities. It is not a sigma, carries no probability and implies no significance
level; the engine fits no distribution and tests none. Never translate a score into odds.

**4. Use attribution carefully.** Contributors say *where* in the data the deviation sits —
which product, region or customer moved with it. That is a pointer for investigation, never
a cause. "Chilled Logistics accounts for 84% of the movement" is fair; "Chilled Logistics
caused the spike" is not.

**5. Never explain.** No "because", no "driven by demand", no "customers preferred". The
engine lists these patterns in `anomaly.CAUSAL_LANGUAGE`. Describe the movement and let the
user, who knows what happened that month, supply the reason.

**6. Respect the privacy labels.** Where a contributor is pseudonymised, keep the
pseudonym. Never reconstruct an identity, and never present an individual transaction.

**7. Carry the caveats.** A flat baseline scored on percentage change, a margin scored in
points rather than currency, contributors measured in revenue for a metric that is not —
the engine attaches these; do not drop them. Where a contributor carries no `share_pct`,
the units did not match and no share may be invented for it.

**8. Label every statement** `[FACT]`, `[CALCULATION]`, `[INTERPRETATION]` or
`[ASSUMPTION]`. The deviation is a calculation. "Worth investigating" is an interpretation.

## Output

Order: what was scanned and at what sensitivity · anomalies ranked by materiality, each with
observed value, baseline and deviation · where the deviation sits · **the investigation
note** · what could not be scanned and why · quality caveats · confidence.

## Failure conditions

| Condition | Behaviour |
|---|---|
| Quality gate halted the run | Report the halt. Produce no anomaly findings |
| Fewer periods than the baseline minimum (default 6 prior) | State that no baseline can be established; scan nothing |
| A metric's column is unmapped | Report that metric as unavailable and name the field |
| Constant series | Report that no period deviates; do not force a flag |
| Zero or near-zero baseline | Report the absolute movement; state that percentage deviation is undefined |
| Nothing flagged | Say so plainly. This is a result, not an empty section |
| Asked whether an anomaly is fraud | Decline. State that the analysis observes deviation only, and repeat what was observed |
| Asked why a period moved | State that the scan locates deviations and does not establish cause |

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md`, `${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md` (including *Data privacy in output*).
