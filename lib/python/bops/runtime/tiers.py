"""Reader tier resolution and the consented bootstrap (ADR-0008).

Four tiers, highest available wins:

    1  openpyxl already importable in the running interpreter      no install
    2  openpyxl in the managed venv at ~/.claude/businessops/runtime/  consented install
    3  stdlib parser                                                no install
    4  guided CSV export                                            no Python needed

Two invariants this module exists to guarantee:

  - **Resolution never installs anything.** `resolve()` is pure inspection. Installing is
    `bootstrap()`, which raises ConsentRequiredError unless consent is explicitly granted.
    There is no configuration value that pre-authorises it: ADR-0010 makes approval
    per-action and non-transferable, so "always" is deliberately not an accepted setting.
  - **The chosen tier is recorded**, so every dataset can carry how it was read and the
    quality gate can warn when a degraded tier was used.

The readers themselves are Milestone 2/3 work. This module resolves and records only.
"""

import json
import os
import subprocess
import sys

from ..errors import ConsentRequiredError, RuntimeUnavailableError

# Pinned by ADR-0008. Verified resolvable during the architecture review.
OPENPYXL_PIN = "openpyxl==3.1.5"
OPENPYXL_PACKAGE = "openpyxl"
OPENPYXL_VERSION = "3.1.5"

RUNTIME_DIR = os.path.join(os.path.expanduser("~"), ".claude", "businessops", "runtime")
STATE_FILENAME = "runtime_state.json"

TIER_OPENPYXL_SYSTEM = 1
TIER_OPENPYXL_MANAGED = 2
TIER_STDLIB = 3
TIER_CSV_FALLBACK = 4

TIER_NAMES = {
    TIER_OPENPYXL_SYSTEM: "openpyxl (system interpreter)",
    TIER_OPENPYXL_MANAGED: "openpyxl (managed runtime)",
    TIER_STDLIB: "stdlib xlsx parser",
    TIER_CSV_FALLBACK: "guided CSV export",
}

# Tiers below this are degraded: usable, but the quality report must say so.
FULL_FIDELITY_MAX_TIER = TIER_OPENPYXL_MANAGED


class ReaderTier:
    """The resolved tier, with enough provenance to record on a dataset."""

    __slots__ = ("tier", "name", "reason", "interpreter", "degraded", "bootstrap_available")

    def __init__(self, tier, reason, interpreter=None, bootstrap_available=False):
        self.tier = tier
        self.name = TIER_NAMES[tier]
        self.reason = reason
        self.interpreter = interpreter
        self.degraded = tier > FULL_FIDELITY_MAX_TIER
        self.bootstrap_available = bootstrap_available

    def as_dict(self):
        """Serialisable record, attached to every dataset from Milestone 2 onward."""
        return {
            "tier": self.tier,
            "name": self.name,
            "reason": self.reason,
            "interpreter": self.interpreter,
            "degraded": self.degraded,
            "bootstrap_available": self.bootstrap_available,
        }

    def quality_warning(self):
        """The warning the quality gate raises for a degraded tier, or None."""
        if self.tier == TIER_STDLIB:
            return ("Workbook read with the stdlib parser (Tier 3). Built-in number "
                    "formats are not yet resolved, so some date and percentage columns "
                    "may be reported as plain numbers. Unsupported constructs are "
                    "refused rather than guessed.")
        if self.tier == TIER_CSV_FALLBACK:
            return ("No usable Python runtime was found (Tier 4). Excel cannot be read "
                    "directly; export the sheet to CSV and supply that instead.")
        return None

    def __repr__(self):
        return "ReaderTier(%d, %r)" % (self.tier, self.name)


# --------------------------------------------------------------------------
# Inspection — never mutates anything
# --------------------------------------------------------------------------

def _openpyxl_importable():
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        return False


