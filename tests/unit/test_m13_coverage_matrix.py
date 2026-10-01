"""M13.1 coverage-matrix and defect-register validator (ADR-0039 sections B, E.6, G.1, K.5).

Makes `docs/testing/coverage-matrix.md` and `docs/testing/defects.md` checkable on every run,
so the matrix cannot drift from the repository without a failing test:

- each of the seven closed sets has exactly the rows its **source** enumerates, recounted
  from the source file itself wherever the source is a table or a file list;
- every status and evidence value is from ADR-0039's closed vocabularies;
- every test a row cites exists, found by parsing the test modules, not by importing them;
- a `covered-by-M13` row cites a test M13 added;
- no row claims automated evidence while no eval case exists (ADR-0039 I-2 to I-4);
- every `gap` row is explained by a defect record, or by the one owner decision (U-1) that
  accepts S2-14 as an owner-accepted environment-unavailable gap (ADR-0040);
- every defect record has every ADR-0039 G.1 field, with closed values, and no score, rank
  or severity. The `status` vocabulary is ADR-0039's as amended by ADR-0043, which adds
  `fixed_product`. Each status pairs only with its class, and a `fixed_product` record must
  carry a status-basis paragraph citing an accepted ADR and an existing verification record;
- the totals table agrees with the rows.

It does not re-check that each cited test *ran unskipped*; that needs the closing run's output
and is done against it in the M13.1 development record (ADR-0039 K.5).
"""

import ast
import glob
import os
import re
import unittest
from collections import Counter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
#: BusinessOps M3 moved the M9-B harness from commands/ to dev/harness/ (ADR-0055); it is still
#: enumerated with the commands so every check keeps covering it at its new location.
MATRIX = os.path.join(REPO, "docs", "testing", "coverage-matrix.md")
DEFECTS = os.path.join(REPO, "docs", "testing", "defects.md")
ARCHITECTURE = os.path.join(REPO, "architecture.md")
ADR_0037 = os.path.join(REPO, "docs", "decisions", "ADR-0037-m12-connector-layer-contract.md")
PLAN = os.path.join(REPO, "project_plan.md")

STATUSES = ("covered", "covered-by-M13", "behavioural-only", "not-applicable", "gap")
LAYERS = ("deterministic", "behavioural", "manual")
AUTOMATED_CLASSES = ("automated_pass", "automated_fail", "not_executed", "execution_unavailable")
EVIDENCE = AUTOMATED_CLASSES + ("deterministic",)
SET_SIZES_IN_ADR_0039 = {"S1": 18, "S2": 15, "S3": 12, "S4": 19, "S5": 13, "S6": 3, "S7": 19}

#: The one `gap` explained by an owner decision rather than a defect: an owner-accepted
#: environment-unavailable gap (ADR-0040, amending ADR-0039 sections B and L). The owner resolved
#: U-1 on 2026-09-18 as (c), an accepted open gap, never covered. Any other unexplained gap fails.
OWNER_DECISIONS = {"S2-14": "U-1"}

TEST_ID = re.compile(r"`((?:unit|integration|negative)\.test_\w+\.\w+\.test\w*)`")
ROW = re.compile(r"^\| (S[1-7]-\d\d) \|")
DEFECT_FIELDS = ("defect_id", "source", "defect_class", "affected_component", "reproducer",
                 "expected_behavior", "observed_behavior", "status", "blocks_m13_completion",
                 "linked_reference", "found")
DEFECT_CLOSED = {"source": ("test", "eval", "measurement"),
                 "defect_class": ("product", "infrastructure"),
                 "status": ("open", "fixed_infrastructure", "fixed_product", "withdrawn"),
                 "blocks_m13_completion": ("yes", "no")}
#: ADR-0043: which statuses each class may carry. `fixed_infrastructure` is infrastructure-only
#: (ADR-0039 G.1); `fixed_product` is product-only, for a fix made and verified outside M13.
CLASS_STATUSES = {"product": ("open", "withdrawn", "fixed_product"),
                  "infrastructure": ("open", "withdrawn", "fixed_infrastructure")}
STATUS_BASIS = "**Status basis (ADR-0043).**"
DECISIONS = os.path.join(REPO, "docs", "decisions")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def matrix_rows():
    rows = []
    for line in _read(MATRIX).splitlines():
        match = ROW.match(line)
        if not match:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        rows.append({"id": cells[0], "requirement": cells[1], "layer": cells[2],
                     "tests": cells[3], "status": cells[4], "evidence": cells[5],
                     "notes": cells[6] if len(cells) > 6 else "",
                     "test_ids": TEST_ID.findall(cells[3])})
    return rows


