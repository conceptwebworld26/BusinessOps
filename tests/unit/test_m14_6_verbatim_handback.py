# -*- coding: utf-8 -*-
"""M14-6: the scout's reply reaches the parser verbatim (M9 criterion 5; ADR-0053).

The history, measured on live runs:

- **M14-5.** The sessions wrote only the de-indented protocol lines to the reply file.
- **M14-6, first fix (skill wording only).** The sessions copied the whole framed tool result, yet
  lost every whitespace-only line and added a final newline, in 4 of 4 runs.

A model copy cannot guarantee "verbatim". So the harness now records the reply itself. Claude Code
gives the plugin's `PostToolUse` hook the scout's own text as `tool_response.content`;
`research.handback.capture()` stores it byte for byte, and `close_retrieval()` reads it back through
`R.handback_reply()`. No model touches it.

These tests pin every link in that chain:

- the capture is byte-exact and ignores every other event;
- an operation id is safe to use as a file name;
- the launcher entry and the hook declaration are exact;
- a tool call may neither invoke the entry nor touch the store;
- `close_retrieval` hands the parser exactly the text it was given;
- every shipped skill that closes a retrieval reads the capture and forbids a copy.

All fixtures are synthetic. The reply shape (prose, whitespace-only lines, no trailing newline) is the
one measured on the 2026-09-27 smoke traces.
"""

import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.join(REPO, "lib", "python") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "lib", "python"))

from bops import research as R                                            # noqa: E402
from bops.research import handback as H                                   # noqa: E402
from bops.research import scout as scout_mod                              # noqa: E402
from bops.writeguard import classify as K                                 # noqa: E402
from bops.writeguard import policy as P                                   # noqa: E402

SUBJECT = "logistics"
CATEGORY = R.INDUSTRY
OPERATION = "m14-6-verbatim"
KWARGS = dict(intent=R.BENCHMARK, public_terms={"industry": "logistics", "period": "2026"},
              operation=OPERATION)

RECORDS = [
    {"reference": "https://www.ons.gov.uk/economy/transport-storage-2026",
     "source": "Office for National Statistics", "title": "Transport and storage sector accounts, 2026",
     "publication_date": "2026-04-30", "source_type": "official_statistics",
     "content": "Gross margin across the sector averaged 14.2%.", "claim_kind": "financials"},
    {"reference": "https://www.logisticsweekly.com/margins", "source": "Logistics Weekly",
     "title": "Where the margin went", "publication_date": "2026-02-11", "source_type": "press",
     "content": "Operators reported thinner margins.", "claim_kind": "financials"},
]

#: The scout's own reply, as `tool_response.content` carries it. It has prose, an indented line, a
#: whitespace-only line, a CRLF and a whitespace-only last line, so any trimming, stripping, de-indenting or
#: line-ending translation would change it.
SCOUT_REPLY = "\n".join(
    ["I searched two public sources and read both.", "   (one page was slow)", "  "]
    + ["%s %s %s" % (scout_mod.RECORD_TOKEN, OPERATION, json.dumps(r)) for r in RECORDS]
    + ["%s %s %d" % (scout_mod.END_TOKEN, OPERATION, len(RECORDS)), "",
       "Notes: one further page returned HTTP 403.\r", "Done.", "  "])


def event(**overrides):
    """A `PostToolUse` event shaped as Claude Code 2.1.283 delivers it (measured by probe)."""
    base = {"session_id": "s-1", "hook_event_name": "PostToolUse", "tool_name": "Agent",
            "tool_use_id": "toolu_1",
            "tool_input": {"subagent_type": H.SCOUT_AGENT,
                           "prompt": json.dumps({"query_text": "logistics 2026",
                                                 "operation": OPERATION})},
            "tool_response": {"status": "completed", "agentType": H.SCOUT_AGENT,
                              "content": [{"type": "text", "text": SCOUT_REPLY}]}}
    base.update(overrides)
    return base


class Home(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="bops-m14-6-home-")
        self.addCleanup(shutil.rmtree, self.home, True)


