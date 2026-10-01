"""M13-DEF-24 remediation (ADR-0051): the deterministic write classifier.

These tests prove the *classifier decision* only: which operations a tool call would perform
and whether each is free, needs approval or is prohibited. They do not prove that Claude Code
enforces the decision; that is runtime evidence, recorded separately in
`docs/development/2026-09-26-m13-def-24-hook-runtime-experiment.md`.

Every test works in a private temporary tree whose "scratch" directory is the only temporary
root, so the working directory is ordinary user space, as a real project folder is.
"""

import glob
import os
import re
import shutil
import tempfile
import unittest

from bops.writeguard import classify as K
from bops.writeguard import hook
from bops.writeguard import policy as P
from bops.writeguard import pyscan
from bops.writeguard import shell

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
#: BusinessOps M3 moved the M9-B harness from commands/ to dev/harness/ (ADR-0055); it is still
#: enumerated with the commands so every check keeps covering it at its new location.
LAUNCHER = os.path.join(REPO, "lib", "bops_run.sh")


class Workspace(unittest.TestCase):

    engaged = True

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="bops-def24-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.cwd = os.path.join(self.base, "work")
        self.scratch = os.path.join(self.base, "scratch")
        self.home = os.path.join(self.base, "home")
        self.guard = os.path.join(self.home, ".claude", "businessops", "guard")
        for d in (self.cwd, self.scratch, self.home, os.path.join(self.cwd, "sub"),
                  os.path.join(self.cwd, "reports")):
            os.makedirs(d)
        for name, text in (("README.md", "ORIGINAL\n"), ("file.txt", "x\n"),
                           ("source.txt", "s\n"), ("data.csv", "a,b\n1,2\n")):
            self.put(name, text)
        self.policy = P.Policy(self.cwd, home=self.home, plugin=REPO, temp_roots=[self.scratch],
                               guard=self.guard, engaged=self.engaged)

    def put(self, name, text):
        with open(os.path.join(self.cwd, name), "w") as handle:
            handle.write(text)

    def path(self, *parts):
        return os.path.join(self.cwd, *parts)

    def bash(self, command):
        return K.classify_tool_call("Bash", {"command": command}, self.policy)

    def tool(self, name, **tool_input):
        return K.classify_tool_call(name, tool_input, self.policy)

    def assertFree(self, result):
        self.assertEqual(result.decision, P.FREE, result)

    def assertApproval(self, result, kind=None, target=None):
        self.assertEqual(result.decision, P.APPROVAL, result)
        if kind is not None:
            self.assertIn((kind, target), [(op.kind, op.target) for op in result.operations],
                          result)

    def assertProhibited(self, result):
        self.assertEqual(result.decision, P.PROHIBITED, result)