def existing_test_ids():
    """Every `sub.module.Class.test_x` defined under tests/, by parsing, not importing."""
    found = set()
    for sub in ("unit", "integration", "negative"):
        for path in glob.glob(os.path.join(REPO, "tests", sub, "test_*.py")):
            module = os.path.splitext(os.path.basename(path))[0]
            tree = ast.parse(_read(path), filename=path)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name.startswith("test"):
                            found.add("%s.%s.%s.%s" % (sub, module, node.name, item.name))
    return found


def _section(text, start, stop=r"^---\s*$"):
    lines, inside = [], False
    for line in text.splitlines():
        if inside and re.match(stop, line):
            break
        if inside:
            lines.append(line)
        if re.match(start, line):
            inside = True
    return lines


def _table_rows(lines):
    return [l for l in lines if l.startswith("| ") and not re.match(r"^\|\s*-", l)][1:]


def source_counts():
    """What each set's source enumerates, recounted from the repository."""
    architecture = _read(ARCHITECTURE)
    section_16 = _table_rows(_section(architecture, r"^## 16\. "))
    section_8 = _table_rows(_section(architecture, r"^## 8\. "))
    section_15 = "\n".join(_section(architecture, r"^## 15\. "))
    corpus = re.search(r"Fixture corpus:(.*?)— plus", section_15, re.S).group(1)
    named_fixtures = [f for f in re.split(r",\s*", " ".join(corpus.split())) if f]
    adr_j = _table_rows(_section(_read(ADR_0037), r"^### J\. ", r"^### K\. "))
    plan = _read(PLAN)
    tier_rows = [l for l in plan.splitlines()
                 if re.match(r"^\| (Tier tests:|No-source, conflicting-source, stale-source)", l)]
    return {
        "S1": len(section_16),
        "S2": len(named_fixtures) + 2,     # + cross-tier equivalence, business-model relevance
        "S4": len((glob.glob(os.path.join(REPO, "commands", "*.md"))
             + glob.glob(os.path.join(REPO, "dev", "harness", "*.md")))),
        "S5": len(section_8),
        "S6": len(tier_rows),
        "S7": len([r for r in adr_j if re.match(r"^\| \d+ \|", r)]),
        "section_16_scenarios": [r.split("|")[1].strip() for r in section_16],
        "section_8_classes": [r.split("|")[1].replace("**", "").strip() for r in section_8],
        "section_15": section_15,
        "named_fixtures": named_fixtures,
        "commands": sorted(os.path.splitext(os.path.basename(p))[0]
                           for p in (glob.glob(os.path.join(REPO, "commands", "*.md"))
                                + glob.glob(os.path.join(REPO, "dev", "harness", "*.md")))),
    }


def defect_blocks():
    """{defect_id: the record's full text}, from its heading to the next `---` rule."""
    blocks, current = {}, None
    for line in (_read(DEFECTS) if os.path.exists(DEFECTS) else "").splitlines():
        heading = re.match(r"^### (M13-DEF-\d\d)\b", line)
        if heading:
            current = heading.group(1)
            blocks[current] = []
            continue
        if re.match(r"^---\s*$", line):
            current = None
        elif current is not None:
            blocks[current].append(line)
    return {k: "\n".join(v) for k, v in blocks.items()}


def status_basis(block):
    """The `**Status basis (ADR-0043).**` paragraph of a record, or None."""
    start = block.find(STATUS_BASIS)
    if start < 0:
        return None
    end = block.find("\n\n", start)
    return block[start:] if end < 0 else block[start:end]


def adr_is_accepted(number):
    for path in glob.glob(os.path.join(DECISIONS, "ADR-%s-*.md" % number)):
        return bool(re.search(r"^\*\*Status:\*\* Accepted\b", _read(path), re.M))
    return False


