"""Semantic mapping: which column means what, and how sure we are.

The scoring is deterministic and lives here (ADR-0012: computation belongs to the engine).
The *decision* the confidence implies is the ambiguity protocol's, and it is not negotiable:

    >= 0.90   map automatically, state the mapping in the output
    0.60-0.89 map provisionally, CONFIRM before any figure depends on it
    <  0.60   ask; do not map

Names alone are never trusted. Every candidate is scored on the header *and* on what the
column actually contains, so a column called "Amount" full of dates does not become revenue.
"""

import datetime
import re

# Confidence thresholds — see reference/ambiguity-protocol.md.
AUTO_THRESHOLD = 0.90
CONFIRM_THRESHOLD = 0.60

AUTO = "auto"
CONFIRM_REQUIRED = "confirm_required"
UNMAPPED = "unmapped"

DATE = "date"
REVENUE = "revenue"
COST = "cost"
PROFIT = "profit"
CUSTOMER = "customer"
PRODUCT = "product"
REGION = "region"
SALESPERSON = "salesperson"
QUANTITY = "quantity"
UNIT_PRICE = "unit_price"
CATEGORY = "category"
ORDER_ID = "order_id"

# Roles added in M5 for the full KPI catalogue. A dataset without them is not deficient -
# the metrics that need them simply report `unavailable` and name the field.
OPERATING_EXPENSE = "operating_expense"
DEPRECIATION = "depreciation"
INVENTORY_VALUE = "inventory_value"
CASH_BALANCE = "cash_balance"
RECEIVABLES = "receivables"
PAYABLES = "payables"
CURRENT_ASSETS = "current_assets"
CURRENT_LIABILITIES = "current_liabilities"
MARKETING_SPEND = "marketing_spend"
LEAD_COUNT = "lead_count"
DEAL_STAGE = "deal_stage"
PIPELINE_VALUE = "pipeline_value"
DEAL_OPENED = "deal_opened"
DEAL_CLOSED = "deal_closed"
RECURRING_REVENUE = "recurring_revenue"
INVESTMENT = "investment"

ROLES = (DATE, REVENUE, COST, PROFIT, CUSTOMER, PRODUCT, REGION,
         SALESPERSON, QUANTITY, UNIT_PRICE, CATEGORY, ORDER_ID,
         OPERATING_EXPENSE, DEPRECIATION, INVENTORY_VALUE, CASH_BALANCE,
         RECEIVABLES, PAYABLES, CURRENT_ASSETS, CURRENT_LIABILITIES,
         MARKETING_SPEND, LEAD_COUNT, DEAL_STAGE, PIPELINE_VALUE,
         DEAL_OPENED, DEAL_CLOSED, RECURRING_REVENUE, INVESTMENT)

