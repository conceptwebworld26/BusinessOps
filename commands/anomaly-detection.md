---
description: Scan a spreadsheet or CSV for periods that deviate from their own historical baseline — revenue, cost, gross profit, gross margin, order volume and customer activity — reporting the observed value, the baseline it was measured against, the size of the deviation, its materiality, and which products, regions or customers sit underneath it. Describes deviations only, and never establishes a cause and never treats an anomaly as fraud. Use when asked whether anything looks unusual, odd or unexpected.
argument-hint: "[path to .xlsx or .csv] [--sensitivity medium] [--shareable]"
---

# /anomaly-detection

Find the periods in one business dataset that do not look like the periods before them.

**This command sequences components. It contains no formula, no threshold and no policy.**
Baselines, deviations and thresholds come from `lib/python/bops/anomaly/`; materiality comes
from the existing policy; privacy comes from the Milestone 3 classification.

## Inputs

| Argument | Meaning | Default |
|---|---|---|
| path | The `.xlsx` or `.csv` to read | required |
| `--sensitivity` | `low`, `medium` or `high` — moves thresholds, never the arithmetic | `anomaly.sensitivity` (medium) |
| `--shareable` | Pseudonymise identifying dimension values in the output | local mode |

## Sequence

1. Run the pipeline (`pipeline.run`). **A `CRITICAL` grade halts here** and nothing is
   scanned — calling a period unusual in a dataset that failed validation would give the
   claim a validity the data does not have.
2. Run `pipeline.detect_anomalies(result)`. Each supported metric becomes a monthly series;
   each period is scored against a trailing baseline by every adequate detector, though
   only a **triggering** detector may raise a flag (a corroborating one is measured and
   reported but cannot flag a period alone); the materiality policy is applied; contributors
   are attributed and passed through the privacy policy.
3. Render with `commands.render`.
4. Hand the `AnomalySet` to **`bops-anomaly-detection`** for interpretation.

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('anomaly-detection', '<path>')
print(commands.render(run))
"
```

## What it reports

Which metrics were scanned and which were unavailable; every flagged period with its
observed value, baseline, deviation, score, detector and status (`unusual` or
`material_anomaly`); and, for flagged periods, the dimension members that moved with the
deviation.

Periods checked and found normal are kept in `observations` — the scan reports its own
coverage, so "nothing found" is distinguishable from "nothing looked at".

## The fraud boundary

An anomaly is a deviation from a baseline. It is never presented as fraud, theft,
manipulation or misconduct, and no approval unlocks that framing — M8 contains no
capability that could establish it. Every flagged finding carries the engine's note that
the deviation may warrant investigation and establishes no cause.

## What it does not do

- Explain why a period moved. Attribution locates a deviation; it does not account for it.
- Forecast (`/revenue-forecast`).
- Expose individual transactions or raw customer records.
- Rank by score alone — materiality decides what leads.
- Use external data of any kind.

## Failure conditions

| Condition | Behaviour |
|---|---|
| Quality `CRITICAL` | Halt; report the reason; scan nothing |
| Quality `WARNING` | Proceed; the caveat travels into every finding |
| No date column | `unavailable`; no period series can be built |
| Fewer than the baseline minimum prior periods (default 6) | `insufficient_data`, with the count and the requirement |
| A metric's column is unmapped | That metric is `unavailable`, naming the field |
| Constant series | No period is flagged; the scan reports that it ran and found nothing |
| Zero baseline | Absolute movement reported; percentage deviation stated as undefined |
| Nothing flagged anywhere | Reported plainly as a result |

Related: `${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`, `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md` (including *Data privacy in output*),
`skills/bops-anomaly-detection/SKILL.md`.