def status_problems(record, block):
    """Why a record's status is invalid under ADR-0039 G.1 as amended by ADR-0043; [] if valid."""
    problems = []
    status, klass = record.get("status"), record.get("defect_class")
    if status not in DEFECT_CLOSED["status"]:
        return ["status %r is not in the closed vocabulary" % (status,)]
    if klass not in CLASS_STATUSES:
        return ["defect_class %r is not in the closed vocabulary" % (klass,)]
    if status not in CLASS_STATUSES[klass]:
        problems.append("status %r is not allowed for a %s defect" % (status, klass))
    if status == "fixed_product":
        basis = status_basis(block or "")
        if basis is None:
            problems.append("fixed_product without a %s paragraph" % STATUS_BASIS)
        else:
            adrs = [n for n in re.findall(r"ADR-(\d{4})", basis) if n not in ("0039", "0043")]
            if not any(adr_is_accepted(n) for n in adrs):
                problems.append("fixed_product basis cites no accepted remediation ADR")
            records = re.findall(r"docs/development/[\w.-]+\.md", basis)
            if not any(os.path.isfile(os.path.join(REPO, r)) for r in records):
                problems.append("fixed_product basis cites no existing verification record")
    return problems


def defect_records():
    """{defect_id: {field: value}} from the register's `### M13-DEF-NN` blocks."""
    if not os.path.exists(DEFECTS):
        return {}
    records, current = {}, None
    for line in _read(DEFECTS).splitlines():
        heading = re.match(r"^### (M13-DEF-\d\d)\b", line)
        if heading:
            current = records.setdefault(heading.group(1), {})
            continue
        field = re.match(r"^\| `(\w+)` \| (.*) \|$", line)
        if current is not None and field:
            current[field.group(1)] = field.group(2).strip()
    return records