class RequiredCases(Workspace):
    """The prompt's security cases 1-17, 22, 23 and 27, at the classifier."""

    def test_01_cat_file_is_read_only(self):
        result = self.bash("cat file.txt")
        self.assertFree(result)
        self.assertEqual(result.operations, [])

    def test_02_cat_redirect_overwrites(self):
        self.assertApproval(self.bash("cat > file.txt"), P.OVERWRITE, self.path("file.txt"))

    def test_03_cat_append(self):
        self.assertApproval(self.bash("cat >> file.txt"), P.APPEND, self.path("file.txt"))

    def test_04_echo_redirect(self):
        self.assertApproval(self.bash("echo hello > file.txt"), P.OVERWRITE, self.path("file.txt"))

    def test_05_printf_redirect(self):
        self.assertApproval(self.bash("printf '%s' x > file.txt"), P.OVERWRITE, self.path("file.txt"))

    def test_06_cp(self):
        self.assertApproval(self.bash("cp source.txt target.txt"), P.CREATE, self.path("target.txt"))
        self.assertApproval(self.bash("cp source.txt file.txt"), P.OVERWRITE, self.path("file.txt"))
        self.assertApproval(self.bash("cp source.txt sub"), P.CREATE, self.path("sub", "source.txt"))
        # A copy into the scratchpad is a working file, not a consequential write.
        self.assertFree(self.bash("cp source.txt %s/copy.txt" % self.scratch))

    def test_07_mv(self):
        result = self.bash("mv source.txt moved.txt")
        self.assertApproval(result, P.MOVE_SOURCE, self.path("source.txt"))
        self.assertApproval(result, P.CREATE, self.path("moved.txt"))

    def test_08_rm(self):
        self.assertApproval(self.bash("rm file.txt"), P.DELETE, self.path("file.txt"))
        self.assertApproval(self.bash("rm -rf sub"), P.DELETE, self.path("sub"))
        self.assertApproval(self.bash("rm *.txt"), P.UNKNOWN_WRITE, None)

    def test_09_python_open_write(self):
        result = self.bash("python3 -c \"open('f.txt', 'w').write('x')\"")
        self.assertApproval(result, P.CREATE, self.path("f.txt"))
        result = self.bash("python3 -c \"open('file.txt', 'w').write('x')\"")
        self.assertApproval(result, P.OVERWRITE, self.path("file.txt"))
        self.assertIn(P.EXECUTE, [op.kind for op in result.operations])

    def test_10_python_open_append(self):
        self.assertApproval(self.bash("python3 -c \"open('file.txt', 'a').write('x')\""),
                            P.APPEND, self.path("file.txt"))

    def test_11_truncate_equivalents(self):
        self.assertApproval(self.bash("python3 -c \"import os; os.truncate('file.txt', 0)\""),
                            P.TRUNCATE, self.path("file.txt"))
        self.assertApproval(self.bash("python3 -c \"open('file.txt', 'r+').truncate()\""))
        self.assertApproval(self.bash("truncate -s 0 file.txt"), P.TRUNCATE, self.path("file.txt"))
        self.assertApproval(self.bash(": > file.txt"), P.OVERWRITE, self.path("file.txt"))

    def test_12_write_tool(self):
        self.assertApproval(self.tool("Write", file_path=self.path("README.md"), content="x"),
                            P.OVERWRITE, self.path("README.md"))
        self.assertApproval(self.tool("Write", file_path=self.path("new.md"), content="x"),
                            P.CREATE, self.path("new.md"))

    def test_13_edit_tool(self):
        self.assertApproval(self.tool("Edit", file_path=self.path("README.md"), old_string="O",
                                      new_string="N"), P.MODIFY, self.path("README.md"))

    def test_14_multiedit_tool(self):
        self.assertApproval(self.tool("MultiEdit", file_path=self.path("README.md"),
                                      edits=[{"old_string": "O", "new_string": "N"}]),
                            P.MODIFY, self.path("README.md"))

    def test_15_notebookedit_tool(self):
        self.put("n.ipynb", "{}")
        self.assertApproval(self.tool("NotebookEdit", notebook_path=self.path("n.ipynb"),
                                      new_source="x"), P.MODIFY, self.path("n.ipynb"))

    def test_16_ambiguous_shell_fails_closed(self):
        for command in ("echo $(date) > log.txt", "cat `ls`", "awk '{print > \"o\"}' file.txt",
                        "eval \"$CMD\"", "bash script.sh", "ls | xargs rm", "curl -o x https://e",
                        "$EDITOR file.txt", "./run.sh", "(cd sub; rm file.txt)",
                        "diff <(cat a) b", "node -e 1", "perl -e 1", "make", "tar xf a.tar",
                        "sed -f script.sed file.txt", "find . -exec rm {} ;", "ls $HOME > out.txt",
                        "PATH=/tmp/evil cat file.txt", "if true; then rm x; fi"):
            with self.subTest(command=command):
                self.assertApproval(self.bash(command))
        self.assertApproval(self.tool("PowerShell", command="Get-ChildItem"))

    def test_17_read_with_shell_syntax_is_not_a_write(self):
        for command in ('grep ">" file.txt', "echo 'a > b'", "cat file.txt 2>&1 | head -5",
                        "cat file.txt > /dev/null", "ls -la && wc -l file.txt",
                        "cat <<'EOF'\n> not a redirect\nEOF\n", "find . -name '*.md'",
                        "git status && git diff && git log --oneline -3",
                        "python3 -c \"import json; print(json.dumps({'a': 1}))\"",
                        "sort file.txt | uniq -c", "grep -c x file.txt; echo done",
                        "head -n 5 data.csv  # > commented.txt", "wc -l < file.txt",
                        "cat file.txt 1>&2", 'echo "cost: \\$5 > budget"'):
            with self.subTest(command=command):
                self.assertFree(self.bash(command))

    def test_22_temp_file_plus_rename_is_caught_at_the_rename(self):
        staged = os.path.join(self.scratch, "t.md")
        self.assertFree(self.bash("cat > %s <<'EOF'\nnew\nEOF" % staged))
        self.assertApproval(self.bash("mv %s README.md" % staged), P.OVERWRITE, self.path("README.md"))
        self.assertApproval(self.bash("cp %s README.md" % staged), P.OVERWRITE, self.path("README.md"))
        self.assertApproval(self.bash("ln -sf %s README.md" % staged), P.LINK, self.path("README.md"))
        combined = self.bash("cat > %s <<'EOF'\nnew\nEOF\nmv %s README.md" % (staged, staged))
        self.assertApproval(combined, P.OVERWRITE, self.path("README.md"))

    def test_23_the_a20_write(self):
        command = "cat > README.md <<'EOF'\n# Sales summary\n\nRevenue ...\nEOF"
        result = self.bash(command)
        self.assertApproval(result, P.OVERWRITE, self.path("README.md"))
        [op] = result.operations
        self.assertTrue(op.exists)

    def test_27_git(self):
        self.assertFree(self.bash("git status"))
        self.assertApproval(self.bash("git commit -m 'x'"), P.GIT_COMMIT, None)
        self.assertApproval(self.bash("git push origin main"), P.GIT_PUSH, None)
        for command in ("git push --force", "git push -f origin main", "git push origin +main",
                        "git push origin :old", "git push --delete origin b",
                        "git push --force-with-lease", "git commit --amend -m x", "git rebase main",
                        "git branch -D feature", "git filter-branch"):
            with self.subTest(command=command):
                self.assertProhibited(self.bash(command))
        self.assertApproval(self.bash("git -c core.pager=sh log"))