def managed_python():
    """Path to the managed venv interpreter, or None if the venv is absent."""
    candidates = (
        os.path.join(RUNTIME_DIR, "Scripts", "python.exe"),   # Windows
        os.path.join(RUNTIME_DIR, "bin", "python3"),          # POSIX
        os.path.join(RUNTIME_DIR, "bin", "python"),
    )
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def managed_has_openpyxl(interpreter=None):
    """True if the managed runtime exists and can import openpyxl."""
    interpreter = interpreter or managed_python()
    if not interpreter:
        return False
    try:
        result = subprocess.run(
            [interpreter, "-c", "import openpyxl; print(openpyxl.__version__)"],
            capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def bootstrap_possible():
    """Whether a Tier 2 bootstrap could succeed: pip and venv must both be available.

    Deliberately does not test network reachability — that would mean a request to an
    external host during what the caller believes is a local inspection.
    """
    try:
        import ensurepip, venv  # noqa: F401
    except ImportError:
        return False
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def resolve(allow_bootstrap="ask", prefer=None, _probe=None):
    """Resolve the highest available tier. **Never installs anything.**

    `prefer` pins a tier for testing or for a user who wants a specific reader.
    `_probe` injects inspection results in tests, so the suite stays deterministic and
    offline.
    """
    probe = _probe or {}
    system_ok = probe.get("system_openpyxl", _openpyxl_importable())
    managed_interp = probe.get("managed_python", managed_python())
    managed_ok = probe.get("managed_openpyxl")
    if managed_ok is None:
        managed_ok = managed_has_openpyxl(managed_interp) if managed_interp else False
    can_bootstrap = probe.get("bootstrap_possible")
    if can_bootstrap is None:
        can_bootstrap = bootstrap_possible()
    stdlib_ok = probe.get("stdlib_available", True)

    if prefer is not None:
        available = {
            TIER_OPENPYXL_SYSTEM: system_ok,
            TIER_OPENPYXL_MANAGED: managed_ok,
            TIER_STDLIB: stdlib_ok,
            TIER_CSV_FALLBACK: True,
        }
        if not available.get(prefer):
            raise RuntimeUnavailableError(
                "preferred tier %s is not available" % prefer, attempted=[prefer])
        return ReaderTier(prefer, "explicitly requested", bootstrap_available=can_bootstrap)

    if system_ok:
        return ReaderTier(TIER_OPENPYXL_SYSTEM,
                          "openpyxl is importable in the current interpreter",
                          interpreter=sys.executable)
    if managed_ok:
        return ReaderTier(TIER_OPENPYXL_MANAGED,
                          "openpyxl is available in the managed runtime",
                          interpreter=managed_interp)
    if stdlib_ok:
        reason = "openpyxl is not installed; using the stdlib parser"
        if can_bootstrap and allow_bootstrap != "never":
            reason += " (a consented Tier 2 bootstrap could upgrade this)"
        return ReaderTier(TIER_STDLIB, reason, interpreter=sys.executable,
                          bootstrap_available=bool(can_bootstrap) and allow_bootstrap != "never")

    return ReaderTier(TIER_CSV_FALLBACK, "no usable Python reader is available")


# --------------------------------------------------------------------------
# Bootstrap — the only function here that changes anything
# --------------------------------------------------------------------------

def consent_request(allow_bootstrap="ask"):
    """Exactly what the user is being asked to approve.

    ADR-0010 requires an approval request to name what changes and where, so this returns
    the full disclosure rather than a yes/no prompt string.
    """
    if allow_bootstrap == "never":
        return None
    return {
        "action": "install the Excel reader dependency",
        "package": OPENPYXL_PIN,
        "location": RUNTIME_DIR,
        "scope": "an isolated virtual environment used only by BusinessOps",
        "touches_system_python": False,
        "touches_repository": False,
        "network": "downloads from PyPI",
        "if_declined": ("BusinessOps continues with the Tier 3 stdlib reader, which handles "
                        "most workbooks but may report some date and percentage columns as "
                        "plain numbers."),
        "reversible": "delete %s" % RUNTIME_DIR,
    }


def bootstrap(consent=False, allow_bootstrap="ask", runtime_dir=None, _runner=None):
    """Create the managed runtime and install the pinned reader.

    Raises ConsentRequiredError unless `consent is True`. There is no configuration value
    that grants consent in advance — approval is per-action (ADR-0010).
    """
    if allow_bootstrap == "never":
        raise ConsentRequiredError(
            "install the Excel reader dependency",
            detail="Configuration sets runtime.allow_bootstrap to 'never'. "
                   "BusinessOps will continue with the Tier 3 stdlib reader.",
            reversible=True)

    if consent is not True:
        request = consent_request(allow_bootstrap)
        detail = "\n".join([
            "  package:  %s" % request["package"],
            "  location: %s" % request["location"],
            "  scope:    %s" % request["scope"],
            "  network:  %s" % request["network"],
            "  undo:     %s" % request["reversible"],
            "  if declined: %s" % request["if_declined"],
        ])
        raise ConsentRequiredError("install the Excel reader dependency", detail=detail)

    target = runtime_dir or RUNTIME_DIR
    runner = _runner or _default_runner

    os.makedirs(os.path.dirname(target), exist_ok=True)
    runner([sys.executable, "-m", "venv", target])

    interpreter = None
    for candidate in (os.path.join(target, "Scripts", "python.exe"),
                      os.path.join(target, "bin", "python3"),
                      os.path.join(target, "bin", "python")):
        if os.path.exists(candidate):
            interpreter = candidate
            break
    if interpreter is None:
        raise RuntimeUnavailableError("managed runtime was created but no interpreter was found")

    runner([interpreter, "-m", "pip", "install", "--disable-pip-version-check", OPENPYXL_PIN])

    tier = ReaderTier(TIER_OPENPYXL_MANAGED,
                      "installed %s into the managed runtime with user consent" % OPENPYXL_PIN,
                      interpreter=interpreter)
    write_state(tier, target)
    return tier


def _default_runner(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeUnavailableError(
            "command failed: %s\n%s" % (" ".join(argv), result.stderr.strip()))
    return result


# --------------------------------------------------------------------------
# State — recorded outside the repository
# --------------------------------------------------------------------------

def state_path(runtime_dir=None):
    return os.path.join(runtime_dir or RUNTIME_DIR, STATE_FILENAME)


def write_state(tier, runtime_dir=None):
    path = state_path(runtime_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = dict(tier.as_dict(), pin=OPENPYXL_PIN)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path


def read_state(runtime_dir=None):
    path = state_path(runtime_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
