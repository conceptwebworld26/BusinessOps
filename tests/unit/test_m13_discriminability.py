"""M13.1 description discriminability measurement - ADR-0039 section D.2 (M13-MEAS-D2, R-05).

Measures the Jaccard overlap of content words between the frontmatter `description`s of
distinct components, **within** each competing tier:

- the **command tier**: every `commands/*.md` a model can route to. A command carrying
  `disable-model-invocation: true` never competes for routing and is listed as excluded;
- the **skill tier**: every `skills/*/SKILL.md`.

Method (the M8 review's tier-scoped Jaccard method; M8 did not record its tokenisation or
stop-word list, so both are fixed here and these scores are not directly comparable with the
M8 figures): the description is lower-cased; content words are maximal runs of ASCII letters
of three or more characters that are not in `STOP_WORDS`; the score is
|A intersect B| / |A union B| over the two word sets.

**Recorded, never a threshold.** No overlap score passes or fails: no accepted architecture
defines an overlap threshold (ADR-0039 D.2). The only assertions are that every built
component has a non-empty description and that the measurement is deterministic.

The 1,024-character skill-description limit (`architecture.md` section 2, ADR-0013) is the
one limit accepted architecture defines, and ADR-0039 D.2 names it as the second assertion.
Two shipped skill descriptions exceed it, so under ADR-0039 section G that assertion is **not
committed failing and not loosened**: the finding is defect M13-DEF-01 in
`docs/testing/defects.md`, whose reproducer is `description_lengths()` below. Every length is
recorded by the measurement.

Full measurement, every pair:

    python -c "import sys; sys.path[:0]=['lib/python','tests']; \
from unit.test_m13_discriminability import measure; import json; \
print(json.dumps(measure(), indent=1, sort_keys=True))"
"""

import atexit
import glob
import itertools
import json
import os
import re
import unittest
from decimal import ROUND_HALF_EVEN, Decimal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

#: The documented hard limit for a skill `description` (architecture.md section 2, ADR-0013).
SKILL_DESCRIPTION_LIMIT = 1024

#: Function words and generic plugin vocabulary that carry no routing signal. Fixed here so
#: the measurement is reproducible; changing it changes every score and needs a new record.
STOP_WORDS = frozenset("""
    about above after again against all also and any are because been before being below
    between both but can could did does doing down during each else ever every few for from
    further had has have having her here hers him his how into its itself just more most
    much must never nor not now off once one only other our ours out over own per same she
    should since some such than that the their theirs them then there these they this those
    through too under until upon very was were what when where whether which while who whom
    whose why will with within without would you your yours
    use used using asked ask want wants user users etc via
""".split())

WORD = re.compile(r"[a-z]+")
QUANTUM = Decimal("0.001")