# role -> (strong name patterns, weak name patterns, expected kind)
_PATTERNS = {
    DATE:        ((r"^(order)?_?date$", r"^invoice_?date$", r"^transaction_?date$",
                   r"^period$", r"^month$"),
                  (r"date", r"period", r"month", r"day"), "date"),
    REVENUE:     ((r"^net_?revenue$", r"^revenue$", r"^net_?sales$", r"^sales_?amount$",
                   r"^net_?amount$", r"^turnover$"),
                  (r"revenue", r"sales", r"amount", r"total", r"value"), "number"),
    COST:        ((r"^cost_?of_?goods$", r"^cogs$", r"^direct_?cost$", r"^cost_?of_?sales$",
                   r"^total_?cost$"),
                  (r"cost", r"cogs", r"expense"), "number"),
    PROFIT:      ((r"^gross_?profit$", r"^profit$", r"^margin_?value$"),
                  (r"profit", r"margin"), "number"),
    CUSTOMER:    ((r"^customer$", r"^customer_?name$", r"^client$", r"^account_?name$",
                   r"^buyer$"),
                  (r"customer", r"client", r"account", r"buyer"), "text"),
    PRODUCT:     ((r"^product$", r"^product_?name$", r"^item$", r"^sku$", r"^service$"),
                  (r"product", r"item", r"sku", r"service"), "text"),
    REGION:      ((r"^region$", r"^territory$", r"^area$", r"^country$", r"^market$"),
                  (r"region", r"territory", r"area", r"country", r"market", r"zone"), "text"),
    SALESPERSON: ((r"^salesperson$", r"^sales_?rep$", r"^rep$", r"^account_?manager$",
                   r"^owner$"),
                  (r"sales_?person", r"sales_?rep", r"\brep\b", r"manager"), "text"),
    QUANTITY:    ((r"^quantity$", r"^qty$", r"^units$", r"^volume$"),
                  (r"quantity", r"qty", r"unit", r"volume", r"count"), "number"),
    UNIT_PRICE:  ((r"^unit_?price$", r"^price$", r"^rate$", r"^asp$"),
                  (r"price", r"rate"), "number"),
    CATEGORY:    ((r"^category$", r"^product_?category$", r"^segment$", r"^line$"),
                  (r"category", r"segment", r"class", r"group"), "text"),
    ORDER_ID:    ((r"^order_?id$", r"^order_?no$", r"^order_?number$", r"^invoice_?no$",
                   r"^transaction_?id$"),
                  (r"order", r"invoice", r"\bid\b", r"reference"), "text"),

    # -- M5 roles ---------------------------------------------------------
    OPERATING_EXPENSE:   ((r"^operating_?expenses?$", r"^opex$", r"^overheads?$",
                           r"^admin_?expenses?$"),
                          (r"opex", r"overhead", r"operating_?exp"), "number"),
    DEPRECIATION:        ((r"^depreciation$", r"^amortisation$", r"^amortization$",
                           r"^depreciation_?amortisation$"),
                          (r"deprecia", r"amorti"), "number"),
    INVENTORY_VALUE:     ((r"^inventory$", r"^inventory_?value$", r"^stock_?value$",
                           r"^closing_?stock$"),
                          (r"inventory", r"stock_?value"), "number"),
    CASH_BALANCE:        ((r"^cash$", r"^cash_?balance$", r"^bank_?balance$",
                           r"^closing_?cash$"),
                          (r"cash_?balance", r"bank_?balance"), "number"),
    RECEIVABLES:         ((r"^receivables$", r"^accounts_?receivable$", r"^debtors$",
                           r"^trade_?receivables$"),
                          (r"receivable", r"debtor"), "number"),
    PAYABLES:            ((r"^payables$", r"^accounts_?payable$", r"^creditors$",
                           r"^trade_?payables$"),
                          (r"payable", r"creditor"), "number"),
    CURRENT_ASSETS:      ((r"^current_?assets$",), (r"current_?asset",), "number"),
    CURRENT_LIABILITIES: ((r"^current_?liabilities$",), (r"current_?liabilit",), "number"),
    MARKETING_SPEND:     ((r"^marketing_?spend$", r"^acquisition_?spend$",
                           r"^marketing_?cost$", r"^ad_?spend$"),
                          (r"marketing", r"acquisition_?cost", r"ad_?spend"), "number"),
    LEAD_COUNT:          ((r"^leads?$", r"^lead_?count$", r"^enquiries$", r"^visitors$",
                           r"^sessions$"),
                          (r"\blead", r"enquir", r"visitor", r"session"), "number"),
    DEAL_STAGE:          ((r"^stage$", r"^deal_?stage$", r"^opportunity_?stage$",
                           r"^outcome$", r"^status$"),
                          (r"stage", r"outcome"), "text"),
    PIPELINE_VALUE:      ((r"^pipeline_?value$", r"^opportunity_?value$",
                           r"^deal_?value$", r"^weighted_?pipeline$"),
                          (r"pipeline", r"opportunity_?value", r"deal_?value"), "number"),
    DEAL_OPENED:         ((r"^opened_?date$", r"^created_?date$", r"^deal_?opened$",
                           r"^opportunity_?created$"),
                          (r"opened", r"created_?date"), "date"),
    DEAL_CLOSED:         ((r"^closed_?date$", r"^won_?date$", r"^deal_?closed$",
                           r"^close_?date$"),
                          (r"closed", r"won_?date"), "date"),
    RECURRING_REVENUE:   ((r"^mrr$", r"^recurring_?revenue$", r"^subscription_?revenue$",
                           r"^arr$"),
                          (r"recurring", r"subscription_?rev", r"\bmrr\b", r"\barr\b"),
                          "number"),
    INVESTMENT:          ((r"^investment$", r"^capital_?invested$", r"^cost_?of_?investment$"),
                          (r"investment", r"invested"), "number"),
}

# Roles where a "cost"-looking name must not win a "unit"-prefixed column, and similar.
_NEGATIVE = {
    REVENUE: (r"unit_?price", r"^cost", r"unit_?cost", r"quantity", r"qty",
              r"recurring", r"pipeline", r"marketing"),
    COST: (r"unit_?cost", r"unit_?price", r"opex", r"overhead", r"marketing"),
    COST:    (r"unit_?cost", r"unit_?price"),
    QUANTITY: (r"price", r"amount", r"revenue", r"cost"),
}


