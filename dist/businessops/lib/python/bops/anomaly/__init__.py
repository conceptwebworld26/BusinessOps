"""Anomaly detection: finding periods that do not look like the ones before them.

Four modules:

    contract.py    what an anomaly is - status, baseline, contributor, the fraud boundary
    baselines.py   three ways of computing "normal", all trailing-only
    detectors.py   the detector registry, each with its adequacy predicate and threshold
    engine.py      the seven-stage scan over a pipeline result

The layer consumes the canonical dataset, semantic map, quality grade and materiality
policy that Milestones 3-6 produce, and returns an `AnomalySet` - an `AnalysisSet`
subclass, so evidence, materiality and presentation apply unchanged.

An anomaly is a measurement, never an accusation: see `contract.FRAUD_LANGUAGE` and
`contract.INVESTIGATION_NOTE`, which the tests assert against every emitted statement.
"""

from .baselines import mad, mean, median, stdev                      # noqa: F401
from .contract import (                                              # noqa: F401
    ABOVE, AVAILABLE, BELOW, CAUSAL_LANGUAGE, FLAGGED, FRAUD_LANGUAGE,
    INSUFFICIENT_DATA, INVESTIGATION_NOTE, MATERIAL_ANOMALY, NORMAL, NOT_APPLICABLE,
    STATUSES, UNAVAILABLE, UNUSUAL, AnomalyError, AnomalySet, Baseline, Contributor,
    Observation,
)
from .detectors import (                                             # noqa: F401
    DETECTOR_IDS, DETECTORS, HIGH, LOW, MEDIUM, SENSITIVITIES, THRESHOLDS, Detector,
    catalogue, resolve_sensitivity,
)
from .engine import (                                                # noqa: F401
    DEFAULT_WINDOW, METRIC_IDS, METRICS, Metric, run, scan_series,
)

__all__ = [
    "NORMAL", "UNUSUAL", "MATERIAL_ANOMALY", "INSUFFICIENT_DATA", "STATUSES", "FLAGGED",
    "AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE", "ABOVE", "BELOW",
    "FRAUD_LANGUAGE", "CAUSAL_LANGUAGE", "INVESTIGATION_NOTE",
    "Baseline", "Contributor", "Observation", "AnomalySet", "AnomalyError",
    "DETECTORS", "DETECTOR_IDS", "Detector", "THRESHOLDS", "SENSITIVITIES",
    "LOW", "MEDIUM", "HIGH", "resolve_sensitivity", "catalogue",
    "median", "mean", "mad", "stdev",
    "METRICS", "METRIC_IDS", "Metric", "run", "scan_series", "DEFAULT_WINDOW",
]
