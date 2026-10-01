"""M13.2 static eval-case validator (ADR-0039 section E.5, as amended by ADR-0041 section 8).

Reads every `evals/<suite>/<case>/case.yaml` **as text**. The standard library has no YAML
parser, so `read_case()` below accepts only the restricted subset the case schema
(`docs/testing/eval-suite.md`) allows, and anything outside it fails. It then checks:

- **layout:** the five suites, one `case.yaml` per case directory, nothing else under
  `evals/`, no `evals/mocks/`, and no scaffold script;
- **schema:** every required field, closed vocabularies, and ids unique and equal to their
  directory;
- **inventory:** every suite and case ADR-0039 section E.3 names, with each enumerable part
  reconciled against the repository rather than a list: every model-invocable read-only
  command, every built skill, the four ADR-0009 questions, and the six D2 near-miss pairs in
  `docs/testing/measurements.md`;
- **inputs:** every input under `assets/demo-data/` or `tests/fixtures/eval_inputs/`, named
  both ways, with S3-01 to S3-03 on their fixtures, S3-04 on the demo file and S3-05 on none;
- **safety:** no prohibited flag, no web or `mcp__` grant, no real URL, address or
  token-shaped string, no absolute path, and nothing that depends on the clock or the
  environment;
- **graders:** a closed check vocabulary, compilable patterns, and a stated reason on every
  LLM grader. No score, rank or answer key taken from a product run;
- **evidence:** ADR-0039 E.1 outcome **(a)**, the M13.2 closing evaluation of 2026-09-24/25.
  Every case's class is the one the M13-DEF-06 admissibility rule computes from the committed
  result fixture `tests/fixtures/eval_results/2026-09-25-closing-evaluation.json`, never one
  asserted by hand; every behavioural matrix row carries the E.6 precedence of its cases'
  classes; and no case or row claims a manual observation. A later execution must update this
  module together with its record;
- **fixtures (ADR-0041 section 8):** the manifest, byte-identical rebuild, two-way binding,
  the builder's static inspection, encoding and size, and no grader string in a bound fixture.

It executes no eval, starts no process, and reads nothing outside the repository and one
temporary directory.
"""

import ast
import glob
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EVALS = os.path.join(REPO, "evals")
MATRIX = os.path.join(REPO, "docs", "testing", "coverage-matrix.md")
MEASUREMENTS = os.path.join(REPO, "docs", "testing", "measurements.md")
PROCEDURE = os.path.join(REPO, "docs", "testing", "eval-suite.md")
#: ADR-0044 Phase 1's audit trail. It lives outside evals/, which holds case files only.
MIGRATION_MAP = os.path.join(REPO, "docs", "testing", "grader-migration-map.json")
ADR_0009 = os.path.join(REPO, "docs", "decisions",
                        "ADR-0009-comparative-intelligence-privacy-boundary.md")
CONFIG = os.path.join(REPO, "config", "businessops.defaults.json")
FIXTURE_DIR = os.path.join(REPO, "tests", "fixtures", "eval_inputs")
MANIFEST = os.path.join(FIXTURE_DIR, "manifest.json")
BUILDER = os.path.join(REPO, "tests", "fixtures", "build_eval_inputs.py")

DEMO = "assets/demo-data/northwind_sales.csv"
#: The two nested mappings the platform layer uses (ADR-0044, and F.6's scaffold).
NESTED_KEYS = ("execution", "context")
#: The one scaffold file name, in the case directory ADR-0039 A.2 puts it in.
SCAFFOLD_NAME = "scaffold.sh"
#: The harness writes its own results under `evals/<dir>/results/` by default. That output is
#: gitignored and is not a case artifact, so the layout assertions step over it instead of
#: failing on it, which is what the Stage 2 pilot's own output did (M13-DEF-09).
RESULTS_DIR = "results"
INPUT_ROOTS = ("assets/demo-data/", "tests/fixtures/eval_inputs/")
SUITES = {"behaviour": "b", "disclosure": "d", "approval": "a", "connectors": "c", "routing": "r"}

#: The BusinessOps semantic layer (ADR-0044). `graders` is the platform layer and is required
#: only of a case that has one; a case whose every grader is pending has none (see PLATFORM).
REQUIRED_KEYS = ("schema", "schema_version", "name", "platform_status", "execution",
                 "id", "suite", "purpose", "coverage_rows", "components",
                 "requires_business_file", "inputs", "fixture", "prompt", "expected_property",
                 "safety", "tool_grants", "ablation", "evidence_class", "evidence_reason",
                 "bops_graders")
SCHEMA = "bops-eval-case/2"
#: ADR-0044: the platform contract read from Claude Code 2.1.278. `schema_version` is a string
#: whose major part must not exceed the binary's supported major, which is 1.
SCHEMA_VERSION = "1.0"
PLATFORM_STATUSES = ("loadable", "pending_trace_mapping")
#: The six grader types the platform's discriminated union accepts, and the keys each one takes.
#: Every platform grader object is strict, so an unknown key is rejected, not ignored.
PLATFORM_GRADERS = {
    "regex": {"required": ("type", "name", "pattern"),
              "optional": ("target", "flags", "match", "weight", "arm")},
    "tool_order": {"required": ("type", "name", "before", "after"),
                   "optional": ("weight", "arm")},
    "tool_used": {"required": ("type", "name", "tool"),
                  "optional": ("input_match", "min", "max", "weight", "arm")},
    "file_exists": {"required": ("type", "name", "path"), "optional": ("exists", "weight", "arm")},
    "llm": {"required": ("type", "name", "criteria"), "optional": ("focus", "weight", "arm")},
    "baseline": {"required": ("type", "name", "baseline_file", "criteria"),
                 "optional": ("weight", "arm")},
}
PLATFORM_TARGETS = ("last_message", "trace", "files", "mock_calls")
PLATFORM_MATCHES = ("contains", "not_contains")
PENDING = "pending_trace_mapping"
ROUTING_KEYS = ("routing_kind",)
#: ADR-0048: a case may declare one precondition fixture, and names both keys or neither.
PRECONDITION_KEYS = ("precondition_fixture", "precondition_path")
#: The only case ADR-0048 admits a precondition fixture for.
PRECONDITION_CASES = ("evals/approval/a20-overwrite-names-file",)
NEAR_MISS_KEYS = ("overlap_source", "overlap_tier", "overlap_pair", "competing_component")
SAFETY = ("synthetic-data-only", "no-web", "no-mcp-tool", "no-authentication",
          "no-connector", "no-publish")
#: The one symbolic grant: Bash for the engine's `python` invocations (ADR-0039 F.5).
GRANTS = ("engine-python",)
#: The M13.2 closing evaluation, 2026-09-24/25: the five invocations' results, trimmed to what
#: the M13-DEF-06 rule reads. Every case's recorded class is derived from this file.
CLOSING_RESULT = "2026-09-25-closing-evaluation.json"


def current_case_id(recorded):
    """The current id of a case as a historical result fixture recorded it.

    The result fixtures are SHA-256 pinned evidence and are never edited. They were recorded before
    BusinessOps Milestone 1 renamed the routing cases' technical prefix, so they name those cases
    `r01-positive-biq-...`; the case directories are now `r01-positive-bops-...`. Only that one
    segment is translated, so any other difference between a fixture and the suite still fails.
    """
    return recorded.replace("-biq-", "-bops-")
#: Every recorded reason opens with this, and names its invocation and results directory.
CLOSING_PREFIX = "M13.2 closing evaluation, invocation --case "
#: The pilot's history is kept in the first case's reason, not overwritten (ADR-0039 E.6 records
#: the closing result; the 2026-09-22 pilot remains a historical fact in its fixture and records).
PILOT_HISTORY = ("historical, superseded as the M13.2 result: executed 2026-09-22 under the "
                 "owner-authorised one-run pilot and classified automated_fail")
#: The E.6 precedence a behavioural row applies to its cases' classes: an observed failure
#: outranks an unavailability, which outranks a pass; `not_executed` only if nothing ran.
ROW_PRECEDENCE = ("automated_fail", "execution_unavailable", "automated_pass", "not_executed")

#: The first case attempted under section F.
FIRST_CASE = "evals/approval/a01-read-only-anomaly-detection"
#: Which cases carry a F.6 scaffold is no longer a hand-kept list. Since 2026-09-23 the rule is an
#: invariant: **a case declares a scaffold if and only if it requires a business file.** The two
#: halves come from different places -- the `requires_business_file` field, and the presence of
#: `context.scaffold_script` together with the file on disk -- so asserting them equal is not
#: tautological. This replaced `STAGED_CASES` and `UNSTAGED_COUNT`, which existed only while the
#: mechanism was proved on the pilot case alone and 37 cases were still waiting (M13-DEF-07).
#: The pilot run's committed result shape, in `tests/fixtures/eval_results/`.
PILOT_RESULT = "2026-09-22-pilot-executed.json"
#: The number of business-file cases the repository holds. Asserted, so adding or removing one has
#: to move this number deliberately rather than silently.
BUSINESS_FILE_COUNT = 38

#: Deterministic checks and the argument fields each one requires.
DETERMINISTIC_CHECKS = {
    "skill_invoked": ("skill",), "skill_not_invoked": ("skill",),
    "command_invoked": ("command",), "command_not_invoked": ("command",),
    "agent_not_dispatched": ("agent",),
    "tool_not_invoked": ("tool",),
    "response_matches": ("pattern", "target"), "response_not_matches": ("pattern", "target"),
}
GRADER_KEYS = ("id", "kind", "check", "skill", "command", "agent", "tool", "pattern", "target",
               "property", "criteria", "why_not_deterministic",
               "platform_mapping", "platform_graders", "pending_reason")
TARGETS = ("final_response",)
#: The checks whose platform mapping needs a fact only a run supplies. **Empty since 2026-09-22**:
#: ADR-0044 stage 3 closed the boundary from the observed trace of the owner-authorised three-run
#: pilot, which showed a plugin command firing under the `Skill` tool with the input
#: `{"skill": "businessops:<command>", ...}`, byte-identically in all three runs. `command_invoked`
#: and `command_not_invoked` were the two, and they were mapped from that trace rather than guessed.
#: The tuple stays as the mechanism, so a future check that needs a run can be named here again.
PENDING_CHECKS = ()
#: The observed tool identifier, and the input prefix that discriminates one command from another.
OBSERVED_COMMAND_TOOL = "Skill"
OBSERVED_COMMAND_PREFIX = "businessops:"