class TheCaptureIsByteExact(Home):

    def test_the_captured_file_holds_exactly_the_scout_text(self):
        path = H.capture(event(), home=self.home)
        self.assertEqual(path, os.path.join(H.root(self.home), OPERATION + ".txt"))
        with io.open(path, "rb") as handle:
            self.assertEqual(handle.read(), SCOUT_REPLY.encode("utf-8"))

    def test_reading_it_back_changes_nothing(self):
        H.capture(event(), home=self.home)
        self.assertEqual(H.reply(OPERATION, home=self.home), SCOUT_REPLY)

    def test_multiple_text_blocks_are_joined_unchanged(self):
        halves = [SCOUT_REPLY[:40], SCOUT_REPLY[40:]]
        H.capture(event(tool_response={"content": [{"type": "text", "text": halves[0]},
                                                   {"type": "text", "text": halves[1]}]}),
                  home=self.home)
        self.assertEqual(H.reply(OPERATION, home=self.home), SCOUT_REPLY)

    def test_a_later_dispatch_for_the_same_operation_replaces_the_earlier(self):
        H.capture(event(), home=self.home)
        H.capture(event(tool_response={"content": [{"type": "text", "text": "second"}]}),
                  home=self.home)
        self.assertEqual(H.reply(OPERATION, home=self.home), "second")

    def test_the_store_is_under_the_guard_root(self):
        self.assertEqual(H.root(self.home), os.path.join(P.guard_root(self.home), "handback"))


class OnlyAScoutDispatchIsCaptured(Home):

    def assertIgnored(self, evt):
        self.assertIsNone(H.capture(evt, home=self.home))
        self.assertFalse(os.path.exists(H.root(self.home)))

    def test_other_events_tools_and_agents_are_ignored(self):
        self.assertIgnored(event(hook_event_name="PreToolUse"))
        self.assertIgnored(event(tool_name="Bash"))
        self.assertIgnored(event(tool_input={"subagent_type": "general-purpose",
                                             "prompt": json.dumps({"operation": OPERATION})}))
        self.assertIgnored("not an event")

    def test_a_prompt_that_is_not_a_brief_is_ignored(self):
        self.assertIgnored(event(tool_input={"subagent_type": H.SCOUT_AGENT, "prompt": "hello"}))
        self.assertIgnored(event(tool_input={"subagent_type": H.SCOUT_AGENT,
                                             "prompt": json.dumps({"query_text": "x"})}))

    def test_an_unsafe_operation_id_is_never_used_as_a_file_name(self):
        for bad in ("../../escape", "a/b", "", ".hidden", "x" * 201, 7):
            with self.subTest(operation=bad):
                self.assertIgnored(event(tool_input={"subagent_type": H.SCOUT_AGENT,
                                                     "prompt": json.dumps({"operation": bad})}))
                with self.assertRaises(H.HandbackError):
                    H.reply(bad, home=self.home)

    def test_a_response_without_text_is_ignored(self):
        self.assertIgnored(event(tool_response={"content": [{"type": "image"}]}))
        self.assertIgnored(event(tool_response=None))

    def test_a_missing_capture_fails_closed(self):
        with self.assertRaises(H.HandbackError):
            H.reply(OPERATION, home=self.home)

    def test_the_entry_never_raises(self):
        self.assertEqual(H.main(io.StringIO("{not json")), 0)


class TheEngineHandsTheParserTheExactText(unittest.TestCase):

    def close(self, payload):
        return R.close_retrieval(payload, SUBJECT, CATEGORY, as_of="2026-09-27", **KWARGS)

    def test_the_captured_reply_parses_to_the_records(self):
        self.assertEqual(self.close(SCOUT_REPLY)["accepted"], len(RECORDS))

    def test_close_retrieval_passes_the_parser_the_same_object(self):
        seen = []
        original = scout_mod.parse_reply

        def spy(reply, brief):
            seen.append(reply)
            return original(reply, brief)

        scout_mod.parse_reply = spy
        try:
            self.close(SCOUT_REPLY)
        finally:
            scout_mod.parse_reply = original
        self.assertEqual(len(seen), 1)
        self.assertIs(seen[0], SCOUT_REPLY)

    def test_a_trimmed_copy_is_a_different_text_even_when_it_parses_the_same(self):
        """Why criterion 5 compares text, not records: the M14-5 copies parsed identically."""
        trimmed = "\n".join(line.strip() for line in SCOUT_REPLY.split("\n")
                            if line.strip().startswith((scout_mod.RECORD_TOKEN, scout_mod.END_TOKEN)))
        self.assertNotEqual(trimmed, SCOUT_REPLY)
        self.assertEqual(self.close(trimmed)["accepted"], self.close(SCOUT_REPLY)["accepted"])


