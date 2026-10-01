"""M13-DEF-24 remediation (ADR-0051): both enforcement layers, exercised as real processes.

- **Layer 1** through the exact production path Claude Code runs: `hooks/hooks.json` names
  `sh "${CLAUDE_PLUGIN_ROOT}/hooks/bops_guard.sh" <event>`, which reaches the resolver
  (`lib/bops_run.sh`), the launcher (`lib/python/bops_run.py --guard`) and the hook. The a20
  write is fed in as Claude Code would feed it, and the file is hashed before and after.
- **Layer 2** inside a real engine process started through the launcher: the execution guard
  is installed before any engine code runs, and stops writes, processes and connections its
  policy does not admit; the export API writes only after a redeemed capability.

What this does not show: that Claude Code honours the hook's deny. That was measured on
Claude Code 2.1.283 and is recorded in
`docs/development/2026-09-26-m13-def-24-hook-runtime-experiment.md`.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENGINE = os.path.join(REPO, "lib", "python")
LAUNCHER = os.path.join(ENGINE, "bops_run.py")
WRAPPER = os.path.join(REPO, "hooks", "bops_guard.sh")
HOOKS_JSON = os.path.join(REPO, "hooks", "hooks.json")
TIMEOUT = 120
A20 = "cat > README.md <<'EOF'\n# Sales summary\n\nRevenue grew.\nEOF"


def _sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class Tree(unittest.TestCase):

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="bops-def24i-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.cwd = os.path.join(self.base, "work")
        self.tmp = os.path.join(self.base, "tmp")
        self.guard = os.path.join(self.base, "guard")
        for d in (self.cwd, self.tmp):
            os.makedirs(d)
        self.readme = os.path.join(self.cwd, "README.md")
        with open(self.readme, "w") as handle:
            handle.write("# Synthetic Project Notes\n")
        self.before = _sha(self.readme)
        self.env = dict((k, v) for k, v in os.environ.items() if not k.startswith(("PYTHON", "BOPS_")))
        self.env.update({"BOPS_GUARD_ROOT": self.guard, "TMPDIR": self.tmp,
                         "BOPS_PYTHON": sys.executable})


class TheProductionHookPath(Tree):
    """Cases 23 and 24 through hooks/bops_guard.sh, as Claude Code invokes it."""

    session = "sess-def24-wrapper"

    def event(self, event, payload):
        result = subprocess.run(["sh", WRAPPER, event], input=json.dumps(payload), cwd=self.cwd,
                                env=self.env, capture_output=True, text=True, timeout=TIMEOUT)
        return result

    def pre(self, tool, **tool_input):
        return self.event("pre-tool-use", {"session_id": self.session, "cwd": self.cwd,
                                           "tool_name": tool, "tool_input": tool_input,
                                           "hook_event_name": "PreToolUse"})

    def test_hooks_json_declares_the_guard_for_the_write_tools(self):
        with open(HOOKS_JSON, encoding="utf-8") as handle:
            hooks = json.load(handle)["hooks"]
        [entry] = hooks["PreToolUse"]
        for tool in ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "PowerShell", "Skill"):
            self.assertIn(tool, entry["matcher"].split("|"))
        for event, name in (("PreToolUse", "pre-tool-use"), ("UserPromptSubmit", "user-prompt-submit"),
                            ("UserPromptExpansion", "user-prompt-expansion")):
            [group] = hooks[event]
            [command] = group["hooks"]
            self.assertEqual(command["type"], "command")
            self.assertEqual(command["command"],
                             'sh "${CLAUDE_PLUGIN_ROOT}/hooks/bops_guard.sh" %s' % name)

    def test_the_a20_write_is_denied_before_it_runs_and_the_file_is_unchanged(self):
        self.assertEqual(self.pre("Skill", skill="businessops:sales-analysis").stdout, "")
        result = self.pre("Bash", command=A20)
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn(self.readme, decision["permissionDecisionReason"])
        self.assertEqual(_sha(self.readme), self.before)

    def test_approval_through_the_users_prompt_then_exactly_one_execution(self):
        self.pre("Skill", skill="businessops:sales-analysis")
        reason = json.loads(self.pre("Bash", command=A20).stdout)["hookSpecificOutput"][
            "permissionDecisionReason"]
        [code] = re.findall(r"BOPS-W-[A-Z0-9]{8}", reason)
        granted = self.event("user-prompt-submit", {"session_id": self.session, "cwd": self.cwd,
                                                    "prompt": "approve %s" % code})
        self.assertIn("The user approved", json.loads(granted.stdout)["hookSpecificOutput"]
                      ["additionalContext"])
        self.assertEqual(self.pre("Bash", command=A20).stdout, "")          # proceeds once
        self.assertIn('"deny"', self.pre("Bash", command=A20).stdout)       # then denied again

    def test_the_guard_fails_closed_when_it_cannot_start(self):
        broken = os.path.join(self.base, "plugin")
        os.makedirs(os.path.join(broken, "hooks"))
        shutil.copy(WRAPPER, os.path.join(broken, "hooks", "bops_guard.sh"))
        payload = json.dumps({"session_id": "s", "cwd": self.cwd, "tool_name": "Bash",
                              "tool_input": {"command": "ls"}})
        result = subprocess.run(["sh", os.path.join(broken, "hooks", "bops_guard.sh"), "pre-tool-use"],
                                input=payload, env=self.env, capture_output=True, text=True,
                                timeout=TIMEOUT)
        self.assertEqual(result.returncode, 2)                  # Claude Code: blocking error
        self.assertIn("blocked before it ran", result.stderr)
        result = subprocess.run(["sh", os.path.join(broken, "hooks", "bops_guard.sh"),
                                 "user-prompt-submit"], input=payload, env=self.env,
                                capture_output=True, text=True, timeout=TIMEOUT)
        self.assertEqual(result.returncode, 0)                  # a prompt is never blocked

    def test_the_launcher_refuses_an_unknown_guard_event(self):
        result = subprocess.run([sys.executable, "-I", LAUNCHER, "--guard", "post-tool-use"],
                                input="{}", env=self.env, capture_output=True, text=True,
                                timeout=TIMEOUT)
        self.assertNotEqual(result.returncode, 0)


class TheEngineExecutionGuard(Tree):
    """Layer 2: BusinessOps's own process enforces the policy whatever called it."""

    def engine(self, code, extra_env=None):
        env = dict(self.env)
        env.update(extra_env or {})
        return subprocess.run([sys.executable, "-I", LAUNCHER, "-c", code], cwd=self.cwd, env=env,
                              capture_output=True, text=True, timeout=TIMEOUT)

    def assertBlocked(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("WriteBlockedError", result.stderr)

    def test_the_launcher_installs_the_guard_before_engine_code(self):
        result = self.engine("from bops.writeguard import engine\nprint(engine.installed())")
        self.assertEqual(result.stdout.strip(), "True", result.stderr)

    def test_a_write_outside_the_engines_state_is_blocked(self):
        for code in ("open('README.md', 'w').write('x')", "open('README.md', 'a').write('x')",
                     "import os\nos.remove('README.md')", "import os\nos.truncate('README.md', 0)",
                     "import os\nos.rename('README.md', 'old.md')",
                     "import shutil\nshutil.copy('README.md', 'copy.md')",
                     "import pathlib\npathlib.Path('new.md').write_text('x')"):
            with self.subTest(code=code):
                self.assertBlocked(self.engine(code))
        self.assertEqual(_sha(self.readme), self.before)
        self.assertEqual(sorted(os.listdir(self.cwd)), ["README.md"])

    def test_temp_file_plus_rename_is_blocked_inside_the_engine(self):
        result = self.engine("import os\nopen(%r, 'w').write('x')\nos.replace(%r, 'README.md')"
                             % (os.path.join(self.tmp, "t"), os.path.join(self.tmp, "t")))
        self.assertBlocked(result)
        self.assertEqual(_sha(self.readme), self.before)

    def test_a_process_or_connection_is_blocked(self):
        self.assertBlocked(self.engine(
            "import subprocess\nsubprocess.run(['sh', '-c', 'echo x > README.md'])"))
        self.assertBlocked(self.engine("import os\nos.system('echo x > README.md')"))
        self.assertBlocked(self.engine(
            "import socket\nsocket.create_connection(('127.0.0.1', 9), timeout=1)"))
        self.assertEqual(_sha(self.readme), self.before)

    def test_the_engines_own_state_and_new_output_are_admitted(self):
        result = self.engine(
            "import os\nos.makedirs('.businessops/verification', exist_ok=True)\n"
            "open('.businessops/verification/r.json', 'x').write('{}')\n"
            "os.makedirs('businessops-output', exist_ok=True)\n"
            "open('businessops-output/summary.md', 'w').write('x')\nprint('ok')")
        self.assertEqual(result.stdout.strip(), "ok", result.stderr)
        self.assertBlocked(self.engine("open('businessops-output/summary.md', 'w').write('y')"))

    def test_a_read_only_command_still_runs_under_the_guard(self):
        """Case 26: an existing read-only command, through the launcher, with the guard on."""
        demo = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
        shutil.copy(demo, os.path.join(self.cwd, "northwind_sales.csv"))
        result = self.engine("from bops import commands\n"
                             "run = commands.run('sales-analysis', 'northwind_sales.csv')\n"
                             "print(run.status)")
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertTrue(result.stdout.strip())
        self.assertEqual(_sha(self.readme), self.before)

    def test_the_export_api_without_a_session_writes_nothing(self):
        result = self.engine("from bops.writeguard import export\nexport.write_text('README.md', 'x')",
                             {"CLAUDE_CODE_SESSION_ID": ""})
        self.assertIn("WriteApprovalRequired", result.stderr)
        self.assertEqual(_sha(self.readme), self.before)

    def test_the_export_api_writes_new_output_without_approval(self):
        result = self.engine("import os\nos.makedirs('businessops-output')\n"
                             "from bops.writeguard import export\n"
                             "print(export.write_text('businessops-output/s.md', 'x')['status'])")
        self.assertEqual(result.stdout.strip(), "written", result.stderr)


class TheExportCapabilityUnderTheGuard(Tree):
    """The export's approved write is admitted by the installed guard, once, for that path."""

    BOOT = (
        "import sys, os, json\n"
        "sys.path.insert(0, %(engine)r)\n"
        "from bops.writeguard import engine, export, capability as C\n"
        "engine.install(engine.EnginePolicy(guard=%(guard)r))\n"
        "store = C.Store(%(guard)r)\n"
        "def attempt(path, text):\n"
        "    try:\n"
        "        return export._write(path, text, False, 'utf-8', store, 's-export')['status']\n"
        "    except Exception as e:\n"
        "        return type(e).__name__ + ':' + str(getattr(e, 'code', ''))\n"
        "%(body)s\n")

    def run_boot(self, body):
        code = self.BOOT % {"engine": ENGINE, "guard": self.guard, "body": body}
        return subprocess.run([sys.executable, "-I", "-c", code], cwd=self.cwd, env=self.env,
                              capture_output=True, text=True, timeout=TIMEOUT)

    def test_request_grant_redeem_write_once(self):
        first = self.run_boot("print(attempt('README.md', 'approved\\n'))")
        kind, code = first.stdout.strip().split(":", 1)
        self.assertEqual(kind, "WriteApprovalRequired", first.stderr)
        # The grant happens outside the engine, as the UserPromptSubmit hook does it.
        sys.path.insert(0, ENGINE)
        from bops.writeguard import capability as C
        record, why = C.Store(self.guard).grant(code, "s-export")
        self.assertIsNone(why)
        result = self.run_boot(
            "print(json.dumps([attempt('OTHER.md', 'approved\\n').split(':')[0],\n"
            "                  attempt('README.md', 'changed\\n').split(':')[0],\n"
            "                  attempt('README.md', 'approved\\n'),\n"
            "                  attempt('README.md', 'approved\\n').split(':')[0]]))")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [
            "WriteApprovalRequired", "WriteApprovalRequired", "written", "WriteApprovalRequired"])
        with open(self.readme) as handle:
            self.assertEqual(handle.read(), "approved\n")

    def test_the_engine_cannot_grant_itself(self):
        result = self.run_boot(
            "first = attempt('README.md', 'x')\n"
            "code = first.split(':', 1)[1]\n"
            "try:\n"
            "    store.grant(code, 's-export')\n"
            "    print('granted')\n"
            "except Exception as e:\n"
            "    print(type(e).__name__)\n")
        self.assertEqual(result.stdout.strip(), "WriteBlockedError", result.stderr)
        self.assertEqual(_sha(self.readme), self.before)


if __name__ == "__main__":
    unittest.main()