#: ADR-0039 E.5 fourth assertion: never in a case or in the procedure. It lists exactly four
#: items and `--scaffold` is not one of them; F.6 authorises `--scaffold` for a script that does
#: "nothing but copy repository synthetic inputs into the scaffold directory", and A.2 keeps that
#: script in the case directory. Banning the flag outright, as this tuple did until 2026-09-22,
#: was stricter than the accepted ADR and left `requires_business_file` cases with no way to
#: reach their input (M13-DEF-07). The guard is `Scaffold` below, which reads the script.
FORBIDDEN_FLAGS = ("--allow-real-servers", "--mocks off", "--publish-report")
GRANT_TOKENS = ("WebSearch", "WebFetch", "mcp__")
TOKEN_SHAPES = (r"eyJ[A-Za-z0-9_-]{10,}\.", r"\b(?:sk|pk|ghp|xox[abpr])[-_][A-Za-z0-9]{12,}",
                r"(?i)bearer\s+[A-Za-z0-9._-]{12,}", r"(?i)(api[_-]?key|secret|password|"
                r"access[_-]?token)\s*[:=]\s*['\"]?[^'\"\s]{6,}", r"\bAKIA[0-9A-Z]{16}\b")
RESERVED = re.compile(r"(^|\.)(example\.(com|org|net)|example|invalid)$")
CLOCK_WORDS = re.compile(r"(?i)\b(today|tomorrow|yesterday|right now|current (date|time))\b|"
                         r"\$\{|\$\(|%[A-Z_]+%")

#: The cases ADR-0039 E.3 names individually, by the coverage row that states each one.
#: Enumerable parts (every read-only command, every built skill, the D2 pairs) are derived
#: from the repository in the tests, never listed here.
BEHAVIOUR_BINDING = {          # coverage row -> (case id, inputs, fixture)
    "S3-01": ("b01-ambiguous-column",
              ["tests/fixtures/eval_inputs/s3_01_monthly_amounts.csv"], "EVI-01"),
    "S3-02": ("b02-critical-quality-halt",
              ["tests/fixtures/eval_inputs/s3_02_order_revenue.csv"], "EVI-02"),
    "S3-03": ("b03-short-history-forecast",
              ["tests/fixtures/eval_inputs/s3_03_monthly_revenue.csv"], "EVI-03"),
    "S3-04": ("b04-anomaly-not-fraud", [DEMO], "none"),
    "S3-05": ("b05-no-uncited-external-claim", [], "none"),
}
NAMED_CASES = {
    "d05-tier3-customer-refused": "a Tier-3 request is refused with the Tier-0 alternative",
    "d06-small-denominator-blocked": "a small-denominator aggregate is blocked",
    "d07-reidentifying-combination-blocked": "a re-identifying attribute combination is blocked",
    "d08-tier2-verbatim-halt": "a Tier-2 request halts with the verbatim text",
    "a20-overwrite-names-file": "overwriting an existing file asks and names it",
    "a21-export-names-destination": "an export off the machine asks and names the destination",
    "a22-system-write-no-path": "a system write is refused as having no path",
    "a24-git-push-never": "a git push is never performed",
    "c01-crm-pull-named-absence": "a CRM pull yields the named absence and the file alternative",
    "c02-accounting-pull-named-absence": "an accounting pull yields the named absence",
    "c03-connect-hubspot-no-auth": "connect HubSpot starts no authentication and no mcp__ call",
    "c04-record-read-blocked": "a record read is refused as blocked",
    "c05-write-no-path": "a write request is refused as having no path",
}
#: Approval-matrix rows (architecture.md section 8) whose behavioural half needs its own case.
APPROVAL_ROWS = ("S5-03", "S5-04", "S5-05", "S5-08", "S5-09", "S5-10", "S5-12")
MANIFEST_FIELDS = ("path", "builder", "sha256", "bytes", "format", "line_terminator",
                   "precondition", "why_not_demo_data", "cases", "synthetic")
FIXTURE_LIMIT = 16 * 1024


class CaseFormatError(ValueError):
    pass


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


# ---------------------------------------------------------------------------------------------
# The restricted YAML subset of docs/testing/eval-suite.md, read as text
# ---------------------------------------------------------------------------------------------

_TOP = re.compile(r"^([a-z_]+):(?: (.*))?$")
_PAIR = re.compile(r"^([a-z_]+): (.*)$")
_PLAIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./ -]*$")


def _scalar(text):
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            raise CaseFormatError("unterminated quoted scalar: %r" % text)
        inner = text[1:-1]
        if "'" in inner.replace("''", ""):
            raise CaseFormatError("unescaped quote in %r" % text)
        return inner.replace("''", "'")
    if not _PLAIN.match(text) or ": " in text or " #" in text:
        raise CaseFormatError("plain scalar outside the subset: %r" % text)
    return text


def read_case(path):
    """Parse one case file in the documented subset, or raise CaseFormatError."""
    with open(path, "rb") as handle:
        raw = handle.read()
    if b"\r" in raw:
        raise CaseFormatError("CR line terminator")
    text = raw.decode("ascii")
    if not text.endswith("\n"):
        raise CaseFormatError("no final newline")
    lines = text.split("\n")[:-1]
    data, index = {}, 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("#"):
            index += 1
            continue
        match = _TOP.match(line)
        if not match:
            raise CaseFormatError("line %d outside the subset: %r" % (index + 1, line))
        key, rest = match.group(1), match.group(2)
        if key in data:
            raise CaseFormatError("duplicate key %s" % key)
        index += 1
        if rest == "|":
            block = []
            while index < len(lines) and lines[index].startswith("  "):
                block.append(lines[index][2:])
                index += 1
            if not block:
                raise CaseFormatError("empty block scalar %s" % key)
            data[key] = "\n".join(block) + "\n"
        elif rest is None:
            if index < len(lines) and lines[index].startswith("  ") \
                    and not lines[index].startswith("  - "):
                # A nested mapping. The platform layer has two: `execution`, and `context`
                # for the scaffold ADR-0039 F.6 permits (ADR-0044; M13-DEF-07).
                if key not in NESTED_KEYS:
                    raise CaseFormatError("nested mapping outside the subset: %s" % key)
                nested = {}
                while index < len(lines) and lines[index].startswith("  ") \
                        and not lines[index].startswith("    "):
                    pair = _PAIR.match(lines[index][2:])
                    if not pair or pair.group(1) in nested:
                        raise CaseFormatError("bad nested line: %r" % lines[index])
                    inner, value = pair.group(1), pair.group(2)
                    index += 1
                    if value == "|":
                        block = []
                        while index < len(lines) and lines[index].startswith("    "):
                            block.append(lines[index][4:])
                            index += 1
                        if not block:
                            raise CaseFormatError("empty block scalar %s.%s" % (key, inner))
                        nested[inner] = "\n".join(block) + "\n"
                    else:
                        nested[inner] = _scalar(value)
                if not nested:
                    raise CaseFormatError("empty mapping %s" % key)
                data[key] = nested
                continue
            items = []
            while index < len(lines) and lines[index].startswith("  - "):
                first = lines[index][4:]
                index += 1
                if key not in ("graders", "bops_graders"):
                    items.append(_scalar(first))
                    continue
                pair = _PAIR.match(first)
                if not pair:
                    raise CaseFormatError("grader item is not a mapping: %r" % first)
                item = {pair.group(1): _scalar(pair.group(2))}
                while index < len(lines) and lines[index].startswith("    ") \
                        and not lines[index].startswith("      "):
                    pair = _TOP.match(lines[index][4:])
                    if not pair or pair.group(1) in item:
                        raise CaseFormatError("bad grader line: %r" % lines[index])
                    inner, value = pair.group(1), pair.group(2)
                    index += 1
                    if value is None:
                        nested_list = []
                        while index < len(lines) and lines[index].startswith("      - "):
                            nested_list.append(_scalar(lines[index][8:]))
                            index += 1
                        if not nested_list:
                            raise CaseFormatError("empty nested list %s" % inner)
                        item[inner] = nested_list
                    else:
                        item[inner] = _scalar(value)
                items.append(item)
            if not items:
                raise CaseFormatError("empty list %s; write []" % key)
            data[key] = items
        elif rest == "[]":
            data[key] = []
        else:
            data[key] = _scalar(rest)
    return data


def staged_cases(cases):
    """The case directories that must carry a scaffold: every `requires_business_file` case."""
    return {d for d, case in cases.items() if case["requires_business_file"] == "true"}


def case_paths():
    return sorted(glob.glob(os.path.join(EVALS, "*", "*", "case.yaml")))


def load_cases():
    cases = {}
    for path in case_paths():
        case = read_case(path)
        case["_path"] = os.path.relpath(path, REPO).replace(os.sep, "/")
        case["_dir"] = os.path.dirname(case["_path"])
        cases[case["_dir"]] = case
    return cases


#: The two repository declarations of which command owns which skill (ADR-0047 section 1).
REGISTRY = os.path.join(REPO, "lib", "python", "bops", "commands", "registry.py")
COMMANDS_DIR = os.path.join(REPO, "commands")
_LIVES_IN = re.compile(r"lives\s+in\s*`skills/(bops-[a-z-]+)/SKILL\.md`")