@unittest.skipUnless(shutil.which("sh"), "the hook runs the POSIX-shell resolver")
class TheHookPathIsExact(Home):

    def test_the_hook_declaration_runs_the_exact_entry_for_dispatches(self):
        with open(os.path.join(REPO, "hooks", "hooks.json"), encoding="utf-8") as handle:
            [group] = json.load(handle)["hooks"]["PostToolUse"]
        self.assertEqual(group["matcher"].split("|"), ["Agent", "Task"])
        [command] = group["hooks"]
        self.assertEqual(command["command"], 'sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" --handback')

    def test_the_launcher_entry_captures_from_stdin_exactly(self):
        env = dict(os.environ, HOME=self.home)
        store_existed = os.path.isdir(H.root())
        proc = subprocess.run([shutil.which("sh"), os.path.join(REPO, "lib", "bops_run.sh"), "--handback"],
                              input=json.dumps(event()).encode("utf-8"), capture_output=True,
                              env=env, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"")
        # The launcher resolves home from the account database, not $HOME (policy.default_home), so
        # read back from wherever it wrote; the account's store is left as it was found.
        written = os.path.join(H.root(), OPERATION + ".txt")
        try:
            with io.open(written, "rb") as handle:
                self.assertEqual(handle.read(), SCOUT_REPLY.encode("utf-8"))
        finally:
            if os.path.exists(written):
                os.unlink(written)
            if not store_existed and os.path.isdir(H.root()) and not os.listdir(H.root()):
                os.rmdir(H.root())

    def test_the_entry_takes_no_argument(self):
        proc = subprocess.run([shutil.which("sh"), os.path.join(REPO, "lib", "bops_run.sh"),
                               "--handback", "extra"], capture_output=True, timeout=120,
                              stdin=subprocess.DEVNULL)
        self.assertEqual(proc.returncode, 2)


class AToolCallCannotForgeACapture(Home):

    def setUp(self):
        super().setUp()
        self.cwd = tempfile.mkdtemp(prefix="bops-m14-6-cwd-")
        self.addCleanup(shutil.rmtree, self.cwd, True)
        self.policy = P.Policy(self.cwd, home=self.home, plugin=REPO,
                               guard=P.guard_root(self.home), engaged=True)

    def decision(self, name, **tool_input):
        return K.classify_tool_call(name, tool_input, self.policy).decision

    def test_invoking_the_capture_entry_is_prohibited(self):
        launcher = os.path.join(REPO, "lib", "bops_run.sh")
        for command in ('sh "%s" --handback' % launcher,
                        'echo {} | sh "%s" --handback' % launcher,
                        'python3 -I %s/lib/python/bops_run.py --handback' % REPO):
            with self.subTest(command=command):
                self.assertEqual(self.decision("Bash", command=command), P.PROHIBITED)

    def test_writing_into_the_store_is_prohibited(self):
        target = os.path.join(H.root(self.home), OPERATION + ".txt")
        self.assertEqual(self.decision("Write", file_path=target, content="forged"), P.PROHIBITED)

    def test_the_documented_inline_close_needs_no_approval(self):
        launcher = os.path.join(REPO, "lib", "bops_run.sh")
        code = ("\nimport json\nfrom bops import research as R\nprint(json.dumps(R.close_retrieval(\n"
                "    R.handback_reply('op-1'), 'logistics', R.INDUSTRY, intent=R.BENCHMARK,\n"
                "    public_terms={'industry': 'logistics'},\n    operation='op-1'), default=str))\n")
        self.assertEqual(self.decision("Bash", command='sh "%s" -c "%s"' % (launcher, code)), P.FREE)


def closing_skills():
    """Every shipped skill whose body closes a retrieval, with prose line wrapping collapsed."""
    found = {}
    for path in sorted(glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md"))):
        text = io.open(path, encoding="utf-8").read()
        if re.search(r"R\.close_retrieval(_object)?\(", text):
            found[os.path.basename(os.path.dirname(path))] = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    return found


RESEARCH = ("bops-company-analysis", "bops-market-analysis", "bops-competitor-analysis",
            "bops-industry-research")


class EveryClosingSkillReadsTheCapture(unittest.TestCase):

    def test_the_closing_skills_are_the_expected_six(self):
        self.assertEqual(sorted(closing_skills()),
                         sorted(RESEARCH + ("bops-benchmark-comparison", "bops-swot")))

    def test_each_research_skill_closes_inline_from_the_capture(self):
        skills = closing_skills()
        for name in RESEARCH:
            with self.subTest(skill=name):
                text = skills[name]
                for phrase in ("Close from the harness's verbatim capture, never from a copy",
                               "R.handback_reply('<operation>'),",
                               "Do not copy, write or retype the reply yourself",
                               "never from a script file",
                               "report the retrieval as failed and stop"):
                    self.assertIn(phrase, text)

    def test_every_closing_skill_reads_the_capture_and_no_model_copy(self):
        for name, text in closing_skills().items():
            with self.subTest(skill=name):
                self.assertIn("handback_reply(", text)
                self.assertNotIn("reply.txt", text)
                self.assertNotIn("exec(open(", text)


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