class Zones(Workspace):

    def test_new_file_in_businessops_output_is_free_but_overwrite_is_not(self):
        self.assertFree(self.bash("mkdir -p businessops-output"))
        os.makedirs(self.path("businessops-output"))
        self.assertFree(self.tool("Write", file_path=self.path("businessops-output", "r.md"),
                                  content="x"))
        with open(self.path("businessops-output", "r.md"), "w") as handle:
            handle.write("x")
        self.assertApproval(self.tool("Write", file_path=self.path("businessops-output", "r.md"),
                                      content="y"), P.OVERWRITE, self.path("businessops-output", "r.md"))

    def test_the_approval_store_is_prohibited(self):
        os.makedirs(os.path.join(self.guard, "granted"))
        forged = os.path.join(self.guard, "granted", "BOPS-W-AAAAAAAA.json")
        self.assertProhibited(self.tool("Write", file_path=forged, content="{}"))
        self.assertProhibited(self.bash("echo {} > %s" % forged))
        self.assertProhibited(self.bash("rm -rf %s" % self.guard))
        self.assertProhibited(self.bash("mv %s/x.json %s" % (self.scratch, forged)))

    def test_the_plugin_may_not_change_itself_while_engaged(self):
        self.assertProhibited(self.tool("Write", file_path=os.path.join(REPO, "hooks", "hooks.json"),
                                        content="{}"))

    def test_original_source_data_is_immutable(self):
        self.assertProhibited(self.bash("echo 3,4 >> data.csv"))
        self.assertProhibited(self.bash("rm data.csv"))
        self.assertProhibited(self.tool("Write", file_path=self.path("data.csv"), content=""))
        self.assertFree(self.bash("cp data.csv %s/work.csv" % self.scratch))
        self.assertFree(self.bash("echo 5,6 >> %s/work.csv" % self.scratch))

    def test_after_cd_a_relative_target_is_unresolved(self):
        result = self.bash("cd reports && cat > summary.md")
        self.assertApproval(result, P.UNKNOWN_WRITE, None)
        self.assertApproval(self.bash("cd /tmp && echo x > %s" % self.path("file.txt")),
                            P.OVERWRITE, self.path("file.txt"))

    def test_tilde_resolves_against_the_trusted_home(self):
        self.assertApproval(self.bash("echo x > ~/notes.txt"), P.CREATE,
                            os.path.join(self.home, "notes.txt"))

    def test_a_symlink_is_resolved_to_its_target(self):
        os.symlink(self.path("README.md"), os.path.join(self.scratch, "innocent.md"))
        self.assertApproval(self.bash("echo x > %s/innocent.md" % self.scratch),
                            P.OVERWRITE, self.path("README.md"))