class SetsAreClosedAgainstTheirSources(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = matrix_rows()
        cls.by_set = Counter(r["id"][:2] for r in cls.rows)
        cls.sources = source_counts()

    def test_every_set_has_the_rows_adr_0039_names(self):
        self.assertEqual(dict(self.by_set), SET_SIZES_IN_ADR_0039)

    def test_each_countable_source_still_enumerates_that_many(self):
        for key in ("S1", "S2", "S4", "S5", "S6", "S7"):
            with self.subTest(set=key):
                self.assertEqual(self.sources[key], SET_SIZES_IN_ADR_0039[key])

    def test_row_ids_are_unique_and_sequential(self):
        ids = [r["id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        for key, size in SET_SIZES_IN_ADR_0039.items():
            expected = ["%s-%02d" % (key, n) for n in range(1, size + 1)]
            self.assertEqual([i for i in ids if i.startswith(key)], expected)

    def test_s1_rows_follow_the_section_16_scenarios_in_order(self):
        s1 = [r for r in self.rows if r["id"].startswith("S1")]
        for row, scenario in zip(s1, self.sources["section_16_scenarios"]):
            with self.subTest(row=row["id"]):
                self.assertTrue(row["requirement"].startswith(scenario), scenario)

    def test_s2_rows_quote_the_fixture_corpus_in_order(self):
        s2 = [r for r in self.rows if r["id"].startswith("S2")]
        for row, fixture in zip(s2, self.sources["named_fixtures"]):
            with self.subTest(row=row["id"]):
                self.assertEqual(row["requirement"], fixture)

    def test_s3_rows_quote_section_15(self):
        """Each quotation is verbatim; " … " marks an elision, and the parts appear in order."""
        text = " ".join(self.sources["section_15"].replace("**", "").split())
        for row in (r for r in self.rows if r["id"].startswith("S3")):
            quoted = " ".join(row["requirement"].replace("**", "").split())
            position = 0
            for fragment in quoted.split(" … "):
                with self.subTest(row=row["id"], fragment=fragment):
                    found = text.find(fragment, position)
                    self.assertGreaterEqual(found, 0)
                    position = found + len(fragment)

    def test_s4_names_every_command_exactly_once(self):
        named = sorted(re.search(r"`/([\w-]+)`", r["requirement"]).group(1)
                       for r in self.rows if r["id"].startswith("S4"))
        self.assertEqual(named, self.sources["commands"])

    def test_s5_rows_follow_the_section_8_classes_in_order(self):
        s5 = [r for r in self.rows if r["id"].startswith("S5")]
        for row, name in zip(s5, self.sources["section_8_classes"]):
            with self.subTest(row=row["id"]):
                self.assertTrue(row["requirement"].startswith(name), name)

    def test_s7_rows_follow_the_j_categories(self):
        s7 = [r for r in self.rows if r["id"].startswith("S7")]
        for number, row in enumerate(s7, start=1):
            with self.subTest(row=row["id"]):
                self.assertTrue(row["requirement"].startswith("J-%d " % number))

    def test_the_missing_24_scenario_list_is_declared_unavailable(self):
        text = _read(MATRIX)
        self.assertIn("24 specified scenarios", text)
        self.assertIn("**not reconstructed**", text)


class RowsUseTheClosedVocabularies(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = matrix_rows()
        cls.tests = existing_test_ids()
        cls.defects = defect_records()

    def test_status_layer_and_evidence_are_closed(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertIn(row["status"], STATUSES)
                self.assertIn(row["layer"], LAYERS)
                self.assertIn(row["evidence"], EVIDENCE)

    def test_every_cited_test_exists(self):
        for row in self.rows:
            for test_id in row["test_ids"]:
                with self.subTest(row=row["id"], test=test_id):
                    self.assertIn(test_id, self.tests)

    def test_covered_rows_cite_deterministic_tests(self):
        for row in self.rows:
            if row["status"] in ("covered", "covered-by-M13"):
                with self.subTest(row=row["id"]):
                    self.assertTrue(row["test_ids"])
                    self.assertEqual(row["layer"], "deterministic")
                    self.assertEqual(row["evidence"], "deterministic")

    def test_covered_by_m13_rows_cite_an_m13_test(self):
        for row in self.rows:
            if row["status"] == "covered-by-M13":
                with self.subTest(row=row["id"]):
                    self.assertTrue(any(".test_m13_" in t for t in row["test_ids"]))

    def test_behavioural_rows_carry_one_automated_class(self):
        for row in self.rows:
            if row["status"] == "behavioural-only":
                with self.subTest(row=row["id"]):
                    self.assertEqual(row["layer"], "behavioural")
                    self.assertIn(row["evidence"], AUTOMATED_CLASSES)

    def test_no_row_claims_automated_evidence_while_no_eval_case_exists(self):
        cases = glob.glob(os.path.join(REPO, "evals", "**", "case.yaml"), recursive=True)
        cases += glob.glob(os.path.join(REPO, "evals", "**", "prompt.md"), recursive=True)
        if cases:
            self.skipTest("eval cases exist; automated evidence is then possible")
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertNotIn(row["evidence"], ("automated_pass", "automated_fail"))

    def test_every_gap_is_explained(self):
        for row in self.rows:
            if row["status"] != "gap":
                continue
            with self.subTest(row=row["id"]):
                cited = re.findall(r"M13-DEF-\d\d", row["notes"])
                if row["id"] in OWNER_DECISIONS:
                    self.assertIn(OWNER_DECISIONS[row["id"]], row["notes"])
                else:
                    self.assertTrue(cited, "a gap must cite its defect record")
                    for defect_id in cited:
                        self.assertIn(defect_id, self.defects)

    def test_owner_decisions_are_only_used_for_gaps(self):
        statuses = {r["id"]: r["status"] for r in self.rows}
        for row_id in OWNER_DECISIONS:
            self.assertEqual(statuses[row_id], "gap")

    def test_the_totals_table_agrees_with_the_rows(self):
        text = _read(MATRIX)
        line = re.search(r"^\| \*\*All\*\* \|(.*)\|$", text, re.M).group(1)
        numbers = [int(n) for n in re.findall(r"\d+", line)]
        counts = Counter(r["status"] for r in self.rows)
        self.assertEqual(numbers, [len(self.rows)] + [counts[s] for s in STATUSES])


class DefectRegisterIsComplete(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.defects = defect_records()

    def test_the_register_exists(self):
        self.assertTrue(os.path.exists(DEFECTS))

    def test_every_record_has_every_field(self):
        for defect_id, record in self.defects.items():
            with self.subTest(defect=defect_id):
                self.assertEqual(sorted(record), sorted(DEFECT_FIELDS))
                self.assertEqual(record["defect_id"], defect_id)

    def test_closed_fields_use_closed_values(self):
        for defect_id, record in self.defects.items():
            for field, allowed in DEFECT_CLOSED.items():
                with self.subTest(defect=defect_id, field=field):
                    self.assertIn(record.get(field), allowed)

    def test_blocking_follows_the_rule_not_judgement(self):
        for defect_id, record in self.defects.items():
            expected = ("yes" if record["defect_class"] == "infrastructure"
                        and record["status"] == "open" else "no")
            with self.subTest(defect=defect_id):
                self.assertEqual(record["blocks_m13_completion"], expected)

    def test_a_product_defect_stays_open_through_m13(self):
        """ADR-0039 G.1 as amended by ADR-0043: `open` or `withdrawn`, or `fixed_product` once a
        dedicated milestone outside M13 has fixed and verified it. Never `fixed_infrastructure`."""
        for defect_id, record in self.defects.items():
            if record["defect_class"] == "product":
                with self.subTest(defect=defect_id):
                    self.assertIn(record["status"], ("open", "withdrawn", "fixed_product"))

    def test_every_status_pairs_with_its_class_and_a_product_fix_states_its_basis(self):
        blocks = defect_blocks()
        for defect_id, record in self.defects.items():
            with self.subTest(defect=defect_id):
                self.assertEqual(status_problems(record, blocks.get(defect_id)), [])

    def test_no_record_is_scored_ranked_or_given_a_severity(self):
        text = _read(DEFECTS) if os.path.exists(DEFECTS) else ""
        for word in ("`severity`", "`score`", "`rank`", "`priority`"):
            self.assertNotIn(word, text)

    def test_ids_are_sequential_and_never_reused(self):
        ids = sorted(self.defects)
        self.assertEqual(ids, ["M13-DEF-%02d" % n for n in range(1, len(ids) + 1)])


class StatusVocabularySemantics(unittest.TestCase):
    """ADR-0043: `fixed_product` is accepted only as defined, the old statuses still are, and
    everything else is rejected. Exercised on synthetic records, so the rule is proven
    independently of the register's current contents."""

    RECORD = "`docs/development/2026-09-20-m13-def-04-implementation.md`"
    BASIS = "**Status basis (ADR-0043).** Fixed under accepted ADR-0042; verified in %s." % RECORD

    def check(self, status, klass, block=""):
        return status_problems({"status": status, "defect_class": klass}, block)

    def test_the_new_status_is_accepted_for_a_product_defect_with_its_basis(self):
        self.assertIn("fixed_product", DEFECT_CLOSED["status"])
        self.assertEqual(self.check("fixed_product", "product", self.BASIS), [])

    def test_the_existing_statuses_remain_accepted_for_their_classes(self):
        for status, klass in (("open", "product"), ("withdrawn", "product"),
                              ("open", "infrastructure"), ("withdrawn", "infrastructure"),
                              ("fixed_infrastructure", "infrastructure")):
            with self.subTest(status=status, klass=klass):
                self.assertEqual(self.check(status, klass), [])

    def test_invalid_statuses_remain_rejected(self):
        for status in ("fixed", "resolved", "closed", "done", "FIXED_PRODUCT", "fixed-product",
                       "fixed_product ", "", None):
            with self.subTest(status=status):
                self.assertTrue(self.check(status, "product", self.BASIS))

    def test_each_fix_status_is_bound_to_its_class(self):
        self.assertTrue(self.check("fixed_product", "infrastructure", self.BASIS))
        self.assertTrue(self.check("fixed_infrastructure", "product"))

    def test_fixed_product_without_a_verifiable_basis_is_rejected(self):
        cases = {
            "no basis paragraph": "",
            "no ADR cited": "**Status basis (ADR-0043).** Verified in %s." % self.RECORD,
            "only ADR-0039 and ADR-0043 cited": "**Status basis (ADR-0043).** Under ADR-0039; "
                                                "verified in %s." % self.RECORD,
            "an ADR that does not exist": "**Status basis (ADR-0043).** Fixed under ADR-9999; "
                                          "verified in %s." % self.RECORD,
            "no existing record": "**Status basis (ADR-0043).** Fixed under ADR-0042; verified "
                                  "in `docs/development/2099-01-01-nonexistent.md`.",
        }
        for name, block in cases.items():
            with self.subTest(case=name):
                self.assertTrue(self.check("fixed_product", "product", block))

    def test_the_blocking_rule_gives_no_for_a_product_fix(self):
        """The unchanged rule: `yes` only for an open infrastructure defect."""
        for klass, status in (("product", "fixed_product"), ("product", "open"),
                              ("infrastructure", "fixed_infrastructure")):
            blocks = "yes" if klass == "infrastructure" and status == "open" else "no"
            with self.subTest(klass=klass, status=status):
                self.assertEqual(blocks, "no")
