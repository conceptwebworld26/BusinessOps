"""The quality-check contract: one shape every family conforms to.

A check is not just a boolean. To be useful downstream — and auditable afterwards — every
finding must say what was checked, why, what was found, how severe it is, which fields it
touches, what evidence supports it, which threshold applied and where that threshold came
from, whether it blocks analysis, and what the user should do about it.

Two vocabularies, deliberately distinct:

  * a **finding** carries `INFO` / `WARNING` / `CRITICAL`
  * the **report** carries `PASS` / `WARNING` / `CRITICAL`, the highest finding severity
    present (INFO-only being a PASS)

They describe different things — one observation, one verdict — so both are kept.

Two rules hold across every family:

  * checks **observe**; they never repair, rewrite, fill, convert or delete anything;
  * a check run over a sampled or streamed dataset says so, and never presents a partial
    pass as exhaustive.
"""

from .. import privacy as privacy_mod

INFO = "INFO"
WARNING = "WARNING"
CRITICAL = "CRITICAL"

PASS = "PASS"

SEVERITY_RANK = {INFO: 0, WARNING: 1, CRITICAL: 2}
_GRADE = {0: PASS, 1: WARNING, 2: CRITICAL}

# How completely a check could run, given the processing mode.
EXHAUSTIVE = "exhaustive"
PARTIAL = "partial"
NOT_RUN = "not_run"


class CheckSpec:
    """The declaration of one quality family: identity and policy, separate from execution."""

    __slots__ = ("check_id", "title", "purpose", "detects", "severity_policy",
                 "can_halt", "thresholds", "requires_roles")

    def __init__(self, check_id, title, purpose, detects, severity_policy,
                 can_halt, thresholds=(), requires_roles=()):
        self.check_id = check_id
        self.title = title
        self.purpose = purpose
        self.detects = detects
        self.severity_policy = severity_policy
        self.can_halt = can_halt
        self.thresholds = tuple(thresholds)
        self.requires_roles = tuple(requires_roles)

    def as_dict(self):
        return {"check_id": self.check_id, "title": self.title, "purpose": self.purpose,
                "detects": self.detects, "severity_policy": self.severity_policy,
                "can_halt": self.can_halt, "thresholds": list(self.thresholds)}

    def __repr__(self):
        return "CheckSpec(%s)" % self.check_id


class Finding:
    """One quality observation.

    The positional signature is the one M2 established, so existing callers keep working;
    everything M4 adds is keyword-only with a safe default.
    """

    __slots__ = ("family", "code", "severity", "message", "detail", "affected",
                 "check_id", "fields", "evidence", "threshold", "observed",
                 "remediation", "halts", "completeness")

    def __init__(self, family, code, severity, message, detail=None, affected=0,
                 check_id=None, fields=(), evidence=None, threshold=None,
                 observed=None, remediation=None, halts=None,
                 completeness=EXHAUSTIVE):
        self.family = family
        self.code = code
        self.severity = severity
        self.message = message
        self.detail = detail
        self.affected = affected
        self.check_id = check_id or family
        self.fields = list(fields)
        self.evidence = dict(evidence or {})
        self.threshold = dict(threshold or {})
        self.observed = observed
        self.remediation = remediation
        self.halts = (severity == CRITICAL) if halts is None else halts
        self.completeness = completeness

    def as_dict(self):
        record = {"family": self.family, "code": self.code, "severity": self.severity,
                  "message": self.message, "detail": self.detail,
                  "affected": self.affected, "check_id": self.check_id,
                  "fields": self.fields, "halts": self.halts,
                  "completeness": self.completeness}
        if self.evidence:
            record["evidence"] = self.evidence
        if self.threshold:
            record["threshold"] = self.threshold
        if self.observed is not None:
            record["observed"] = self.observed
        if self.remediation:
            record["remediation"] = self.remediation
        return record

    def __repr__(self):
        return "Finding(%s/%s %s)" % (self.family, self.code, self.severity)


class CheckResult:
    """What one family produced, including the case where it could not run."""

    __slots__ = ("spec", "findings", "completeness", "skipped_reason", "examined")

    def __init__(self, spec, findings=(), completeness=EXHAUSTIVE,
                 skipped_reason=None, examined=None):
        self.spec = spec
        self.findings = list(findings)
        self.completeness = completeness
        self.skipped_reason = skipped_reason
        self.examined = examined

    @property
    def check_id(self):
        return self.spec.check_id

    @property
    def passed(self):
        return not any(f.severity != INFO for f in self.findings)

    @property
    def grade(self):
        if not self.findings:
            return PASS
        return _GRADE[max(SEVERITY_RANK[f.severity] for f in self.findings)]

    def as_dict(self):
        return {"check_id": self.check_id, "title": self.spec.title,
                "grade": self.grade, "completeness": self.completeness,
                "skipped_reason": self.skipped_reason, "examined": self.examined,
                "can_halt": self.spec.can_halt,
                "findings": [f.as_dict() for f in self.findings]}

    def __repr__(self):
        return "CheckResult(%s: %s, %d findings)" % (
            self.check_id, self.grade, len(self.findings))


# ---------------------------------------------------------------------------
# Privacy-safe evidence
# ---------------------------------------------------------------------------

def safe_examples(values, sensitivity_map=None, column=None, limit=3):
    """Examples that are safe to put in a report.

    Quality reporting must not become a privacy leak, so a column classified above
    `derived_safe` never contributes literal values — the report gets a count and a type
    instead. This never weakens the M3 classification; it only reads it.
    """
    if sensitivity_map is not None and column is not None:
        sensitivity = sensitivity_map.sensitivity_of(column)
        if privacy_mod.rank(sensitivity) > privacy_mod.rank(privacy_mod.DERIVED_SAFE):
            return {"redacted": True, "sensitivity": sensitivity,
                    "note": "values withheld because the field is classified %r"
                            % sensitivity}
    sample = []
    for value in values:
        if value in (None, ""):
            continue
        text = str(value)
        sample.append(text if len(text) <= 40 else text[:37] + "...")
        if len(sample) >= limit:
            break
    return {"redacted": False, "examples": sample}


def redact_label(value, sensitivity_map=None, column=None):
    """A single label, redacted if the field is sensitive."""
    if sensitivity_map is not None and column is not None:
        sensitivity = sensitivity_map.sensitivity_of(column)
        if privacy_mod.rank(sensitivity) > privacy_mod.rank(privacy_mod.DERIVED_SAFE):
            return "<redacted: %s>" % sensitivity
    return str(value)


# ---------------------------------------------------------------------------
# Threshold resolution with provenance
# ---------------------------------------------------------------------------

def threshold(config, key, default):
    """Resolve a configured threshold and record where it came from.

    The report must distinguish the configured threshold from the observed value, and say
    which layer supplied it, so a user can re-run with a different setting and understand
    why the answer changed.
    """
    value = config.get(key, default) if config is not None else default
    source = config.source_of(key) if config is not None else None
    return value, {"key": key, "value": value, "source": source or "built-in default"}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REGISTRY = []


def register(spec, function):
    """Register one family. Adding a family is registration, not core surgery."""
    REGISTRY.append((spec, function))
    return function


def specs():
    return [spec for spec, _fn in REGISTRY]


def spec_for(check_id):
    for spec, _fn in REGISTRY:
        if spec.check_id == check_id:
            return spec
    return None