def _normalise(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _kind_of(values):
    """What a column actually contains, from a sample of its non-empty values."""
    sample = [v for v in values if v is not None and v != ""][:200]
    if not sample:
        return "empty", 0.0
    dates = sum(1 for v in sample if isinstance(v, (datetime.date, datetime.datetime)))
    numbers = sum(1 for v in sample if isinstance(v, (int, float)) and not isinstance(v, bool))
    texts = len(sample) - dates - numbers
    total = float(len(sample))
    if dates / total >= 0.9:
        return "date", dates / total
    if numbers / total >= 0.9:
        return "number", numbers / total
    if texts / total >= 0.9:
        return "text", texts / total
    return "mixed", max(dates, numbers, texts) / total


class Evidence:
    """Why a column scored as it did, broken down by signal.

    Kept separate from the score so that "why did BusinessOps think this column was revenue?"
    has a real answer rather than just a number.
    """

    __slots__ = ("name_score", "content_score", "penalty", "observed_kind",
                 "kind_purity", "notes")

    def __init__(self, name_score=0.0, content_score=0.0, penalty=0.0,
                 observed_kind=None, kind_purity=0.0, notes=None):
        self.name_score = round(name_score, 3)
        self.content_score = round(content_score, 3)
        self.penalty = round(penalty, 3)
        self.observed_kind = observed_kind
        self.kind_purity = round(kind_purity, 3)
        self.notes = list(notes or [])

    def as_dict(self):
        return {"name_score": self.name_score, "content_score": self.content_score,
                "penalty": self.penalty, "observed_kind": self.observed_kind,
                "kind_purity": self.kind_purity, "notes": self.notes}

    def explain(self):
        return "; ".join(self.notes) if self.notes else "no evidence recorded"

    def __repr__(self):
        return "Evidence(name=%.2f content=%.2f penalty=%.2f)" % (
            self.name_score, self.content_score, self.penalty)


class Mapping:
    """One column bound (or not) to a business role."""

    __slots__ = ("role", "column", "confidence", "status", "reason", "alternatives",
                 "evidence")

    def __init__(self, role, column, confidence, status, reason, alternatives=None,
                 evidence=None):
        self.role = role
        self.column = column
        self.confidence = round(confidence, 3)
        self.status = status
        self.reason = reason
        self.alternatives = list(alternatives or [])
        self.evidence = evidence or Evidence()

    @property
    def usable_without_confirmation(self):
        return self.status == AUTO

    def as_dict(self):
        return {"role": self.role, "column": self.column, "confidence": self.confidence,
                "status": self.status, "reason": self.reason,
                "alternatives": self.alternatives, "evidence": self.evidence.as_dict()}

    def explain(self):
        """A sentence a user can read: why this column, and how sure."""
        return ("Column %r maps to %r with confidence %.2f (%s). Evidence: %s."
                % (self.column, self.role, self.confidence, self.status,
                   self.evidence.explain()))

    def __repr__(self):
        return "Mapping(%s -> %s @%.2f %s)" % (self.role, self.column,
                                               self.confidence, self.status)


class SemanticMap:
    """The resolved mapping for a dataset, including what still needs confirming."""

    def __init__(self, mappings, unmapped_roles, columns, rejected=None):
        self.mappings = mappings                 # role -> Mapping
        self.unmapped_roles = list(unmapped_roles)
        self.columns = list(columns)
        self.rejected = dict(rejected or {})     # role -> best candidate that missed

    def column_for(self, role):
        mapping = self.mappings.get(role)
        return mapping.column if mapping else None

    def has(self, role):
        return role in self.mappings

    def needs_confirmation(self):
        return [m for m in self.mappings.values() if m.status == CONFIRM_REQUIRED]

    def confirmed(self, role):
        """True only when the role is mapped and needs no confirmation."""
        mapping = self.mappings.get(role)
        return bool(mapping and mapping.status == AUTO)

    def require(self, roles):
        """Roles that are missing, and roles that are mapped but unconfirmed."""
        missing = [r for r in roles if r not in self.mappings]
        unconfirmed = [r for r in roles
                       if r in self.mappings and self.mappings[r].status != AUTO]
        return missing, unconfirmed

    def as_dict(self):
        return {"mappings": {r: m.as_dict() for r, m in sorted(self.mappings.items())},
                "unmapped_roles": self.unmapped_roles,
                "rejected": self.rejected,
                "needs_confirmation": [m.role for m in self.needs_confirmation()]}

    def explain(self, role):
        """Why this role is mapped as it is, or why it is not mapped at all."""
        if role in self.mappings:
            return self.mappings[role].explain()
        if role in self.rejected:
            best = self.rejected[role]
            return ("No column was accepted for %r. The closest was %r at confidence %.2f, "
                    "below the %.2f threshold: %s."
                    % (role, best["column"], best["confidence"], CONFIRM_THRESHOLD,
                       best["reason"]))
        return "No column resembled %r at all." % role

    def clarification_request(self):
        """The exact questions to put to the user, per the ambiguity protocol."""
        questions = []
        for mapping in self.needs_confirmation():
            alternatives = "".join(
                "\n    - %s (confidence %.2f)" % (c, s) for c, s in mapping.alternatives[:3])
            questions.append(
                "Role %r is provisionally mapped to column %r (confidence %.2f). %s"
                "\n  Candidates:%s\n  Confirm before any figure depends on it."
                % (mapping.role, mapping.column, mapping.confidence,
                   mapping.reason, alternatives or "\n    - (no alternative)"))
        return questions


def _score(role, column, values):
    """Score one (role, column) pair. Returns (score, reason, Evidence).

    Four signals: header name, column content, type agreement, and negative evidence.
    Each is recorded so the result can be explained rather than merely asserted.
    """
    strong, weak, expected = _PATTERNS[role]
    normalised = _normalise(column)
    notes = []

    name_score = 0.0
    if any(re.fullmatch(p, normalised) for p in strong):
        name_score = 0.75
        notes.append("header %r is a strong name for %s" % (column, role))
    elif any(re.search(p, normalised) for p in weak):
        name_score = 0.42
        notes.append("header %r weakly suggests %s" % (column, role))

    penalty = 0.0
    for negative in _NEGATIVE.get(role, ()):
        if re.search(negative, normalised):
            penalty = name_score * 0.65
            name_score -= penalty
            notes.append("penalised: the header also matches another role's pattern")
            break

    if name_score <= 0.0:
        return 0.0, "no name match", Evidence(
            0.0, 0.0, penalty, None, 0.0,
            ["header %r does not indicate %s" % (column, role)])

    kind, purity = _kind_of(values)
    if kind == "empty":
        notes.append("column is empty, so content cannot corroborate the header")
        return (name_score * 0.4, "name matches but the column is empty",
                Evidence(name_score, 0.0, penalty, kind, purity, notes))

    if kind == expected:
        content_score = 0.25 * purity
        notes.append("content is %s in %d%% of sampled values, matching what %s expects"
                     % (kind, int(purity * 100), role))
        reason = "name and content both indicate %s" % role
    elif kind == "mixed":
        content_score = 0.05
        notes.append("content is of mixed types, so it only weakly corroborates the header")
        reason = "name matches but the column holds mixed types"
    else:
        notes.append("content is %s but %s expects %s, so the header is contradicted"
                     % (kind, role, expected))
        return (name_score * 0.3,
                "name suggests %s but the column contains %s" % (role, kind),
                Evidence(name_score, 0.0, penalty, kind, purity, notes))

    return (min(1.0, name_score + content_score), reason,
            Evidence(name_score, content_score, penalty, kind, purity, notes))


def infer(dataset, roles=ROLES):
    """Infer a SemanticMap. Never guesses: low confidence yields confirmation or nothing."""
    scored = {}
    for role in roles:
        candidates = []
        for column in dataset.columns:
            score, reason, evidence = _score(role, column, dataset.column(column))
            if score > 0:
                candidates.append((column, score, reason, evidence))
        candidates.sort(key=lambda c: (-c[1], c[0]))
        if candidates:
            scored[role] = candidates

    # One column may only fill one role; the strongest claim wins.
    claimed, mappings = {}, {}
    ordered = sorted(scored.items(), key=lambda kv: -kv[1][0][1])
    for role, candidates in ordered:
        for column, score, reason, evidence in candidates:
            if column in claimed:
                continue
            if score < CONFIRM_THRESHOLD:
                break
            status = AUTO if score >= AUTO_THRESHOLD else CONFIRM_REQUIRED
            mappings[role] = Mapping(
                role, column, score, status, reason,
                alternatives=[(c, round(sc, 3))
                              for c, sc, _r, _e in candidates if c != column][:3],
                evidence=evidence)
            claimed[column] = role
            break

    rejected = {}
    for role, candidates in scored.items():
        if role in mappings:
            continue
        best = candidates[0]
        rejected[role] = {"column": best[0], "confidence": round(best[1], 3),
                          "reason": best[2], "evidence": best[3].as_dict()}

    unmapped = [r for r in roles if r not in mappings]
    return SemanticMap(mappings, unmapped, dataset.columns, rejected)


def derivable_profit(semantic_map):
    """Profit is usable if mapped directly, or derivable from revenue and cost."""
    if semantic_map.confirmed(PROFIT):
        return "direct"
    if semantic_map.confirmed(REVENUE) and semantic_map.confirmed(COST):
        return "derived"
    return None