class TheEngine(Workspace):

    def engine(self, code, prefix=""):
        return self.bash('%ssh "%s" -c "%s"' % (prefix, LAUNCHER, code))

    def test_confined_engine_code_is_free_and_engages(self):
        result = self.engine("from bops import commands\nprint(commands.render(commands.run('sales-analysis', 'x.csv')))")
        self.assertTrue(result.engine)
        self.assertFree(result)

    def test_the_heredoc_form_is_read(self):
        result = self.bash('sh "%s" -c "$(cat <<\'PY\'\nfrom bops import commands\nprint(1)\nPY\n)"'
                           % LAUNCHER)
        self.assertTrue(result.engine)
        self.assertFree(result)

    def test_unconfined_engine_code_needs_approval(self):
        for code in ("import os\nos.remove('README.md')", "open('README.md', 'w')",
                     "from bops import commands\ncommands.x = 1",
                     "from bops.writeguard import capability", "getattr(print, 'x')"):
            with self.subTest(code=code):
                result = self.engine(code)
                self.assertTrue(result.engine)
                self.assertApproval(result, P.EXECUTE, None)

    def test_a_changed_environment_is_not_the_engine(self):
        self.assertApproval(self.engine("print(1)", prefix="HOME=/tmp/x "))
        self.assertApproval(self.engine("print(1)", prefix="BOPS_VERIFICATION_DIR=/x "))

    def test_the_guard_entry_is_prohibited_from_a_tool_call(self):
        self.assertProhibited(self.bash('sh "%s" --guard user-prompt-submit' % LAUNCHER))
        self.assertProhibited(self.bash('python3 -I "%s/lib/python/bops_run.py" --guard pre-tool-use'
                                        % REPO))

    def test_redirecting_engine_output_is_still_a_write(self):
        self.assertApproval(self.bash('sh "%s" -c "print(1)" > README.md' % LAUNCHER),
                            P.OVERWRITE, self.path("README.md"))

    def test_every_shipped_engine_block_is_confined(self):
        """Existing read-only commands and skills keep running without approval (case 26)."""
        blocks, parsed = 0, 0
        for path in sorted((glob.glob(os.path.join(REPO, "commands", "*.md"))
             + glob.glob(os.path.join(REPO, "dev", "harness", "*.md"))) +
                           glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md"))):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for body in re.findall(r"```bash\n(.*?)```", text, re.S):
                if "bops_run.sh" not in body:
                    continue
                blocks += 1
                command = body.replace("${CLAUDE_PLUGIN_ROOT}", REPO)
                result = self.bash(command)
                with self.subTest(path=os.path.relpath(path, REPO)):
                    self.assertTrue(result.engine)
                    code = shell.parse(command)[0].words[3].text
                    try:
                        compile(code, "<block>", "exec")
                    except SyntaxError:
                        continue          # a template with prose placeholders, filled by the model
                    parsed += 1
                    self.assertFree(result)
        # 34, plus the inline close each of the four research skills documents since M14-6 (ADR-0053).
        self.assertEqual(blocks, 38)
        self.assertGreaterEqual(parsed, 33)


class TheShellReader(unittest.TestCase):

    def test_unmodelled_constructs_raise(self):
        for command in ("echo `id`", "echo $(id)", "diff <(a) b", "(rm x)", "echo $((1+2))",
                        "cat <<EOF\n$(id)\nEOF\n", "case x in a) ;; esac", "echo 'open"):
            with self.subTest(command=command):
                with self.assertRaises(shell.ShellParseError):
                    shell.parse(command)

    def test_a_heredoc_body_is_data_not_commands(self):
        [cmd] = shell.parse("cat > out <<'EOF'\nrm -rf /\n> x\nEOF\n")
        self.assertEqual([w.text for w in cmd.words], ["cat"])
        self.assertEqual(cmd.redirects[1].body, "rm -rf /\n> x\n")

    def test_quotes_and_fds(self):
        [cmd] = shell.parse("grep '>' \"a b\" 2>&1")
        self.assertEqual([w.text for w in cmd.words], ["grep", ">", "a b"])
        self.assertTrue(cmd.redirects[0].dup)


class ThePythonScanner(unittest.TestCase):

    def test_confined_code(self):
        for code in ("import json, sys\nprint(json.dumps({'a': 1}))",
                     "from decimal import Decimal\nprint(Decimal('1.5') * 2)",
                     "text = open('a.txt', encoding='utf-8').read()"):
            with self.subTest(code=code):
                self.assertTrue(pyscan.is_confined(code))

    def test_unconfined_code(self):
        for code in ("import os", "open('a', 'w')", "f = open", "eval('1')", "x.__class__",
                     "print.__self__", "import subprocess", "json.x = 1", "from os import path",
                     "import sys\nsys.modules['x']", "getattr(json, 'loads')",
                     "vars()", "__import__('os')", "exec('1')", "def f(): pass\nf.__code__",
                     "from json import *", "open('a', mode=m)", "import sys\nsys.settrace(None)"):
            with self.subTest(code=code):
                self.assertFalse(pyscan.is_confined(code))

    def test_engine_confinement_admits_bops_but_not_the_guard(self):
        self.assertTrue(pyscan.is_confined("from bops import commands", engine=True))
        self.assertTrue(pyscan.is_confined("from bops.writeguard import export\n"
                                           "export.write_text('a', 'b')", engine=True))
        for code in ("from bops.writeguard import capability", "import bops.writeguard.engine",
                     "from bops import writeguard", "from bops.runtime import tiers\ntiers.os",
                     "from bops import _private", "from bops.writeguard.export import _write"):
            with self.subTest(code=code):
                self.assertFalse(pyscan.is_confined(code, engine=True))
        self.assertFalse(pyscan.is_confined("from bops import commands"))


class Outside(Workspace):
    """Not engaged: only the approval store is protected; ordinary work is not governed here."""

    engaged = False

    def test_the_plugin_is_editable_when_not_engaged(self):
        result = self.tool("Write", file_path=os.path.join(REPO, "hooks", "x.json"), content="{}")
        self.assertNotEqual(result.decision, P.PROHIBITED)

    def test_the_store_is_prohibited_even_when_not_engaged(self):
        self.assertProhibited(self.bash("touch %s/x" % self.guard))


class WindowsShellDevices(Workspace):
    """BOPS-R11: on native Windows a Bash device name is a device, not a new file.

    Git Bash maps `/dev/null` and the other POSIX device names to devices, but
    os.path.realpath() turns them into drive paths such as C:\\dev\\null. The classifier keeps the
    exact device names only for a Bash word on Windows. `classify._WINDOWS` is switched here so
    both platforms' handling is exercised on any host.
    """

    def windows(self, value):
        previous = K._WINDOWS
        K._WINDOWS = value
        self.addCleanup(setattr, K, "_WINDOWS", previous)

    def test_a_redirect_to_a_device_is_not_a_file_write_on_windows(self):
        self.windows(True)
        for command in ("ls x 2>/dev/null", "cat file.txt > /dev/null", "grep x file.txt 2>/dev/null | head -1",
                        "cat file.txt &>/dev/null", "echo x > /dev/stderr"):
            with self.subTest(command=command):
                self.assertFree(self.bash(command))

    def test_a_genuine_file_write_still_needs_approval_on_windows(self):
        self.windows(True)
        self.assertApproval(self.bash("echo x > notes.txt"), P.CREATE, self.path("notes.txt"))
        self.assertApproval(self.bash("echo x > README.md"))
        for near_miss in ("echo x > /dev/nullx", "echo x > /dev/null/x", "echo x > dev/null",
                          "echo x > C:/dev/null"):
            with self.subTest(command=near_miss):
                self.assertApproval(self.bash(near_miss))

    def test_a_file_tool_path_is_never_treated_as_a_device(self):
        """The Write tool on Windows would create C:\\dev\\null; only a shell word is a device."""
        self.windows(True)
        for tool in ("Write", "Edit", "MultiEdit"):
            with self.subTest(tool=tool):
                self.assertApproval(self.tool(tool, file_path="/dev/null", content="x"))

    def test_the_security_invariants_are_unchanged_on_windows(self):
        """The device branch decides nothing but a device word: every other decision is unchanged.

        Compared with the branch off rather than against fixed results, because the approval-store
        cases have separate, pre-existing Windows failures (`Zones.test_the_approval_store_is_
        prohibited`, `Outside.test_the_store_is_prohibited_even_when_not_engaged`) that BOPS-R11
        neither causes nor fixes. A device name beside a real target never hides that target.
        """
        cases = ("echo x > %s/x.json" % self.guard.replace("\\", "/"), "echo x > data.csv",
                 "tee /dev/null data.csv < file.txt", "cat file.txt > /dev/null; echo x > README.md",
                 "cp file.txt /dev/null README.md", "echo x > notes.txt", "rm file.txt 2>/dev/null")
        decisions = {}
        for value in (False, True):
            self.windows(value)
            decisions[value] = [self.bash(command).decision for command in cases]
        self.assertEqual(decisions[True], decisions[False])
        self.windows(True)
        self.assertProhibited(self.bash("echo x > data.csv"))
        self.assertProhibited(self.bash("tee /dev/null data.csv < file.txt"))
        self.assertApproval(self.bash("cat file.txt > /dev/null; echo x > README.md"))
        self.assertApproval(self.bash("rm file.txt 2>/dev/null"), P.DELETE, self.path("file.txt"))

    def test_other_platforms_keep_the_existing_resolution(self):
        """Off Windows the device branch is never taken: the result is exactly realpath()'s."""
        self.windows(False)
        expected = P.FREE if P.Policy.is_device(os.path.realpath("/dev/null")) else P.APPROVAL
        self.assertEqual(self.bash("cat file.txt > /dev/null").decision, expected)
        self.assertFree(self.bash("cat file.txt"))
        self.assertApproval(self.bash("echo x > notes.txt"))


class GuardMessages(Workspace):
    """BOPS-R12: the guard's user-facing text cites only documentation that ships with the plugin."""

    def test_block_messages_cite_the_shipped_readme_not_developer_documents(self):
        approval = self.bash("echo x > README.md").needing(P.APPROVAL)
        prohibited = self.bash("echo x > data.csv").needing(P.PROHIBITED)
        texts = [json_text for response in (hook.approval_response("Bash", approval, "BOPS-W-ABCD2345"),
                                            hook.prohibited_response("Bash", prohibited))
                 for json_text in (response["hookSpecificOutput"]["permissionDecisionReason"],
                                   response["systemMessage"])]
        texts += [op.reason for op in approval + prohibited]
        for text in texts:
            with self.subTest(text=text[:60]):
                for developer_only in ("CLAUDE.md", "architecture.md", "project_plan.md", "docs/development"):
                    self.assertNotIn(developer_only, text)
        self.assertIn("README", texts[0])
        self.assertIn("Approval and write safety", texts[0])

    def test_no_shipped_guard_string_names_a_developer_document(self):
        """Every string a guard module can emit; docstrings are developer text and are skipped."""
        import ast
        directory = os.path.join(REPO, "lib", "python", "bops", "writeguard")
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(directory, name), encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                          if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
                          and node.body and isinstance(node.body[0], ast.Expr)
                          and isinstance(node.body[0].value, ast.Constant)}
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and id(node) not in docstrings:
                    with self.subTest(module=name, text=node.value[:60]):
                        self.assertNotIn("CLAUDE.md", node.value)


if __name__ == "__main__":
    unittest.main()
