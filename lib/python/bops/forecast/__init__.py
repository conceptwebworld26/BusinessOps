"""Forecasting: deterministic estimates about periods that have not happened yet.

Five modules, split by the question each answers:

    contract.py   what an estimate is - class 6, scenarios, assumptions, uncertainty
    series.py     what history exists, at what frequency, with what gaps
    methods.py    the method registry, each with its adequacy predicate
    validate.py   holdout backtesting, used to both select and characterise a method
    variance.py   forecast versus actual, once the actuals arrive
    engine.py     the nine-stage orchestration over a pipeline result

The layer consumes the canonical dataset, semantic map, quality grade and KPI contracts
that Milestones 3-5 produce, and returns a `ForecastSet` - an `AnalysisSet` subclass, so
Milestone 6's materiality, evidence and presentation machinery applies unchanged.

Nothing here reads a file, calls a network, or uses randomness.
"""

from .contract import (                                              # noqa: F401
    AVAILABLE, BASE, DOWNSIDE, EMPIRICAL_ERROR, FORBIDDEN_CERTAINTY,
    HISTORICAL_VOLATILITY, INSUFFICIENT_DATA, NOT_APPLICABLE, NO_BAND, SCENARIOS,
    STATUSES, UNAVAILABLE, UPSIDE, Assumption, AssumptionRegister, ForecastError,
    ForecastPoint, ForecastResult, ForecastSet, Scenario, UncertaintyBand, Validation,
)
from .engine import (                                                # noqa: F401
    MAX_HORIZON, TARGETS, TARGET_IDS, Target, compare_actuals, forecast_series,
    resolve_horizon, run,
)
from .methods import METHOD_IDS, METHODS, Method, adequate, catalogue  # noqa: F401
from .series import History, prepare                                 # noqa: F401
from .validate import select                                         # noqa: F401
from . import variance                                               # noqa: F401

__all__ = [
    "AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE", "INSUFFICIENT_DATA", "STATUSES",
    "BASE", "UPSIDE", "DOWNSIDE", "SCENARIOS", "FORBIDDEN_CERTAINTY",
    "EMPIRICAL_ERROR", "HISTORICAL_VOLATILITY", "NO_BAND",
    "Assumption", "AssumptionRegister", "UncertaintyBand", "ForecastPoint", "Scenario",
    "Validation", "ForecastResult", "ForecastSet", "ForecastError",
    "METHODS", "METHOD_IDS", "Method", "adequate", "catalogue",
    "History", "prepare", "select", "variance",
    "TARGETS", "TARGET_IDS", "Target", "MAX_HORIZON",
    "run", "forecast_series", "resolve_horizon", "compare_actuals",
]
