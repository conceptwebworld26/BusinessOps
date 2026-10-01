"""BusinessOps error types.

Two rules from CLAUDE.md shape this module:

  - Fail loudly. Never degrade silently into a plausible-looking wrong answer.
  - Never guess. Ambiguity and absence are reported, not filled in.

So these are distinct types rather than one generic error: a caller must be able to tell
"the data is missing" from "the data is ambiguous" from "you need the user's consent",
because each demands a different response from the command that catches it.
"""


class BusinessOpsError(Exception):
    """Base for every BusinessOps error."""


class ConfigError(BusinessOpsError):
    """Configuration or Business Context could not be loaded or is invalid."""

    def __init__(self, message, errors=None, source=None):
        super().__init__(message)
        self.errors = list(errors or [])
        self.source = source

    def detail(self):
        lines = [str(self)]
        if self.source:
            lines.append("  source: %s" % self.source)
        lines.extend("  - %s" % e for e in self.errors)
        return "\n".join(lines)


class VocabularyError(ConfigError):
    """A value is outside its controlled vocabulary.

    Never resolved by guessing the nearest match — the caller asks the user.
    """


class MissingContextError(BusinessOpsError):
    """Required Business Context is absent.

    Carries the specific missing fields so a command can ask precisely rather than
    asking the user to "set up your context".
    """

    def __init__(self, missing_fields, purpose=None):
        self.missing_fields = list(missing_fields)
        self.purpose = purpose
        detail = ", ".join(self.missing_fields)
        msg = "Insufficient business context: %s" % detail
        if purpose:
            msg += " (needed for: %s)" % purpose
        super().__init__(msg)


class ConsentRequiredError(BusinessOpsError):
    """An action needs explicit user approval that has not been granted.

    Raised instead of performing the action. Per ADR-0010 approval is per-action and
    non-transferable, so this carries exactly what is being asked for.
    """

    def __init__(self, action, detail=None, reversible=True):
        self.action = action
        self.detail = detail
        self.reversible = reversible
        msg = "Explicit user approval required: %s" % action
        if detail:
            msg += "\n%s" % detail
        super().__init__(msg)


class RuntimeUnavailableError(BusinessOpsError):
    """No usable reader tier is available for the requested operation."""

    def __init__(self, message, attempted=None):
        super().__init__(message)
        self.attempted = list(attempted or [])


class WriteBlockedError(BusinessOpsError):
    """A filesystem, process or network effect was stopped before it happened (ADR-0051).

    Raised by the engine's execution guard. It is deliberately not an `OSError`: a caller that
    tolerates ordinary I/O failures must not swallow a refusal and carry on as if the write had
    merely failed.
    """


class WriteApprovalRequired(ConsentRequiredError):
    """A BusinessOps write needs the user's explicit, per-action approval (ADR-0051).

    Carries the approval `code` the user must send and the `operations` it would authorise.
    Nothing has been written when this is raised.
    """

    def __init__(self, action, code=None, operations=None, detail=None):
        self.code = code
        self.operations = list(operations or [])
        super().__init__(action, detail=detail, reversible=True)
