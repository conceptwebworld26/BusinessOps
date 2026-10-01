"""Holdout backtesting: testing a method on history it was not allowed to see.

A forecast that has never been tested is not thereby wrong, but it is differently
trustworthy. The only honest way to say how wrong a method tends to be is to hide the tail
of the history, forecast it, and compare - which is what this module does.

Two uses, and they are separate on purpose:

  * **selection** - every adequate method is backtested, and the one with the lowest error
    is chosen. Selection is therefore evidence-driven rather than a hardcoded preference,
    and it is deterministic: ties break on the declared priority order in `methods.py`.
  * **reporting** - the winning method's error becomes the uncertainty band, so the width
    of the band is a measured property of this dataset rather than a convention.

The error metric is MAPE (mean absolute percentage error), with MAE alongside it because
MAPE is undefined against a zero actual and misleading against a near-zero one. Periods
whose actual is zero are excluded from MAPE and counted, so a series that is mostly zeros
cannot produce a flatteringly small error.
"""

from decimal import Decimal

from . import contract, methods as methods_mod

ZERO = Decimal("0")

#: Never hold back more than this share of the history - a backtest that trains on a
#: quarter of the data measures the shortage of training data, not the method.
MAX_HOLDOUT_SHARE = Decimal("0.34")

#: Below this, holding anything back leaves too little to train on to mean anything.
MIN_FOR_VALIDATION = 6


def holdout_size(periods, horizon, minimum=2):
    """How many periods to hold back: the horizon, capped by what history can spare."""
    if periods < MIN_FOR_VALIDATION:
        return 0
    ceiling = int(Decimal(periods) * MAX_HOLDOUT_SHARE)
    size = min(horizon, ceiling)
    return size if size >= minimum else 0


def _errors(actual, predicted):
    """(mae, mape, skipped_zero_actuals) for two aligned value lists."""
    absolute, percentage, skipped = [], [], 0
    for a, f in zip(actual, predicted):
        difference = a - f
        if difference < ZERO:
            difference = -difference
        absolute.append(difference)
        if a == ZERO:
            skipped += 1
            continue
        magnitude = a if a > ZERO else -a
        percentage.append(difference / magnitude * Decimal("100"))
    mae = sum(absolute, ZERO) / Decimal(len(absolute)) if absolute else None
    mape = (sum(percentage, ZERO) / Decimal(len(percentage))) if percentage else None
    return mae, mape, skipped


def score(history, method, holdout):
    """Backtest one method. Returns a dict, or None if it cannot be trained on the split."""
    series = history.series
    train, test = series[:-holdout], series[-holdout:]
    if not method.adequate_for(train):
        return None
    predicted = method.project(train, len(test))
    mae, mape, skipped = _errors([v for _p, v in test], predicted)
    return {"method": method.method_id, "mae": mae, "mape": mape,
            "zero_actual_periods": skipped, "priority": method.priority,
            "training_periods": len(train), "validation_periods": len(test)}


def select(history, horizon, preferred=None):
    """Choose the method and produce its `Validation` record.

    Returns `(method, validation, candidates)`. When no backtest is possible the choice
    falls back to the most capable adequate method by declared priority, and the validation
    record says plainly that nothing was tested.
    """
    adequate = methods_mod.adequate(history.series)
    if not adequate:
        return None, contract.Validation(
            contract.INSUFFICIENT_DATA,
            reason="No forecast method's minimum history requirement is met."), []

    if preferred is not None:
        chosen = methods_mod.get(preferred)
        if not chosen.adequate_for(history.series):
            return None, contract.Validation(
                contract.INSUFFICIENT_DATA,
                reason=("The requested method %r needs %d periods; %d are available."
                        % (preferred, chosen.min_periods, history.periods))), []
        adequate = [chosen]

    holdout = holdout_size(history.periods, horizon)
    if not holdout:
        chosen = adequate[-1] if preferred is None else adequate[0]
        return chosen, contract.Validation(
            contract.INSUFFICIENT_DATA, method=chosen.method_id,
            reason=("%d periods of history is too short to hold any back for a backtest "
                    "while leaving enough to train on (at least %d periods are needed); "
                    "the forecast is unvalidated."
                    % (history.periods, MIN_FOR_VALIDATION))), []

    scored = [s for s in (score(history, m, holdout) for m in adequate) if s]
    if not scored:
        chosen = adequate[-1]
        return chosen, contract.Validation(
            contract.INSUFFICIENT_DATA, method=chosen.method_id,
            reason=("No method could be trained on the %d periods left after holding "
                    "back %d for validation." % (history.periods - holdout, holdout))), []

    #: Ranking key. A method with no MAPE (every actual was zero) falls back to MAE, and
    #: priority breaks exact ties so two runs never disagree.
    def rank(entry):
        mape = entry["mape"]
        return (0 if mape is not None else 1,
                mape if mape is not None else entry["mae"] or ZERO,
                -entry["priority"])

    scored.sort(key=rank)
    best = scored[0]
    chosen = methods_mod.get(best["method"])
    train_span = "%s..%s" % (history.labels[0], history.labels[-holdout - 1])
    test_span = "%s..%s" % (history.labels[-holdout], history.labels[-1])

    validation = contract.Validation(
        contract.AVAILABLE, method=chosen.method_id,
        training_period=train_span, validation_period=test_span,
        training_periods=best["training_periods"],
        validation_periods=best["validation_periods"],
        mape=best["mape"], mae=best["mae"],
        candidates=[{"method": s["method"],
                     "mape": s["mape"], "mae": s["mae"]} for s in scored])
    return chosen, validation, scored