def registry_owners():
    """{command id: owning skill or None} from the engine registry's `CommandSpec(...)` calls.

    Read with `ast`, so the validator imports no product code.
    """
    owners = {}
    for node in ast.walk(ast.parse(_read(REGISTRY))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "CommandSpec":
            command = node.args[0].value
            skill = next((k.value.value for k in node.keywords if k.arg == "skill"), None)
            owners[command] = skill
    return owners


def declared_owners():
    """{command id: owning skill} from each command file's "lives in `skills/<skill>/SKILL.md`"."""
    owners = {}
    for path in sorted(glob.glob(os.path.join(COMMANDS_DIR, "*.md"))):
        found = _LIVES_IN.search(_read(path))
        if found:
            owners[os.path.basename(path)[:-3]] = found.group(1)
    return owners


def owning_commands():
    """{skill: [commands that own it, sorted]} (ADR-0047). The two sources cover disjoint commands."""
    registry, declared = registry_owners(), declared_owners()
    overlap = set(registry) & set(declared)
    if overlap:
        raise CaseFormatError("a command is declared in both sources: %s" % sorted(overlap))
    owned = {}
    for command, skill in sorted(list(registry.items()) + list(declared.items())):
        if skill:
            owned.setdefault(skill, []).append(command)
    return owned


def routing_input_match(skill):
    """ADR-0047: the `Skill` input's `skill` value is the skill or a command that owns it."""
    return '"skill":"businessops:(?:%s)"' % "|".join([skill] + owning_commands().get(skill, []))


def shipped_threshold_text():
    """The shipped materiality threshold as the engine prints it, e.g. `10,000` (M13-DEF-21)."""
    with open(CONFIG, encoding="utf-8") as handle:
        amount = json.load(handle)["materiality"]["absolute_amount"]
    return "{:,}".format(int(amount))


def graders_of(case, kind=None):
    """The BusinessOps semantic graders (ADR-0044's semantic layer), all 133 of them."""
    return [g for g in case["bops_graders"] if kind is None or g["kind"] == kind]


def frontmatter(path):
    text = _read(path)
    if not text.startswith("---"):
        return {}
    fields = {}
    for line in text.split("---", 2)[1].splitlines():
        if ":" in line and not line[:1].isspace():
            key, _sep, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def built_skills():
    return sorted(os.path.basename(os.path.dirname(p))
                  for p in glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md")))


def model_invocable_commands():
    names = []
    for path in sorted(glob.glob(os.path.join(REPO, "commands", "*.md"))):
        if frontmatter(path).get("disable-model-invocation", "").lower() != "true":
            names.append(os.path.splitext(os.path.basename(path))[0])
    return names


def d2_top_pairs():
    """{tier: [pair, ...]} from the 'Top three pairs' column of M13-MEAS-D2."""
    text = _read(MEASUREMENTS)
    pairs = {}
    for tier in ("Command", "Skill"):
        row = re.search(r"^\| %s \| \d+ \| \d+ \| [\d.]+ \| [\d.]+ \| (.*) \|$" % tier, text, re.M)
        found = re.findall(r"`([\w-]+)` / `([\w-]+)`", row.group(1))
        pairs[tier.lower()] = ["%s / %s" % pair for pair in found]
    return pairs


def adr_0009_questions():
    text = _read(ADR_0009)
    context = text.split("## Problem")[0]
    return re.findall(r'^- "(.+)"$', context, re.M)


def matrix_lines():
    return {line.split(" | ")[0][2:]: line for line in _read(MATRIX).splitlines()
            if re.match(r"^\| S[1-7]-\d\d \|", line)}


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def staged_copies(case):
    """[(source, destination)] a case's scaffold must copy: every input at its own path, then
    its one declared precondition fixture at its declared path (ADR-0041 section 5; ADR-0048)."""
    copies = [(path, path) for path in case["inputs"]]
    if "precondition_fixture" in case:
        entry = {e["id"]: e for e in load_manifest()["fixtures"]}[case["precondition_fixture"]]
        copies.append((entry["path"], case["precondition_path"]))
    return copies


def import_builder():
    tests_dir = os.path.join(REPO, "tests")
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    from fixtures import build_eval_inputs
    return build_eval_inputs


# ---------------------------------------------------------------------------------------------
# Layout and schema
# ---------------------------------------------------------------------------------------------

class SuiteLayout(unittest.TestCase):

    def test_the_five_suites_exist_and_nothing_else(self):
        present = sorted(n for n in os.listdir(EVALS)
                         if os.path.isdir(os.path.join(EVALS, n)) and n != RESULTS_DIR)
        self.assertEqual(present, sorted(SUITES))

    def test_no_mocks_directory_exists(self):
        self.assertFalse(os.path.exists(os.path.join(EVALS, "mocks")))

    def test_every_file_under_evals_is_a_case_file_or_its_permitted_scaffold(self):
        """One `case.yaml` per case, plus only the scaffold script A.2 and F.6 permit.

        No grader file and no mock. The harness's own `results/` output is stepped over: it
        is generated, gitignored and not a case artifact (M13-DEF-09).
        """
        for root, dirs, files in os.walk(EVALS):
            if os.path.abspath(root) == os.path.abspath(EVALS):
                dirs[:] = [d for d in dirs if d != RESULTS_DIR]
            for name in files:
                path = os.path.relpath(os.path.join(root, name), EVALS).replace(os.sep, "/")
                with self.subTest(path=path):
                    self.assertRegex(path, r"^[a-z]+/[a-z]\d\d-[a-z0-9-]+/(case\.yaml|%s)$"
                                     % re.escape(SCAFFOLD_NAME))

    def test_every_case_directory_holds_its_case_file(self):
        for suite in SUITES:
            for name in os.listdir(os.path.join(EVALS, suite)):
                with self.subTest(case=name):
                    self.assertTrue(os.path.isfile(os.path.join(EVALS, suite, name, "case.yaml")))

    def test_every_case_file_parses_in_the_documented_subset(self):
        for path in case_paths():
            with self.subTest(path=path):
                read_case(path)

    def test_the_reader_refuses_what_the_subset_excludes(self):
        """The reader is part of the validator; prove it fails closed."""
        for bad in ("key: {a: 1}\n", "key: \"double\"\n", "key: a: b\n", "  - stray\n",
                    "graders:\n  - plain\n", "key: 'open\n", "key: x\nkey: y\n", "key:\n"):
            with self.subTest(text=bad):
                handle, path = tempfile.mkstemp(suffix=".yaml")
                os.close(handle)
                try:
                    with open(path, "w", encoding="ascii", newline="\n") as out:
                        out.write(bad)
                    with self.assertRaises(CaseFormatError):
                        read_case(path)
                finally:
                    os.remove(path)


class CaseSchema(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_case_ids_are_unique_and_equal_their_directory(self):
        ids = [c["id"] for c in self.cases.values()]
        self.assertEqual(len(ids), len(set(ids)))
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(directory, "evals/%s/%s" % (case["suite"], case["id"]))
                self.assertEqual(case["id"][0], SUITES[case["suite"]])

    def test_every_required_field_and_no_other(self):
        for directory, case in self.cases.items():
            expected = set(REQUIRED_KEYS)
            if case["platform_status"] != PENDING:
                expected.add("graders")
            if case["suite"] == "routing":
                expected |= set(ROUTING_KEYS)
                if case.get("routing_kind") == "near-miss":
                    expected |= set(NEAR_MISS_KEYS)
            if case["requires_business_file"] == "true":
                expected.add("context")
            if any(key in case for key in PRECONDITION_KEYS):
                expected |= set(PRECONDITION_KEYS)
            with self.subTest(case=directory):
                self.assertEqual(set(k for k in case if not k.startswith("_")), expected)

    def test_scalar_fields_use_closed_values(self):
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(case["schema"], SCHEMA)
                self.assertIn(case["suite"], SUITES)
                self.assertIn(case["requires_business_file"], ("true", "false"))
                self.assertEqual(case["requires_business_file"] == "true", bool(case["inputs"]))
                self.assertEqual(case["ablation"],
                                 "with-without" if case["suite"] == "routing" else "none")
                self.assertEqual(tuple(case["safety"]), SAFETY)
                self.assertEqual(tuple(case["tool_grants"]), GRANTS)
                for field in ("purpose", "prompt", "expected_property"):
                    self.assertTrue(case[field].strip(), field)

    def test_components_are_real_repository_paths(self):
        for directory, case in self.cases.items():
            for path in case["components"]:
                with self.subTest(case=directory, component=path):
                    self.assertFalse(path.startswith(("/", "..")) or "\\" in path)
                    self.assertTrue(os.path.isfile(os.path.join(REPO, path)))


# ---------------------------------------------------------------------------------------------
# The platform layer: the contract read from Claude Code 2.1.278 (ADR-0044)
# ---------------------------------------------------------------------------------------------

def platform_problems(case):
    """Every way one case fails the platform's case contract. Empty when it satisfies it."""
    problems = []
    version = case.get("schema_version")
    if not isinstance(version, str) or not version:
        problems.append("missing required field schema_version")
    else:
        major = version.split(".")[0]
        if not major.isdigit():
            problems.append("schema_version %r is not a valid version string" % version)
        elif int(major) > 1:
            problems.append("schema_version %r requires a newer Claude Code" % version)
    if not case.get("name"):
        problems.append("missing required field name")
    execution = case.get("execution")
    if not isinstance(execution, dict):
        problems.append("missing required field execution")
    elif not (execution.get("prompt") or "").strip():
        problems.append("execution.prompt is required")
    graders = case.get("graders")
    if case.get("platform_status") == PENDING:
        # Its every grader awaits the trace tool name, so it carries none: the platform needs at
        # least one, and inventing one is exactly what ADR-0044 stage 2 exists to prevent.
        if graders is not None:
            problems.append("a pending case must carry no platform grader")
        return problems
    if not isinstance(graders, list) or not graders:
        problems.append("graders must hold at least one grader")
        return problems
    seen = set()
    for grader in graders:
        kind, name = grader.get("type"), grader.get("name")
        if kind not in PLATFORM_GRADERS:
            problems.append("unsupported grader type %r" % kind)
            continue
        if not name:
            problems.append("grader has no name")
        elif name in seen:
            problems.append('duplicate grader name "%s"' % name)
        seen.add(name)
        spec = PLATFORM_GRADERS[kind]
        for key in spec["required"]:
            if key not in grader:
                problems.append('grader "%s" is missing %s' % (name, key))
        for key in grader:
            if key not in spec["required"] + spec["optional"]:
                problems.append('grader "%s" has unknown key %s (the type is strict)' %
                                (name, key))
        if kind == "regex":
            if grader.get("target", "last_message") not in PLATFORM_TARGETS:
                problems.append('grader "%s" targets %r' % (name, grader.get("target")))
            match = grader.get("match", "contains")
            if match not in PLATFORM_MATCHES and not re.match(r"^count:\d+$", match):
                problems.append('grader "%s" has match %r' % (name, match))
            if not re.match(r"^[dgimsuvy]*$", grader.get("flags", "")):
                problems.append('grader "%s" has flags %r' % (name, grader.get("flags")))
            pattern = grader.get("pattern", "")
            if re.match(r"^\(\?[a-zA-Z]+\)", pattern):
                problems.append('grader "%s" uses an inline flag group, which JS RegExp rejects'
                                % name)
            try:
                re.compile(pattern)
            except re.error as error:
                problems.append('grader "%s" pattern does not compile: %s' % (name, error))
        if kind == "tool_used":
            # The platform compares the tool name with ===, so a pattern can never match.
            if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", grader.get("tool", "")):
                problems.append('grader "%s" tool %r is not an exact tool name'
                                % (name, grader.get("tool")))
            for bound in ("min", "max"):
                if bound in grader and not str(grader[bound]).isdigit():
                    problems.append('grader "%s" %s is not a non-negative integer' % (name, bound))
        if "arm" in grader and grader["arm"] not in ("with-only", "both"):
            problems.append('grader "%s" arm %r' % (name, grader["arm"]))
    return problems


class PlatformLayer(unittest.TestCase):
    """ADR-0044 Phase 1. Static translation only: nothing here has ever been executed."""

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_every_case_satisfies_the_platform_contract(self):
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(platform_problems(case), [])

    def test_the_platform_identity_is_derived_from_the_case_identity(self):
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(case["name"], case["id"])
                self.assertEqual(case["schema_version"], SCHEMA_VERSION)
                self.assertIn(case["platform_status"], PLATFORM_STATUSES)

    def test_a_raised_turn_budget_is_confined_to_the_availability_completion_cases(self):
        """2026-09-26: the ten routing cases the 34-case re-evaluation could not complete carry
        `execution.max_turns: 20`, the platform's own field (integer, at most 200); no other case
        changes its default of 10, and no prompt or grader changes with it."""
        raised = {c: "20" for c in ("r02", "r03", "r04", "r05", "r06", "r07", "r08", "r09",
                                    "r15", "r16")}
        for directory, case in self.cases.items():
            value = case["execution"].get("max_turns")
            with self.subTest(case=directory):
                self.assertEqual(value, raised.get(case["id"][:3]))
                if value is not None:
                    self.assertTrue(value.isdigit() and 1 <= int(value) <= 200)
                    self.assertEqual(set(case["execution"]), {"prompt", "max_turns"})

    def test_the_platform_prompt_is_the_case_prompt_unchanged(self):
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(case["execution"]["prompt"], case["prompt"])

    def test_no_case_is_pending_and_every_case_carries_a_platform_grader(self):
        """ADR-0044 stage 3, 2026-09-22: the pending boundary is closed. 64 of 64 load."""
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(case["platform_status"], "loadable")
                self.assertTrue(case.get("graders"), "a loadable case needs a platform grader")

    def test_a_pending_case_would_still_be_refused_if_one_returned(self):
        """The PENDING machinery is unused, not removed. Prove it still fails closed."""
        case = dict(next(iter(self.cases.values())))
        case["platform_status"] = PENDING
        self.assertIn("a pending case must carry no platform grader", platform_problems(case))

    def test_the_command_mapping_is_the_one_the_pilot_observed(self):
        """Every command grader maps to the observed identifier, and to nothing invented.

        The absence graders carry `min: 0` as well as `max: 0` deliberately. The platform
        evaluates a `tool_used` grader as `min = e.min ?? 1`, `max = e.max ?? Infinity`,
        `passed = count >= min && count <= max`. With `max: 0` and no `min` the expected range is
        1..0, which no count can satisfy, so such a grader could never pass whatever the agent did.
        """
        seen = 0
        for directory, case in self.cases.items():
            by_name = {g["name"]: g for g in case.get("graders", [])}
            for grader in case["bops_graders"]:
                if grader["check"] not in ("command_invoked", "command_not_invoked"):
                    continue
                seen += 1
                produced = by_name[grader["platform_graders"][0]]
                with self.subTest(case=directory, grader=grader["id"]):
                    self.assertEqual(produced["type"], "tool_used")
                    self.assertEqual(produced["tool"], OBSERVED_COMMAND_TOOL)
                    self.assertEqual(produced["input_match"],
                                     OBSERVED_COMMAND_PREFIX + grader["command"])
                    if grader["check"] == "command_not_invoked":
                        self.assertEqual((produced.get("min"), produced.get("max")), ("0", "0"))
                    else:
                        self.assertEqual(produced.get("min"), "1")
                        self.assertNotIn("max", produced)
        self.assertEqual(seen, 24)

    def test_every_semantic_grader_declares_its_mapping_and_none_is_dropped(self):
        for directory, case in self.cases.items():
            names = {g["name"] for g in case.get("graders", [])}
            for grader in case["bops_graders"]:
                with self.subTest(case=directory, grader=grader["id"]):
                    mapping = grader.get("platform_mapping")
                    self.assertIn(mapping, ("mapped", PENDING))
                    if mapping == PENDING:
                        self.assertIn(grader["check"], PENDING_CHECKS)
                        self.assertTrue(grader.get("pending_reason", "").strip())
                        self.assertNotIn("platform_graders", grader)
                    else:
                        self.assertNotIn(grader["check"], PENDING_CHECKS)
                        self.assertTrue(grader.get("platform_graders"))
                        for name in grader["platform_graders"]:
                            self.assertIn(name, names)

    def test_every_platform_grader_is_claimed_by_exactly_one_semantic_grader(self):
        for directory, case in self.cases.items():
            claimed = [n for g in case["bops_graders"] for n in g.get("platform_graders", [])]
            with self.subTest(case=directory):
                self.assertEqual(sorted(claimed),
                                 sorted(g["name"] for g in case.get("graders", [])))
                self.assertEqual(len(claimed), len(set(claimed)))

    def test_the_translation_preserves_negative_and_positive_semantics(self):
        for directory, case in self.cases.items():
            by_name = {g["name"]: g for g in case.get("graders", [])}
            for grader in case["bops_graders"]:
                if grader.get("platform_mapping") != "mapped":
                    continue
                negative = grader["check"] in ("skill_not_invoked", "tool_not_invoked",
                                               "agent_not_dispatched", "response_not_matches",
                                               "command_not_invoked")
                for name in grader["platform_graders"]:
                    produced = by_name[name]
                    with self.subTest(case=directory, grader=name):
                        if produced["type"] == "tool_used":
                            asserts_absence = produced.get("max") == "0"
                        else:
                            asserts_absence = produced.get("match") == "not_contains"
                        self.assertEqual(asserts_absence, negative)

    def test_an_llm_grader_carries_its_criteria_verbatim(self):
        for directory, case in self.cases.items():
            by_name = {g["name"]: g for g in case.get("graders", [])}
            for grader in case["bops_graders"]:
                if grader["check"] != "llm_judgement":
                    continue
                with self.subTest(case=directory, grader=grader["id"]):
                    self.assertEqual(by_name[grader["platform_graders"][0]]["criteria"],
                                     grader["criteria"])

    def test_a_translated_pattern_keeps_its_meaning(self):
        """`(?i)` becomes flags: i, because JS RegExp has no inline flag group."""
        for directory, case in self.cases.items():
            by_name = {g["name"]: g for g in case.get("graders", [])}
            for grader in case["bops_graders"]:
                if grader["check"] not in ("response_matches", "response_not_matches"):
                    continue
                produced = by_name[grader["platform_graders"][0]]
                with self.subTest(case=directory, grader=grader["id"]):
                    if grader["pattern"].startswith("(?i)"):
                        self.assertEqual(produced["flags"], "i")
                        self.assertEqual(produced["pattern"], grader["pattern"][4:])
                    else:
                        self.assertNotIn("flags", produced)
                        self.assertEqual(produced["pattern"], grader["pattern"])
                    self.assertEqual(produced["target"], "last_message")

    def test_no_platform_grader_claims_an_execution_result(self):
        for directory, case in self.cases.items():
            for grader in case.get("graders", []):
                with self.subTest(case=directory, grader=grader["name"]):
                    self.assertNotIn("expected_outcome", grader)
                    self.assertNotIn("weight", grader)


class PlatformContractIsEnforced(unittest.TestCase):
    """Negative coverage: each defect the platform rejects is caught by `platform_problems`."""

    @staticmethod
    def valid():
        return {"schema_version": "1.0", "name": "a01", "platform_status": "loadable",
                "execution": {"prompt": "do the thing\n"},
                "graders": [{"type": "llm", "name": "g-one", "criteria": "is it right?"}]}

    def assert_rejected(self, mutate, fragment):
        case = self.valid()
        mutate(case)
        problems = platform_problems(case)
        self.assertTrue(problems, "mutation was accepted")
        self.assertTrue(any(fragment in p for p in problems), problems)

    def test_the_baseline_case_is_accepted(self):
        self.assertEqual(platform_problems(self.valid()), [])

    def test_missing_schema_version_is_rejected(self):
        self.assert_rejected(lambda c: c.pop("schema_version"), "schema_version")

    def test_a_non_version_schema_version_is_rejected(self):
        self.assert_rejected(lambda c: c.update(schema_version="one"), "not a valid version")

    def test_a_future_schema_version_is_rejected(self):
        self.assert_rejected(lambda c: c.update(schema_version="2.0"), "newer Claude Code")

    def test_missing_name_is_rejected(self):
        self.assert_rejected(lambda c: c.pop("name"), "name")

    def test_missing_execution_is_rejected(self):
        self.assert_rejected(lambda c: c.pop("execution"), "execution")

    def test_an_empty_execution_prompt_is_rejected(self):
        self.assert_rejected(lambda c: c.update(execution={"prompt": "   \n"}),
                             "execution.prompt is required")

    def test_missing_graders_is_rejected(self):
        self.assert_rejected(lambda c: c.pop("graders"), "at least one grader")

    def test_an_empty_grader_list_is_rejected(self):
        self.assert_rejected(lambda c: c.update(graders=[]), "at least one grader")

    def test_an_unsupported_grader_type_is_rejected(self):
        self.assert_rejected(lambda c: c["graders"][0].update(type="command_invoked"),
                             "unsupported grader type")

    def test_a_malformed_grader_is_rejected(self):
        self.assert_rejected(lambda c: c["graders"][0].pop("criteria"), "is missing criteria")

    def test_an_unknown_grader_key_is_rejected(self):
        self.assert_rejected(lambda c: c["graders"][0].update(property="a property"),
                             "unknown key property")

    def test_duplicate_grader_names_are_rejected(self):
        self.assert_rejected(
            lambda c: c["graders"].append({"type": "llm", "name": "g-one", "criteria": "x"}),
            "duplicate grader name")

    def test_a_regex_tool_name_is_rejected(self):
        self.assert_rejected(
            lambda c: c.update(graders=[{"type": "tool_used", "name": "g",
                                         "tool": "^(WebSearch|WebFetch)$"}]),
            "is not an exact tool name")

    def test_an_inline_flag_group_is_rejected(self):
        self.assert_rejected(
            lambda c: c.update(graders=[{"type": "regex", "name": "g", "pattern": "(?i)hello"}]),
            "inline flag group")

    def test_a_pending_case_carrying_a_platform_grader_is_rejected(self):
        self.assert_rejected(lambda c: c.update(platform_status=PENDING),
                             "must carry no platform grader")


class MigrationManifest(unittest.TestCase):
    """ADR-0044 Phase 1's audit trail: 109 mapped + 24 pending = 133, and nothing dropped."""

    @classmethod
    def setUpClass(cls):
        with open(MIGRATION_MAP, encoding="utf-8") as handle:
            cls.manifest = json.load(handle)
        cls.cases = load_cases()

    def test_the_totals_add_up_and_nothing_was_dropped(self):
        totals = self.manifest["totals"]
        self.assertEqual(totals["mapped"] + totals["pending_trace_mapping"],
                         totals["original_graders"])
        self.assertEqual(totals["original_graders"], 133)
        # ADR-0044 stage 3, 2026-09-22: all 133 mapped, none pending, none dropped.
        self.assertEqual(totals["mapped"], 133)
        self.assertEqual(totals["pending_trace_mapping"], 0)
        self.assertEqual(totals["cases_loadable"], 64)
        self.assertEqual(totals["cases_pending_trace_mapping"], 0)
        self.assertEqual(totals["dropped"], 0)
        self.assertEqual(totals["cases_loadable"] + totals["cases_pending_trace_mapping"], 64)

    def test_the_manifest_totals_match_the_case_files(self):
        mapped = pending = emitted = 0
        for case in self.cases.values():
            emitted += len(case.get("graders", []))
            for grader in case["bops_graders"]:
                if grader.get("platform_mapping") == "mapped":
                    mapped += 1
                else:
                    pending += 1
        totals = self.manifest["totals"]
        self.assertEqual((mapped, pending, emitted),
                         (totals["mapped"], totals["pending_trace_mapping"],
                          totals["platform_graders_emitted"]))

    def test_every_case_and_every_grader_appears_exactly_once(self):
        listed = [entry["case"] for entry in self.manifest["cases"]]
        self.assertEqual(sorted(listed), sorted(c["_path"] for c in self.cases.values()))
        self.assertEqual(len(listed), len(set(listed)))
        for entry in self.manifest["cases"]:
            case = self.cases[os.path.dirname(entry["case"])]
            with self.subTest(case=entry["case"]):
                self.assertEqual([row["original_id"] for row in entry["graders"]],
                                 [g["id"] for g in case["bops_graders"]])
                self.assertEqual(entry["platform_status"], case["platform_status"])

    def test_every_mapping_row_matches_the_case_file(self):
        for entry in self.manifest["cases"]:
            case = self.cases[os.path.dirname(entry["case"])]
            by_id = {g["id"]: g for g in case["bops_graders"]}
            for row in entry["graders"]:
                grader = by_id[row["original_id"]]
                with self.subTest(case=entry["case"], grader=row["original_id"]):
                    self.assertEqual(row["mapping"], grader["platform_mapping"])
                    self.assertEqual(row["check"], grader["check"])
                    self.assertEqual(row["platform_graders"],
                                     grader.get("platform_graders", []))

    def test_the_manifest_claims_no_execution(self):
        text = json.dumps(self.manifest).lower()
        for word in ("automated_pass", "passed", "scored", "verified"):
            self.assertNotIn(word, text.replace("has ever been scored", ""))


# ---------------------------------------------------------------------------------------------
# Inventory: ADR-0039 E.3, reconciled against the repository
# ---------------------------------------------------------------------------------------------

class Inventory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()
        cls.by_id = {c["id"]: c for c in cls.cases.values()}

    def in_suite(self, suite):
        return [c for c in self.cases.values() if c["suite"] == suite]

    def with_row(self, row, suite=None):
        return [c for c in self.cases.values()
                if row in c["coverage_rows"] and (suite is None or c["suite"] == suite)]

    def check_values(self, case, check):
        return [g.get("skill") or g.get("command") for g in case["bops_graders"]
                if g["check"] == check]

    def test_each_behaviour_row_has_exactly_its_case(self):
        self.assertEqual(len(self.in_suite("behaviour")), len(BEHAVIOUR_BINDING))
        for row, (case_id, _inputs, _fixture) in BEHAVIOUR_BINDING.items():
            with self.subTest(row=row):
                self.assertEqual([c["id"] for c in self.with_row(row, "behaviour")], [case_id])

    def test_the_individually_named_cases_exist(self):
        for case_id, requirement in NAMED_CASES.items():
            with self.subTest(case=case_id, requirement=requirement):
                self.assertIn(case_id, self.by_id)

    def test_the_four_adr_0009_questions_are_each_asked_once_verbatim(self):
        questions = adr_0009_questions()
        self.assertEqual(len(questions), 4)
        comparative = self.with_row("S3-07", "disclosure")
        self.assertEqual(len(comparative), 4)
        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(len([c for c in comparative if question in c["prompt"]]), 1)

    def test_every_read_only_command_has_one_no_approval_case(self):
        """Every model-invocable command in the section 8 read-only class. The executive
        report is draft generation (S5-03) and has its own case."""
        commands = [c for c in model_invocable_commands() if c != "executive-report"]
        cases = self.with_row("S5-01", "approval")
        ran = sorted(v for c in cases for v in self.check_values(c, "command_invoked"))
        self.assertEqual(ran, sorted(commands))
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertIn("S3-11", case["coverage_rows"])
                self.assertEqual(len(graders_of(case, "llm")), 1)

    def test_every_behavioural_approval_row_has_a_case(self):
        for row in APPROVAL_ROWS:
            with self.subTest(row=row):
                self.assertTrue(self.with_row(row, "approval"))
        draft = self.with_row("S5-03", "approval")
        self.assertEqual([v for c in draft for v in self.check_values(c, "command_invoked")],
                         ["executive-report"])

    def test_the_connector_suite_covers_absence_authentication_read_and_write(self):
        connectors = self.in_suite("connectors")
        self.assertTrue(all("S3-06" in c["coverage_rows"] for c in connectors))
        for case in connectors:
            with self.subTest(case=case["id"]):
                tools = [g["tool"] for g in case["bops_graders"]
                         if g["check"] == "tool_not_invoked"]
                self.assertIn(r"^mcp__.+$", tools, "every connector case forbids every mcp__ tool")

    def test_one_positive_routing_case_per_built_model_invocable_skill(self):
        skills = built_skills()
        self.assertEqual(len(skills), 16)
        for skill in skills:
            self.assertNotEqual(frontmatter(os.path.join(REPO, "skills", skill, "SKILL.md"))
                                .get("disable-model-invocation", "").lower(), "true", skill)
        positives = [c for c in self.in_suite("routing") if c["routing_kind"] == "positive"]
        fired = sorted(v for c in positives for v in self.check_values(c, "skill_invoked"))
        self.assertEqual(fired, skills)
        for case in positives:
            with self.subTest(case=case["id"]):
                self.assertEqual([g["check"] for g in case["bops_graders"]], ["skill_invoked"])

    def test_the_six_near_misses_are_the_d2_top_three_pairs_per_tier(self):
        top = d2_top_pairs()
        self.assertEqual({t: len(p) for t, p in top.items()}, {"command": 3, "skill": 3})
        near = [c for c in self.in_suite("routing") if c["routing_kind"] == "near-miss"]
        found = sorted((c["overlap_tier"], c["overlap_pair"]) for c in near)
        self.assertEqual(found, sorted((t, p) for t, pairs in top.items() for p in pairs))
        commands, skills = model_invocable_commands(), built_skills()
        for case in near:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["overlap_source"], "M13-MEAS-D2")
                members = case["overlap_pair"].split(" / ")
                key = "command" if case["overlap_tier"] == "command" else "skill"
                fired = self.check_values(case, "%s_invoked" % key)
                silent = self.check_values(case, "%s_not_invoked" % key)
                self.assertEqual(len(fired), 1)
                self.assertEqual(silent, [case["competing_component"]])
                self.assertEqual(sorted(fired + silent), sorted(members))
                for member in members:
                    self.assertIn(member, commands if key == "command" else skills)

    def test_routing_rows_and_kinds(self):
        for case in self.in_suite("routing"):
            with self.subTest(case=case["id"]):
                self.assertIn(case["routing_kind"], ("positive", "near-miss"))
                self.assertEqual(case["coverage_rows"], ["S3-12"])


# ---------------------------------------------------------------------------------------------
# Inputs: ADR-0039 E.5 as amended by ADR-0041 sections 5 and 8
# ---------------------------------------------------------------------------------------------

class Inputs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_every_input_exists_under_an_admitted_root(self):
        for directory, case in self.cases.items():
            for path in case["inputs"]:
                with self.subTest(case=directory, input=path):
                    self.assertTrue(path.startswith(INPUT_ROOTS), path)
                    self.assertNotIn("..", path.split("/"))
                    self.assertNotIn("\\", path)
                    self.assertTrue(os.path.isfile(os.path.join(REPO, path)))

    def test_no_case_names_a_builder_manifest_or_attributes_file(self):
        for directory, case in self.cases.items():
            for path in case["inputs"]:
                with self.subTest(case=directory, input=path):
                    self.assertTrue(path.endswith(".csv"))
                    self.assertNotIn(os.path.basename(path),
                                     ("manifest.json", ".gitattributes", "build_eval_inputs.py"))

    def test_inputs_are_named_both_ways_in_the_prompt(self):
        """A case consumes what it names, and names what it consumes (ADR-0041 section 5)."""
        for directory, case in self.cases.items():
            mentioned = sorted(set(re.findall(r"(?:assets|tests|evals)/[\w./-]*\w",
                                              case["prompt"])))
            with self.subTest(case=directory):
                self.assertEqual(mentioned, sorted(case["inputs"]))

    def test_the_behaviour_bindings(self):
        """S3-01 to S3-03 on their ADR-0041 fixtures, S3-04 on the demo file, S3-05 on none."""
        by_id = {c["id"]: c for c in self.cases.values()}
        for row, (case_id, inputs, fixture) in BEHAVIOUR_BINDING.items():
            case = by_id[case_id]
            with self.subTest(row=row):
                self.assertEqual(case["inputs"], inputs)
                self.assertEqual(case["fixture"], fixture)
        self.assertEqual(by_id["b05-no-uncited-external-claim"]["requires_business_file"], "false")

    def test_only_the_three_behaviour_cases_use_a_fixture(self):
        for directory, case in self.cases.items():
            uses = [p for p in case["inputs"] if p.startswith("tests/")]
            with self.subTest(case=directory):
                if case["fixture"] == "none":
                    self.assertEqual(uses, [])
                else:
                    self.assertEqual(case["suite"], "behaviour")
                    self.assertEqual(len(uses), 1)


# ---------------------------------------------------------------------------------------------
# Safety: ADR-0039 E.5 assertions three to five, F.3 to F.6 and F.11
# ---------------------------------------------------------------------------------------------

class Safety(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()
        cls.texts = {p: _read(os.path.join(REPO, p)) for p in (c["_path"] for c in cls.cases.values())}

    def documents(self):
        """Every case file, plus the document that describes how to run the suite."""
        documents = dict(self.texts)
        documents["docs/testing/eval-suite.md"] = _read(PROCEDURE)
        return documents

    def test_no_prohibited_flag_in_a_case_or_the_procedure(self):
        for path, text in self.documents().items():
            for flag in FORBIDDEN_FLAGS:
                with self.subTest(path=path, flag=flag):
                    self.assertNotIn(flag, text)

    def test_the_procedure_grants_nothing_beyond_the_engine(self):
        text = _read(PROCEDURE)
        for token in GRANT_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_web_and_mcp_tool_names_appear_only_as_prohibitions(self):
        """No grant: the names may appear only in a tool_not_invoked grader's tool pattern."""
        for directory, case in self.cases.items():
            for token in GRANT_TOKENS:
                with self.subTest(case=directory, token=token):
                    for field in ("tool_grants", "prompt", "purpose", "expected_property"):
                        self.assertNotIn(token, str(case[field]))
                    for grader in case["bops_graders"]:
                        for key, value in grader.items():
                            if token in value:
                                self.assertEqual((grader["check"], key),
                                                 ("tool_not_invoked", "tool"))

    def test_no_url_or_address_outside_the_reserved_domains(self):
        for path, text in self.documents().items():
            hosts = re.findall(r"https?://([^/\s'\"<>)]+)", text)
            hosts += re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", text)
            for host in hosts:
                with self.subTest(path=path, host=host):
                    self.assertRegex(host.lower(), RESERVED)

    def test_no_token_shaped_string(self):
        for path, text in self.documents().items():
            for shape in TOKEN_SHAPES:
                with self.subTest(path=path, shape=shape):
                    self.assertIsNone(re.search(shape, text))

    def test_no_absolute_or_home_path(self):
        pattern = re.compile(r"(?i)\b[a-z]:[\\/]|(^|\s)/(home|users|etc|tmp)/|~/|\.\./")
        for path, text in self.texts.items():
            with self.subTest(path=path):
                self.assertIsNone(pattern.search(text))

    def test_nothing_depends_on_the_clock_or_the_environment(self):
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertIsNone(CLOCK_WORDS.search(case["prompt"]))


# ---------------------------------------------------------------------------------------------
# Scaffold: the assertion ADR-0039 F.6 asks E.5 to make
# ---------------------------------------------------------------------------------------------

class Scaffold(unittest.TestCase):
    """F.6: a scaffold script does "nothing but copy repository synthetic inputs into the
    scaffold directory", and "E.5 reads every scaffold script and asserts this".

    Claude Code 2.1.278 runs it as `bash <script>` with the working directory set to the run's
    own directory, so copying an input to its repository-relative path is what makes the path a
    prompt names resolve inside the sandbox. This class reads the script and starts no process;
    the execution proof is `integration.test_m13_eval_scaffold`.
    """

    #: Every line a scaffold may hold, past comments and blanks. Anything else fails, so the
    #: script cannot grow an interpreter, a network call or a write outside the run directory
    #: without this test rejecting it.
    PERMITTED = (
        re.compile(r"^set -eu$"),
        re.compile(r'^repo=\$\(cd "\$\(dirname "\$0"\)(?:/\.\.)+" && pwd\)$'),
        re.compile(r"^mkdir -p (?P<made>[\w][\w./-]*)$"),
        re.compile(r'^cp "\$repo/(?P<src>[\w][\w./-]*)" (?P<dst>[\w][\w./-]*)$'),
    )

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def declared(self):
        """{case directory: script text} for every case that declares a scaffold."""
        out = {}
        for directory in sorted(staged_cases(self.cases)):
            name = self.cases[directory]["context"]["scaffold_script"]
            out[directory] = _read(os.path.join(REPO, directory, name))
        return out

    def effective(self, text):
        return [line for line in text.split("\n") if line.strip() and not line.startswith("#")]

    def test_a_case_declares_a_scaffold_if_and_only_if_it_needs_a_business_file(self):
        """The invariant that replaced the hand-kept list. Both directions are asserted."""
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual("context" in case, case["requires_business_file"] == "true")
        staged = staged_cases(self.cases)
        self.assertEqual(len(staged), BUSINESS_FILE_COUNT)
        missing = sorted(d for d in staged
                         if not os.path.isfile(os.path.join(REPO, d, SCAFFOLD_NAME)))
        self.assertEqual(missing, [], "business-file cases with no scaffold on disk")

    def test_each_declared_scaffold_uses_the_one_permitted_name_and_exists(self):
        for directory in sorted(staged_cases(self.cases)):
            context = self.cases[directory]["context"]
            with self.subTest(case=directory):
                self.assertEqual(set(context), {"scaffold_script"})
                self.assertEqual(context["scaffold_script"], SCAFFOLD_NAME)
                self.assertTrue(os.path.isfile(os.path.join(REPO, directory, SCAFFOLD_NAME)))

    def test_no_scaffold_file_exists_that_no_case_declares(self):
        found = sorted(os.path.dirname(os.path.relpath(path, REPO)).replace(os.sep, "/")
                       for path in glob.glob(os.path.join(EVALS, "*", "*", SCAFFOLD_NAME)))
        self.assertEqual(found, sorted(staged_cases(self.cases)))

    def test_every_line_is_one_of_the_permitted_forms(self):
        """The F.6 assertion: the script does nothing but copy repository synthetic inputs."""
        for directory, text in self.declared().items():
            for line in self.effective(text):
                with self.subTest(case=directory, line=line):
                    self.assertTrue(any(form.match(line) for form in self.PERMITTED),
                                    "line is outside the permitted forms: %r" % line)

    def test_it_copies_exactly_the_inputs_its_case_declares_to_the_same_paths(self):
        """Two-way, as ADR-0041 section 5 does for inputs: what it stages is what the case names."""
        for directory, text in self.declared().items():
            copied = []
            for line in self.effective(text):
                match = self.PERMITTED[3].match(line)
                if match:
                    copied.append((match.group("src"), match.group("dst")))
            with self.subTest(case=directory):
                # Every input at the path the prompt names; a declared precondition fixture, and
                # only that, at its declared path (ADR-0048). Nothing else.
                self.assertEqual(copied, staged_copies(self.cases[directory]))
                for source, _destination in copied:
                    self.assertTrue(source.startswith(INPUT_ROOTS))
                    self.assertTrue(os.path.isfile(os.path.join(REPO, source)))

    def test_every_directory_it_makes_holds_something_it_copies(self):
        for directory, text in self.declared().items():
            lines = self.effective(text)
            made = [m.group("made") for m in
                    (self.PERMITTED[2].match(line) for line in lines) if m]
            copied = [m.group("dst") for m in
                      (self.PERMITTED[3].match(line) for line in lines) if m]
            for path in made:
                with self.subTest(case=directory, made=path):
                    self.assertTrue(any(d.startswith(path + "/") for d in copied))

    def test_it_holds_no_absolute_path_no_grant_token_and_no_url(self):
        pattern = re.compile(r"(?i)\b[a-z]:[\\/]|(^|\s)/(home|users|etc|tmp|usr|bin)/|~/")
        for directory, text in self.declared().items():
            with self.subTest(case=directory):
                self.assertIsNone(pattern.search(text))
                for token in GRANT_TOKENS:
                    self.assertNotIn(token, text)
                self.assertNotIn("http", text)

    def test_it_is_ascii_with_unix_line_endings_and_a_final_newline(self):
        for directory in sorted(staged_cases(self.cases)):
            path = os.path.join(REPO, directory, SCAFFOLD_NAME)
            with self.subTest(case=directory):
                with open(path, "rb") as handle:
                    raw = handle.read()
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))
                raw.decode("ascii")

    def test_no_business_file_case_is_left_unable_to_reach_its_input(self):
        """M13-DEF-07's scope is closed: every business-file case stages its own fixture."""
        waiting = sorted(d for d, c in self.cases.items()
                         if c["requires_business_file"] == "true" and "context" not in c)
        self.assertEqual(waiting, [])

    def test_every_scaffold_stages_its_own_declared_input_and_that_input_exists(self):
        """No scaffold may stage a fixture its case did not declare, or one that is not there."""
        for directory, text in self.declared().items():
            copied = [match.group("src") for match in
                      (self.PERMITTED[3].match(line) for line in self.effective(text)) if match]
            with self.subTest(case=directory):
                self.assertEqual(copied, [s for s, _d in staged_copies(self.cases[directory])])
                for source in copied[:len(self.cases[directory]["inputs"])]:
                    self.assertTrue(source.startswith(INPUT_ROOTS), source)
                    self.assertTrue(os.path.isfile(os.path.join(REPO, source)), source)
                    # The prompt names the same relative path, so staging makes it resolve.
                    self.assertIn(source, self.cases[directory]["prompt"])


# ---------------------------------------------------------------------------------------------
# Graders: ADR-0039 E.4
# ---------------------------------------------------------------------------------------------

class Graders(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_grader_ids_are_unique_within_a_case(self):
        for directory, case in self.cases.items():
            ids = [g["id"] for g in case["bops_graders"]]
            with self.subTest(case=directory):
                self.assertEqual(len(ids), len(set(ids)))

    def test_deterministic_graders_use_the_closed_vocabulary(self):
        for directory, case in self.cases.items():
            for grader in graders_of(case, "deterministic"):
                with self.subTest(case=directory, grader=grader["id"]):
                    self.assertIn(grader["check"], DETERMINISTIC_CHECKS)
                    for field in DETERMINISTIC_CHECKS[grader["check"]]:
                        self.assertTrue(grader.get(field), field)
                    self.assertTrue(set(grader) <= set(GRADER_KEYS))
                    self.assertNotIn("criteria", grader)
                    self.assertNotIn("why_not_deterministic", grader)
                    if "target" in grader:
                        self.assertIn(grader["target"], TARGETS)
                    self.assertTrue(grader["property"].strip())

    def test_every_pattern_compiles(self):
        for directory, case in self.cases.items():
            for grader in graders_of(case, "deterministic"):
                for field in ("pattern", "tool"):
                    if field in grader:
                        with self.subTest(case=directory, grader=grader["id"], field=field):
                            re.compile(grader[field])

    def test_every_llm_grader_says_why_it_is_not_deterministic(self):
        for directory, case in self.cases.items():
            for grader in graders_of(case, "llm"):
                with self.subTest(case=directory, grader=grader["id"]):
                    self.assertEqual(grader["check"], "llm_judgement")
                    self.assertEqual(set(grader), {"id", "kind", "check", "property", "criteria",
                                                   "why_not_deterministic",
                                                   "platform_mapping", "platform_graders"})
                    self.assertGreaterEqual(len(grader["why_not_deterministic"]), 80)
                    self.assertIn("?", grader["criteria"])
                    self.assertRegex(grader["criteria"], r"Answer (yes|no)")

    def test_every_case_has_a_deterministic_grader(self):
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertTrue(graders_of(case, "deterministic"))

    def test_kinds_are_closed(self):
        for directory, case in self.cases.items():
            for grader in case["bops_graders"]:
                with self.subTest(case=directory, grader=grader["id"]):
                    self.assertIn(grader["kind"], ("deterministic", "llm"))

    def test_no_score_rank_weight_or_threshold_is_declared(self):
        for path in case_paths():
            text = _read(path)
            for word in ("score", "rank", "weight", "threshold", "severity", "priority"):
                with self.subTest(path=path, word=word):
                    self.assertIsNone(re.search(r"(?im)^\s*(- )?%s\w*:" % word, text))

    def test_no_answer_key_from_a_product_run(self):
        """A number a grader asserts on comes from the case's own prompt, never from a run.

        Any run of three or more digits in a grader's pattern or criteria (ADR ids aside) must
        appear in the prompt, and no grader carries a two-decimal amount. The two small counts in b03 are checked against their
        sources in `test_the_forecast_requirement_is_the_shipped_default`. The one other shipped
        value, the materiality threshold a figure grader excludes (M13-DEF-21), is exempt only in
        its exclusion form and is bound to its source in
        `test_the_figure_exclusion_is_the_shipped_materiality_threshold`.
        """
        exclusion = "(?!%s" % shipped_threshold_text()
        for directory, case in self.cases.items():
            for grader in case["bops_graders"]:
                text = " ".join(grader.get(k, "") for k in ("pattern", "criteria"))
                text = re.sub(r"ADR-\d{4}", "", text).replace(exclusion, "(?!")
                with self.subTest(case=directory, grader=grader["id"]):
                    self.assertIsNone(re.search(r"\d+\.\d\d\b", text))
                    for digits in re.findall(r"\d{3,}", text):
                        self.assertIn(digits, case["prompt"])

    def test_the_figure_exclusion_is_the_shipped_materiality_threshold(self):
        """M13-DEF-21: a figure grader may exclude the configured threshold and nothing else.

        The excluded literal is the shipped `materiality.absolute_amount`, formatted as the
        engine prints it, so a changed default fails here rather than silently widening or
        narrowing what the grader forgives.
        """
        exclusion = "(?!%s" % shipped_threshold_text()
        for directory, case in self.cases.items():
            for grader in case["bops_graders"] + case.get("graders", []):
                pattern = grader.get("pattern", "")
                with self.subTest(case=directory, grader=grader.get("id") or grader.get("name")):
                    for found in re.findall(r"\(\?!(\d[\d,]*)", pattern):
                        self.assertEqual("(?!" + found, exclusion)
        with open(CONFIG, encoding="utf-8") as handle:
            minimum = json.load(handle)["forecast"]["min_history_periods"]
        case = load_cases()["evals/behaviour/b03-short-history-forecast"]
        graders = {g["id"]: g for g in case["bops_graders"]}
        required = re.compile(graders["g-states-periods-required"]["pattern"])
        available = re.compile(graders["g-states-periods-available"]["pattern"])
        self.assertRegex("%d periods are required" % minimum, required)
        self.assertNotRegex("%d periods are required" % (minimum + 1), required)
        manifest = {f["id"]: f for f in load_manifest()["fixtures"]}
        self.assertIn("Four monthly periods", manifest["EVI-03"]["precondition"])
        self.assertRegex("4 monthly periods of history", available)

    def test_the_patterns_mean_what_their_properties_say(self):
        """Positive and negative probes, so a pattern cannot silently match nothing."""
        cases = load_cases()
        probes = {
            ("behaviour/b01-ambiguous-column", "g-no-separated-figure"): ("1,265.00", "0.67"),
            ("behaviour/b02-critical-quality-halt", "g-names-the-grade"): ("grade CRITICAL", "grade PASS"),
            ("behaviour/b05-no-uncited-external-claim", "g-no-reliable-source"):
                ("No reliable source found.", "No source."),
            ("disclosure/d01-tier0-churn-comparison", "g-no-internal-figure-sent"):
                ("B2B SaaS churn 8% benchmark", "B2B SaaS churn rate benchmark 2026"),
            ("connectors/c01-crm-pull-named-absence", "g-file-alternative"):
                ("Export the data to CSV or Excel", "No alternative."),
            ("approval/a24-git-push-never", "g-no-push"):
                ("git -C repo push origin main", "git status"),
        }
        for (directory, grader_id), (hit, miss) in probes.items():
            grader = {g["id"]: g for g in cases["evals/" + directory]["bops_graders"]}[grader_id]
            with self.subTest(case=directory, grader=grader_id):
                self.assertRegex(hit, grader["pattern"])
                self.assertNotRegex(miss, grader["pattern"])


# ---------------------------------------------------------------------------------------------
# Evidence and the coverage matrix: ADR-0039 E.6, B and I-2 to I-4
# ---------------------------------------------------------------------------------------------

class EvidenceAndMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()
        cls.rows = matrix_lines()

    @staticmethod
    def rule():
        spec = importlib.util.spec_from_file_location(
            "m13_eval_results_rule", os.path.join(os.path.dirname(__file__),
                                                  "test_m13_eval_results.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @classmethod
    def closing_classes(cls):
        """{case id: (class, reason)} as the M13-DEF-06 rule computes them from the fixture."""
        with open(os.path.join(REPO, "tests", "fixtures", "eval_results", CLOSING_RESULT),
                  encoding="utf-8") as handle:
            document = json.load(handle)
        rule, classes = cls.rule(), {}
        for invocation in document["invocations"]:
            # The classes were recorded under the rule then in force; ADR-0049 does not re-score.
            classes.update((current_case_id(case), verdict) for case, verdict in
                           rule.classify_result(invocation, split_rule=rule.SPLIT_AS_RECORDED).items())
        return classes

    def test_every_case_carries_the_class_the_closing_evaluation_computes(self):
        """ADR-0039 E.6 classes are derived by the M13-DEF-06 rule, never asserted by hand.

        All 64 cases were attempted under section F, so none is `not_executed`. A run stopped
        by the subscription session limit or the turn limit is not admissible, so a case whose
        only non-passing runs are such stops is `execution_unavailable` -- never a pass.
        """
        classes = self.closing_classes()
        self.assertEqual(sorted(case["id"] for case in self.cases.values()), sorted(classes))
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(case["evidence_class"], classes[case["id"]][0])
                self.assertTrue(case["evidence_reason"].startswith(CLOSING_PREFIX))
                self.assertIn(case["evidence_class"], case["evidence_reason"])
        counts = {}
        for case in self.cases.values():
            counts[case["evidence_class"]] = counts.get(case["evidence_class"], 0) + 1
        self.assertEqual(counts, {"automated_pass": 16, "automated_fail": 34,
                                  "execution_unavailable": 14})

    def test_the_pilot_result_is_kept_as_history_not_overwritten(self):
        """The 2026-09-22 pilot stays `automated_fail` in its own fixture and in the case's reason;
        the closing evaluation, not the pilot, supplies the case's M13.2 class."""
        with open(os.path.join(REPO, "tests", "fixtures", "eval_results", PILOT_RESULT),
                  encoding="utf-8") as handle:
            rule = self.rule()
            pilot = rule.classify_result(json.load(handle), split_rule=rule.SPLIT_AS_RECORDED)
        case = self.cases[FIRST_CASE]
        self.assertEqual(pilot[case["id"]][0], "automated_fail")
        self.assertIn(PILOT_HISTORY, case["evidence_reason"])
        self.assertEqual(case["evidence_class"], self.closing_classes()[case["id"]][0])

    def test_rows_carry_their_cases_precedence_and_no_manual_observation_is_claimed(self):
        """A behavioural row's class is the E.6 precedence of its cases' classes."""
        by_dir = {directory: case["evidence_class"] for directory, case in self.cases.items()}
        for path in case_paths():
            with self.subTest(path=path):
                self.assertNotIn("manual_observation", _read(path))
        for row_id, line in self.rows.items():
            if " | behavioural | " not in line:
                continue
            cited = re.findall(r"`(evals/[\w-]+/[\w-]+)/case\.yaml`", line.split(" | ")[3])
            present = {by_dir[c] for c in cited}
            expected = next(k for k in ROW_PRECEDENCE if k in present)
            with self.subTest(row=row_id):
                self.assertIn(" | behavioural-only | %s | " % expected, line)

    def test_every_coverage_row_a_case_names_exists_and_cites_it_back(self):
        for directory, case in self.cases.items():
            for row in case["coverage_rows"]:
                with self.subTest(case=directory, row=row):
                    self.assertIn(row, self.rows)
                    self.assertIn("`%s/case.yaml`" % directory, self.rows[row])

    def test_every_case_a_row_cites_exists_and_names_that_row(self):
        for row_id, line in self.rows.items():
            for cited in re.findall(r"`(evals/[\w-]+/[\w-]+)/case\.yaml`", line):
                with self.subTest(row=row_id, case=cited):
                    self.assertIn(cited, self.cases)
                    self.assertIn(row_id, self.cases[cited]["coverage_rows"])

    def test_every_behavioural_row_cites_at_least_one_case(self):
        for row_id, line in self.rows.items():
            if " | behavioural-only | " in line:
                with self.subTest(row=row_id):
                    self.assertRegex(line, r"`evals/[\w-]+/[\w-]+/case\.yaml`")


# ---------------------------------------------------------------------------------------------
# Committed eval input fixtures: ADR-0041 section 8
# ---------------------------------------------------------------------------------------------

class EvalInputFixtures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.entries = cls.manifest["fixtures"]
        cls.cases = load_cases()

    def fixture_bytes(self, entry):
        with open(os.path.join(REPO, entry["path"]), "rb") as handle:
            return handle.read()

    def test_the_manifest_has_every_field_in_every_entry(self):
        self.assertEqual(self.manifest["contract"], "ADR-0041")
        for entry in self.entries:
            with self.subTest(fixture=entry.get("id")):
                extra = {"stage_as"} if "stage_as" in entry else set()
                self.assertEqual(set(entry), set(MANIFEST_FIELDS) | {"id"} | extra)
                self.assertRegex(entry["id"], r"^EVI-\d\d$")
                # ADR-0048: Markdown only for a declared precondition fixture; CSV otherwise.
                self.assertEqual(entry["format"], "markdown" if extra else "csv")
                self.assertEqual(entry["line_terminator"], "\n")
                self.assertIn("ADR-0041", entry["synthetic"])
                for field in ("precondition", "why_not_demo_data"):
                    self.assertTrue(entry[field].strip())
        ids = [e["id"] for e in self.entries]
        self.assertEqual(ids, ["EVI-%02d" % n for n in range(1, len(ids) + 1)])

    def test_the_manifest_lists_exactly_the_files_present(self):
        present = sorted(n for n in os.listdir(FIXTURE_DIR)
                         if n not in ("manifest.json", ".gitattributes"))
        listed = sorted(os.path.basename(e["path"]) for e in self.entries)
        self.assertEqual(present, listed)
        for entry in self.entries:
            with self.subTest(fixture=entry["id"]):
                self.assertEqual(os.path.dirname(entry["path"]), "tests/fixtures/eval_inputs")
                self.assertFalse(os.path.isdir(os.path.join(REPO, entry["path"])))

    def test_the_committed_bytes_match_the_manifest(self):
        for entry in self.entries:
            data = self.fixture_bytes(entry)
            with self.subTest(fixture=entry["id"]):
                self.assertEqual(len(data), entry["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])

    def test_the_builder_reproduces_every_fixture_byte_for_byte(self):
        builder = import_builder()
        functions = dict(builder.BUILDERS)
        self.assertEqual([i for i, _f in builder.BUILDERS], [e["id"] for e in self.entries])
        directory = tempfile.mkdtemp(prefix="bops-m13-eval-inputs-")
        try:
            for entry in self.entries:
                name = re.match(r"^tests/fixtures/build_eval_inputs\.py:(\w+)\(directory\)$",
                                entry["builder"]).group(1)
                with self.subTest(fixture=entry["id"]):
                    self.assertIs(functions[entry["id"]], getattr(builder, name))
                    written = getattr(builder, name)(directory)
                    self.assertEqual(os.path.basename(written), os.path.basename(entry["path"]))
                    with open(written, "rb") as handle:
                        self.assertEqual(handle.read(), self.fixture_bytes(entry))
            self.assertEqual(len(os.listdir(directory)), len(self.entries))
        finally:
            shutil.rmtree(directory)

    def test_two_rebuilds_are_identical(self):
        builder = import_builder()
        outputs = []
        for _run in range(2):
            directory = tempfile.mkdtemp(prefix="bops-m13-eval-inputs-")
            try:
                digest = hashlib.sha256()
                for _id, function in builder.BUILDERS:
                    with open(function(directory), "rb") as handle:
                        digest.update(handle.read())
                outputs.append(digest.hexdigest())
            finally:
                shutil.rmtree(directory)
        self.assertEqual(outputs[0], outputs[1])

    def test_the_binding_holds_both_ways_and_nothing_is_orphaned(self):
        bound = {}
        for directory, case in self.cases.items():
            for path in case["inputs"]:
                if path.startswith("tests/fixtures/eval_inputs/"):
                    bound.setdefault(path, set()).add(directory)
        declared = {}
        for directory, case in self.cases.items():
            if "precondition_fixture" in case:
                declared.setdefault(case["precondition_fixture"], set()).add(directory)
        for entry in self.entries:
            with self.subTest(fixture=entry["id"]):
                self.assertTrue(entry["cases"], "an orphaned fixture")
                if "stage_as" in entry:
                    # ADR-0048: bound through `precondition_fixture`, never as an input.
                    self.assertEqual(sorted(declared.get(entry["id"], ())), sorted(entry["cases"]))
                    self.assertNotIn(entry["path"], bound)
                    for directory in entry["cases"]:
                        self.assertEqual(self.cases[directory]["precondition_path"], entry["stage_as"])
                    continue
                self.assertEqual(sorted(bound.get(entry["path"], ())), sorted(entry["cases"]))
                for directory in entry["cases"]:
                    self.assertEqual(self.cases[directory]["fixture"], entry["id"])
        self.assertEqual(sorted(bound), sorted(e["path"] for e in self.entries if "stage_as" not in e))
        self.assertEqual(sorted(declared), sorted(e["id"] for e in self.entries if "stage_as" in e))

    def test_every_fixture_is_ascii_lf_small_and_complete(self):
        for entry in self.entries:
            data = self.fixture_bytes(entry)
            with self.subTest(fixture=entry["id"]):
                data.decode("ascii")
                self.assertNotIn(b"\r", data)
                self.assertTrue(data.endswith(b"\n"))
                self.assertNotEqual(data[:3], b"\xef\xbb\xbf")
                self.assertLessEqual(len(data), FIXTURE_LIMIT)

    def test_fixture_text_values_are_synthetic_and_carry_no_instruction(self):
        """Text values use the `Synthetic ...` form; no header or value states an answer."""
        telling = re.compile(r"(?i)expected|answer|ambiguous|critical|fraud|refus|forecast|"
                             r"insufficient|verdict|halt|clarif|instruction|confirm")
        for entry in self.entries:
            lines = self.fixture_bytes(entry).decode("ascii").splitlines()
            with self.subTest(fixture=entry["id"]):
                self.assertIsNone(telling.search("\n".join(lines)))
                if entry["format"] == "markdown":
                    for line in lines:
                        if line.strip():
                            self.assertIn("Synthetic", line)
                    continue
                for line in lines[1:]:
                    for value in line.split(","):
                        if value and not re.match(r"^(\d{4}-\d\d-\d\d|\d+\.\d\d)$", value):
                            self.assertTrue(value.startswith("Synthetic "), value)

    def test_no_url_address_host_or_token_in_a_fixture(self):
        for entry in self.entries:
            text = self.fixture_bytes(entry).decode("ascii")
            with self.subTest(fixture=entry["id"]):
                self.assertIsNone(re.search(r"(?i)https?://|www\.|@|\.(com|net|org|io)\b", text))
                for shape in TOKEN_SHAPES:
                    self.assertIsNone(re.search(shape, text))

    def test_no_grader_string_appears_in_its_bound_fixture(self):
        """ADR-0041 section 6: echoing the fixture can neither satisfy nor trip a grader."""
        for entry in self.entries:
            text = self.fixture_bytes(entry).decode("ascii")
            for directory in entry["cases"]:
                for grader in graders_of(self.cases[directory], "deterministic"):
                    with self.subTest(fixture=entry["id"], grader=grader["id"]):
                        if "pattern" in grader and grader["check"].startswith("response_"):
                            self.assertIsNone(re.search(grader["pattern"], text))
                        for field in ("skill", "command", "agent"):
                            if field in grader:
                                self.assertNotIn(grader[field], text)

    def test_the_gitattributes_pins_the_directory(self):
        with open(os.path.join(FIXTURE_DIR, ".gitattributes"), "rb") as handle:
            self.assertEqual(handle.read(), b"* -text\n")

    def test_the_builder_is_statically_deterministic(self):
        """ADR-0041 section 3: no file read, network, random, clock, environment or process."""
        source = _read(BUILDER)
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        self.assertEqual(imported, {"os"})
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                    and node.value.id == "os":
                self.assertEqual(node.attr, "path")
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) \
                    and getattr(node.value.value, "id", None) == "os":
                self.assertEqual(node.attr, "join")
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
                modes = [a.value for a in node.args[1:2] if isinstance(a, ast.Constant)]
                self.assertEqual(modes, ["wb"], "the builder opens files for writing only")
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, ("set", "frozenset", "float", "hash", "id", "input",
                                           "eval", "exec", "__import__", "globals"))
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                self.fail("binary floating point in the builder")
        for word in ("random", "time", "datetime", "uuid", "environ", "getenv", "platform",
                     "locale", "socket", "urllib", "http", "subprocess", "glob", "listdir",
                     "getcwd", "expanduser", "tempfile", "secrets"):
            with self.subTest(word=word):
                self.assertIsNone(re.search(r"\b%s\b" % word, source.split('"""', 2)[2]))

    def test_each_builder_writes_only_into_the_directory_it_is_given(self):
        builder = import_builder()
        for fixture_id, function in builder.BUILDERS:
            with self.subTest(fixture=fixture_id):
                self.assertEqual(function.__code__.co_argcount, 1)
                self.assertIsNone(function.__defaults__)


if __name__ == "__main__":
    unittest.main()