def frontmatter(path):
    """The key/value lines of a markdown file's leading `---` block, as a dict of strings."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    fields = {}
    for line in block.splitlines():
        if ":" not in line or line[:1].isspace():
            continue
        key, _sep, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = json.loads(value) if value[0] == '"' else value[1:-1]
        fields[key.strip()] = value
    return fields


def components():
    """{tier: {name: description}}, plus the commands excluded from routing competition."""
    commands, excluded = {}, {}
    for path in sorted(glob.glob(os.path.join(REPO, "commands", "*.md"))):
        name = os.path.splitext(os.path.basename(path))[0]
        fields = frontmatter(path)
        if fields.get("disable-model-invocation", "").lower() == "true":
            excluded[name] = "disable-model-invocation: true"
            continue
        commands[name] = fields.get("description", "")
    skills = {}
    for path in sorted(glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md"))):
        skills[os.path.basename(os.path.dirname(path))] = frontmatter(path).get(
            "description", "")
    return {"command": commands, "skill": skills}, excluded


def content_words(description):
    return frozenset(w for w in WORD.findall(description.lower())
                     if len(w) >= 3 and w not in STOP_WORDS)


def jaccard(first, second):
    """Exact Jaccard index as a Decimal; two empty sets score zero, never a division error."""
    union = first | second
    if not union:
        return Decimal(0)
    return Decimal(len(first & second)) / Decimal(len(union))


def _q(value):
    return str(value.quantize(QUANTUM, rounding=ROUND_HALF_EVEN))


def description_lengths():
    """{component: characters} for every skill description - the M13-DEF-01 reproducer."""
    tiers, _excluded = components()
    return {name: len(text) for name, text in sorted(tiers["skill"].items())}


def measure():
    """The whole D.2 measurement as a JSON-ready dict. Deterministic: same files, same bytes."""
    tiers, excluded = components()
    result = {"method": "jaccard over content words, tier-scoped",
              "stop_words": len(STOP_WORDS), "excluded": excluded, "tiers": {}}
    for tier, members in sorted(tiers.items()):
        words = {name: content_words(text) for name, text in members.items()}
        pairs = []
        for left, right in itertools.combinations(sorted(members), 2):
            pairs.append({"pair": [left, right],
                          "score": jaccard(words[left], words[right])})
        pairs.sort(key=lambda p: (-p["score"], p["pair"]))
        scores = [p["score"] for p in pairs]
        mean = sum(scores, Decimal(0)) / Decimal(len(scores)) if scores else Decimal(0)
        result["tiers"][tier] = {
            "components": len(members),
            "pairs": len(pairs),
            "mean": _q(mean),
            "max": _q(max(scores)) if scores else None,
            "top3": [{"pair": p["pair"], "score": _q(p["score"])} for p in pairs[:3]],
            "all_pairs": [{"pair": p["pair"], "score": _q(p["score"])} for p in pairs],
            "description_chars": {n: len(t) for n, t in sorted(members.items())},
        }
    return result


def _print_summary():
    try:
        record = measure()
    except Exception:              # the tests below report any failure; exit output is a courtesy
        return
    print(os.linesep + "  M13-MEAS-D2 (measurement, not benchmarking; no threshold)")
    for tier, data in sorted(record["tiers"].items()):
        print("  M13-MEAS-D2 %s tier: %d components, %d pairs, mean %s, max %s, top3 %s"
              % (tier, data["components"], data["pairs"], data["mean"], data["max"],
                 json.dumps(data["top3"])))
    if record["excluded"]:
        print("  M13-MEAS-D2 excluded from routing competition: %s"
              % json.dumps(record["excluded"], sort_keys=True))


_REGISTERED = []


class DescriptionsExist(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not _REGISTERED:
            atexit.register(_print_summary)
            _REGISTERED.append(True)

    def test_every_command_has_a_non_empty_description(self):
        for path in sorted(glob.glob(os.path.join(REPO, "commands", "*.md"))):
            with self.subTest(command=os.path.basename(path)):
                self.assertTrue(frontmatter(path).get("description", "").strip())

    def test_every_skill_has_a_non_empty_description(self):
        paths = sorted(glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md")))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(skill=os.path.basename(os.path.dirname(path))):
                self.assertTrue(frontmatter(path).get("description", "").strip())

    def test_every_agent_has_a_non_empty_description(self):
        for path in sorted(glob.glob(os.path.join(REPO, "agents", "*.md"))):
            with self.subTest(agent=os.path.basename(path)):
                self.assertTrue(frontmatter(path).get("description", "").strip())

    def test_every_skill_description_is_within_the_documented_limit(self):
        """M13-DEF-01, fixed in M14-5: the assertion ADR-0039 section G held back while it failed."""
        for name, length in description_lengths().items():
            with self.subTest(skill=name):
                self.assertLessEqual(length, SKILL_DESCRIPTION_LIMIT)


class MeasurementIsDeterministic(unittest.TestCase):

    def test_two_measurements_are_identical(self):
        self.assertEqual(json.dumps(measure(), sort_keys=True),
                         json.dumps(measure(), sort_keys=True))

    def test_every_pair_within_each_tier_is_scored_exactly_once(self):
        tiers, _excluded = components()
        record = measure()
        for tier, members in tiers.items():
            n = len(members)
            self.assertEqual(record["tiers"][tier]["pairs"], n * (n - 1) // 2)
            seen = {tuple(p["pair"]) for p in record["tiers"][tier]["all_pairs"]}
            self.assertEqual(len(seen), n * (n - 1) // 2)

    def test_tiers_are_measured_separately(self):
        tiers, _excluded = components()
        self.assertFalse(set(tiers["command"]) & set(tiers["skill"]))

    def test_a_command_outside_routing_competition_is_listed_not_silently_dropped(self):
        tiers, excluded = components()
        on_disk = {os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(os.path.join(REPO, "commands", "*.md"))}
        self.assertEqual(set(tiers["command"]) | set(excluded), on_disk)


class TheJaccardPrimitive(unittest.TestCase):
    """Self-tests of the measurement instrument, so a wrong score is caught here first."""

    def test_identical_sets_score_one(self):
        self.assertEqual(jaccard(frozenset("ab"), frozenset("ab")), Decimal(1))

    def test_disjoint_sets_score_zero(self):
        self.assertEqual(jaccard(frozenset("ab"), frozenset("cd")), Decimal(0))

    def test_two_empty_sets_score_zero_rather_than_raising(self):
        self.assertEqual(jaccard(frozenset(), frozenset()), Decimal(0))

    def test_partial_overlap_is_exact(self):
        self.assertEqual(jaccard(frozenset("abc"), frozenset("bcd")), Decimal(2) / Decimal(4))

    def test_content_words_drop_stop_words_short_words_and_digits(self):
        self.assertEqual(content_words("Use when the 20 sales of an EBITDA margin"),
                         frozenset({"sales", "ebitda", "margin"}))

    def test_frontmatter_reads_quoted_and_plain_values(self):
        import tempfile
        directory = tempfile.mkdtemp(prefix="bops-m13-fm-")
        try:
            path = os.path.join(directory, "x.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('---\ndescription: "A \\"quoted\\" one"\nname: plain value\n---\nbody\n')
            fields = frontmatter(path)
            self.assertEqual(fields["description"], 'A "quoted" one')
            self.assertEqual(fields["name"], "plain value")
        finally:
            import shutil
            shutil.rmtree(directory, ignore_errors=True)
