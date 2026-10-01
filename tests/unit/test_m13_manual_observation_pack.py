"""M13.2 manual-observation execution pack validator (ADR-0039 section E.1, outcome (c); G-2).

`docs/testing/manual-observation-pack.md` tells the owner how to perform the twelve
`manual_observation` scenarios that ADR-0039 section E.1 requires, one per S3 row. It is
preparation only. This module keeps it honest and in step with the case files:

- exactly twelve packets, one per S3 row, in order, each on the case that `eval-suite.md`
  designates for that row, and each case naming that row in its `coverage_rows`;
- each packet's exact prompt equals the case's `prompt` byte for byte; its expected property
  quotes the case's `expected_property`; its inputs are the case's inputs, which exist, with the
  manifest SHA-256 for a fixture; its record path follows `docs/testing/manual/<row>-<case-id>.md`;
- no manual observation exists yet (`docs/testing/manual/` is absent), the pack says so, and
  no packet predicts or claims a result;
- the evidence-class table keeps `manual_observation` apart from every automated class;
- WD-1 (product defect M13-DEF-04) is recorded as remediated on 2026-09-20 under ADR-0042, with
  its finding kept as history and G-2 unchanged;
- G-3 is stated OPEN in the required words, and the pack grants and names nothing prohibited.

When the owner records the first observation, `test_no_manual_observation_exists_yet` must be
replaced, in the same change, by assertions on the records themselves.
"""

import json
import os
import re
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACK = os.path.join(REPO, "docs", "testing", "manual-observation-pack.md")
SUITE_DOC = os.path.join(REPO, "docs", "testing", "eval-suite.md")
MANUAL_DIR = os.path.join(REPO, "docs", "testing", "manual")
MANIFEST = os.path.join(REPO, "tests", "fixtures", "eval_inputs", "manifest.json")

G3_SENTENCE = ("Platform verification remains open and is required before any automated/plugin "
               "evaluation execution.")
ROWS = ["S3-%02d" % n for n in range(1, 13)]
PACKET = re.compile(r"^### Scenario (\d+) — (S3-\d\d) — `([\w-]+)`$", re.M)
FIELDS = ("Matrix row", "Case", "Purpose", "Input", "Working-directory setup", "Exact prompt",
          "Expected property", "Forbidden behaviour", "Evidence to capture", "Void condition",
          "Record path")
PREDICTIONS = re.compile(r"(?i)\bshould (pass|fail|refuse)\b|\bwill (pass|fail|refuse|not)\b|"
                         r"\bexpected response\b|\bthe model will\b|\bis expected to (say|refuse|"
                         r"answer|respond)\b|\b(case|scenario|observation) (passed|failed|passes|"
                         r"fails)\b|\bresult:\s*(pass|fail)")
FORBIDDEN_TOKENS = ("--allow-real-servers", "--mocks off", "--publish-report", "--scaffold",
                    "WebSearch", "WebFetch", "mcp__")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def load_cases():
    tests_dir = os.path.join(REPO, "tests")
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    from unit.test_m13_eval_cases import load_cases as load
    return load()


def packets():
    """[(number, row, case_id, body)] in document order."""
    text = _read(PACK)
    found = list(PACKET.finditer(text))
    result = []
    for index, match in enumerate(found):
        end = found[index + 1].start() if index + 1 < len(found) else len(text)
        result.append((int(match.group(1)), match.group(2), match.group(3),
                       text[match.end():end]))
    return result


def field(body, name):
    match = re.search(r"^- \*\*%s:\*\*(.*?)(?=^- \*\*|\Z)" % re.escape(name), body, re.M | re.S)
    return match.group(1) if match else None


def designations():
    return dict(re.findall(r"^\| (S3-\d\d) \| `(evals/[\w-]+/[\w-]+)`", _read(SUITE_DOC), re.M))


class PacketInventory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.packets = packets()
        cls.cases = load_cases()
        cls.designated = designations()

    def test_twelve_packets_one_per_s3_row_in_order(self):
        self.assertEqual([p[0] for p in self.packets], list(range(1, 13)))
        self.assertEqual([p[1] for p in self.packets], ROWS)

    def test_each_packet_is_on_the_designated_case_for_its_row(self):
        self.assertEqual(sorted(self.designated), ROWS)
        for _n, row, case_id, body in self.packets:
            directory = self.designated[row]
            with self.subTest(row=row):
                self.assertEqual(directory.rsplit("/", 1)[1], case_id)
                self.assertIn(directory, self.cases)
                self.assertIn(row, self.cases[directory]["coverage_rows"])
                self.assertIn("`%s/case.yaml`" % directory, field(body, "Case"))

    def test_every_packet_has_every_field(self):
        for _n, row, _case, body in self.packets:
            for name in FIELDS:
                with self.subTest(row=row, field=name):
                    self.assertIsNotNone(field(body, name))
                    self.assertTrue(field(body, name).strip())


class PacketsMatchTheCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.packets = packets()
        cls.cases = load_cases()
        cls.designated = designations()
        with open(MANIFEST, encoding="utf-8") as handle:
            cls.manifest = {f["path"]: f for f in json.load(handle)["fixtures"]}

    def case(self, row):
        return self.cases[self.designated[row]]

    def test_the_exact_prompt_is_the_case_prompt_byte_for_byte(self):
        for _n, row, _case, body in self.packets:
            block = re.search(r"```text\n(.*?)\n  ```", field(body, "Exact prompt"), re.S).group(1)
            prompt = "\n".join(line[2:] for line in block.split("\n"))
            with self.subTest(row=row):
                self.assertEqual(prompt + "\n", self.case(row)["prompt"])

    def test_the_expected_property_quotes_the_case(self):
        for _n, row, _case, body in self.packets:
            with self.subTest(row=row):
                self.assertTrue(field(body, "Expected property").strip().startswith(
                    self.case(row)["expected_property"]))

    def test_the_purpose_quotes_the_case(self):
        for _n, row, _case, body in self.packets:
            with self.subTest(row=row):
                self.assertEqual(field(body, "Purpose").strip(), self.case(row)["purpose"])

    def test_inputs_are_the_case_inputs_and_exist(self):
        for _n, row, _case, body in self.packets:
            named = re.findall(r"`((?:assets|tests)/[\w./-]+)`", field(body, "Input"))
            setup = re.findall(r'cp "<REPO>/([\w./-]+)"', field(body, "Working-directory setup"))
            inputs = self.case(row)["inputs"]
            with self.subTest(row=row):
                self.assertEqual(named, inputs)
                self.assertEqual(setup, inputs)
                if not inputs:
                    self.assertEqual(field(body, "Input").strip(), "none")
                for path in inputs:
                    self.assertTrue(os.path.isfile(os.path.join(REPO, path)))
                    if path in self.manifest:
                        self.assertIn(self.manifest[path]["sha256"], field(body, "Input"))

    def test_record_paths_follow_the_canonical_convention(self):
        for _n, row, case_id, body in self.packets:
            with self.subTest(row=row):
                self.assertEqual(field(body, "Record path").strip(),
                                 "`docs/testing/manual/%s-%s.md`" % (row, case_id))


class NothingIsObservedOrPredicted(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = _read(PACK)

    def test_no_manual_observation_exists_yet(self):
        self.assertFalse(os.path.exists(MANUAL_DIR))
        self.assertIn("ZERO manual observations have been performed", self.text)

    def test_no_packet_predicts_or_claims_a_result(self):
        for _n, row, _case, body in packets():
            with self.subTest(row=row):
                self.assertIsNone(PREDICTIONS.search(body))
                self.assertIn("**Observe** whether", body) if row != "S3-12" else \
                    self.assertIn("**Observe** which", body)

    def test_the_template_is_a_template_not_a_record(self):
        template = re.search(r"````markdown\n(.*?)\n````", self.text, re.S).group(1)
        self.assertIn("# MANUAL OBSERVATION — <row> — <case-id> — not an automated result", template)
        for placeholder in ("<YYYY-MM-DD>", "<git rev-parse HEAD>", "<the case's prompt, exactly>"):
            self.assertIn(placeholder, template)
        self.assertIsNone(re.search(r"\b20\d\d-\d\d-\d\d\b", template))

    def test_evidence_classes_are_kept_apart(self):
        rows = dict(re.findall(r"^\| `(\w+)` \| [^|]+ \| (.+) \|$", self.text, re.M))
        self.assertEqual(sorted(rows), sorted(["manual_observation", "automated_pass",
                                               "automated_fail", "not_executed",
                                               "execution_unavailable"]))
        self.assertIn("only class a record carries", rows["manual_observation"])
        for automated in ("automated_pass", "automated_fail"):
            self.assertTrue(rows[automated].startswith("**Never.**"))
        self.assertIn("stays `not_executed`", rows["not_executed"])

    def test_wd1_is_recorded_as_remediated_with_its_history_kept(self):
        """WD-1 (classification C, M13-DEF-04) was remediated on 2026-09-20 under ADR-0042.

        The pack must state the remediated state first, keep the WD-1 finding as history, keep
        G-2 unchanged, and still perform no observation. The launcher it names must exist.
        """
        from unit.test_m13_coverage_matrix import defect_records
        record = defect_records()["M13-DEF-04"]
        self.assertEqual(record["defect_class"], "product")
        self.assertIn("sys.path.insert(0, 'lib/python')", record["reproducer"])
        self.assertIn("RESOLVED 2026-09-20", self.text)
        self.assertIn("S3-01 to S3-11 are no longer blocked by M13-DEF-04", self.text)
        self.assertIn("**G-2 is unchanged**", self.text)
        self.assertIn("classification C", self.text)
        self.assertIn('python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/bops_run.py" -c', self.text)
        self.assertNotIn("Proposed ADR-0042", self.text)
        self.assertTrue(os.path.isfile(os.path.join(REPO, "lib", "python", "bops_run.py")))

    def test_g3_is_stated_open(self):
        self.assertIn(G3_SENTENCE, self.text)
        self.assertIn("G-3 is\nOPEN", self.text)

    def test_nothing_prohibited_is_named_or_granted(self):
        for token in FORBIDDEN_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)

    def test_no_url_outside_the_reserved_domains(self):
        for host in re.findall(r"https?://([^/\s'\"<>)`]+)", self.text):
            with self.subTest(host=host):
                self.assertRegex(host.lower(), r"(^|\.)(example\.(com|org|net)|example|invalid)$")


if __name__ == "__main__":
    unittest.main()
