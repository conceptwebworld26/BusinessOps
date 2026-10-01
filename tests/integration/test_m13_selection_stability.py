"""M13.1 forecast method-selection stability - ADR-0039 section D.3 (M13-MEAS-D3, R-10).

A deterministic **leave-one-period-out** measurement over the demo revenue series
(`assets/demo-data/northwind_sales.csv`, 24 monthly periods). It uses the production path
unchanged:

- `pipeline.run` builds the dataset and semantic map;
- `forecast.series.prepare` builds the revenue history exactly as the forecast engine does for
  its `revenue` target;
- `forecast.engine.resolve_horizon` gives each window the production default horizon;
- `forecast.validate.select` chooses the method.

Windows: the full series, then each truncation that removes one more trailing period, while
the window still meets the configured minimum history (`forecast.min_history_periods`). The
literal leave-one-out comparison is the full series against the series minus its final
period; the remaining windows extend it back to the minimum.

Recorded per window: periods, last period, horizon, selected method, and every candidate's
backtest error. Summarised: the number of distinct selections and the number of adjacent
windows whose selection differs.

**Recorded, never a threshold.** The only assertion is determinism: the same input gives the
same selection. No method, priority, holdout or configuration is changed, and no stability
figure is a pass or fail (ADR-0039 D.3, D.5).
"""

import atexit
import json
import os
import unittest

from bops import mapping as mapping_mod
from bops import pipeline
from bops.forecast import engine as forecast_engine
from bops.forecast import series as series_mod
from bops.forecast import validate

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_CONTEXT = os.path.join(REPO, "assets", "demo-data", "business_context.json")

_RESULT = []


def _demo_run():
    if not _RESULT:
        with open(DEMO_CONTEXT, encoding="utf-8") as handle:
            context = json.load(handle)
        _RESULT.append(pipeline.run(DEMO, context_overrides=context, load_context_files=False))
    return _RESULT[0]


def _window(history, keep):
    return series_mod.History(
        history.metric, history.series[:keep], frequency=history.frequency,
        regular=history.regular, gaps=history.gaps, trimmed=history.trimmed,
        original_periods=history.original_periods, notes=history.notes,
        partial_final=history.partial_final)


def _text(value):
    return None if value is None else str(value)


def measure():
    """The D.3 measurement as a JSON-ready dict."""
    result = _demo_run()
    config = result.config
    history, reason = series_mod.prepare(result.dataset, result.semantic_map,
                                         mapping_mod.REVENUE, "Revenue")
    if history is None:
        return {"status": "execution_unavailable", "reason": reason}
    minimum = int(config.get("forecast.min_history_periods", 12))

    windows = []
    for keep in range(history.periods, minimum - 1, -1):
        window = _window(history, keep)
        horizon, _note = forecast_engine.resolve_horizon(None, window.periods, config)
        chosen, validation, scored = validate.select(window, horizon)
        windows.append({
            "periods": window.periods,
            "removed_trailing": history.periods - keep,
            "last_period": window.last_period,
            "horizon": horizon,
            "selected": chosen.method_id if chosen else None,
            "validation_status": validation.status,
            "validation_periods": validation.validation_periods,
            "candidates": [{"method": s["method"], "mape": _text(s["mape"]),
                            "mae": _text(s["mae"])} for s in scored],
        })

    selections = [w["selected"] for w in windows]
    changes = sum(1 for a, b in zip(selections, selections[1:]) if a != b)
    return {
        "status": "executed",
        "series": "demo revenue (%s)" % os.path.basename(DEMO),
        "history_periods": history.periods,
        "history_span": history.span,
        "min_history_periods": minimum,
        "windows": windows,
        "distinct_selections": sorted(set(s for s in selections if s)),
        "adjacent_changes": changes,
        "leave_one_out": {"full": selections[0],
                          "minus_final_period": selections[1] if len(selections) > 1
                          else None},
    }


def _print_summary():
    try:
        record = measure()
    except Exception:
        return
    print(os.linesep + "  M13-MEAS-D3 (measurement, not benchmarking; no threshold)")
    if record["status"] != "executed":
        print("  M13-MEAS-D3 %s" % json.dumps(record, sort_keys=True))
        return
    for window in record["windows"]:
        print("  M13-MEAS-D3 window periods=%d last=%s horizon=%s selected=%s"
              % (window["periods"], window["last_period"], window["horizon"],
                 window["selected"]))
    print("  M13-MEAS-D3 distinct=%s adjacent_changes=%d leave_one_out=%s"
          % (json.dumps(record["distinct_selections"]), record["adjacent_changes"],
             json.dumps(record["leave_one_out"], sort_keys=True)))


_REGISTERED = []


class SelectionStabilityMeasurement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not _REGISTERED:
            atexit.register(_print_summary)
            _REGISTERED.append(True)

    def test_the_measurement_executes_on_the_demo_revenue_series(self):
        record = measure()
        self.assertEqual(record["status"], "executed", record.get("reason"))
        self.assertGreaterEqual(len(record["windows"]), 2,
                                "leave-one-out needs at least two windows")

    def test_the_same_input_gives_the_same_selection(self):
        self.assertEqual(json.dumps(measure(), sort_keys=True),
                         json.dumps(measure(), sort_keys=True))

    def test_selection_is_deterministic_per_window(self):
        result = _demo_run()
        history, _reason = series_mod.prepare(result.dataset, result.semantic_map,
                                              mapping_mod.REVENUE, "Revenue")
        for keep in (history.periods, history.periods - 1):
            window = _window(history, keep)
            horizon, _note = forecast_engine.resolve_horizon(None, window.periods,
                                                             result.config)
            first = validate.select(window, horizon)[0]
            second = validate.select(window, horizon)[0]
            with self.subTest(periods=keep):
                self.assertEqual(first.method_id, second.method_id)

    def test_every_window_meets_the_configured_minimum_history(self):
        record = measure()
        for window in record["windows"]:
            self.assertGreaterEqual(window["periods"], record["min_history_periods"])

    def test_windows_remove_exactly_one_more_trailing_period_each(self):
        removed = [w["removed_trailing"] for w in measure()["windows"]]
        self.assertEqual(removed, list(range(len(removed))))
