# -*- coding: utf-8 -*-
"""The local `recompute` MCP server (ADR-0035 section 3), driven as a real stdio subprocess.

The server is a transport: one tool, one closed argument, one closed envelope. Most tests start the
module directly (`<python> lib/python/bops/verification_server.py`), speak JSON-RPC to it, and check
what crosses the pipe - and that nothing reaches stderr, which Claude Code copies into its debug log.
`DeclaredEntry` starts it exactly as `.mcp.json` does since ADR-0052 (`sh lib/bops_run.sh
--verifier`), on a PATH that offers `python3` and no `python`: the host shape R-13 could not start.

**Every fixture is synthetic.** Requests and records go to a temporary directory, removed afterwards.
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"), os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import commands as C                              # noqa: E402
from bops import executive_report as E                      # noqa: E402
from bops import verification as V                          # noqa: E402
from bops import verification_server as server_mod          # noqa: E402
from bops.commands import runner as runner_mod              # noqa: E402
from unit import test_m10_3_2_strategy as F                # noqa: E402

SERVER = os.path.join(REPO_ROOT, "lib", "python", "bops", "verification_server.py")
MCP_JSON = os.path.join(REPO_ROOT, ".mcp.json")
ENVELOPE_KEYS = {"protocol", "request_id", "status", "record_id", "error_code"}


class Server(object):
    """One server session: send messages, collect responses and stderr."""

    def __init__(self, directory):
        self.directory = directory

    def exchange(self, *messages):
        env = dict(os.environ, **{V.ENV_DIRECTORY: self.directory})
        lines = [{"jsonrpc": "2.0", "id": 0, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18"}},
                 {"jsonrpc": "2.0", "method": "notifications/initialized"}] + list(messages)
        proc = subprocess.run([sys.executable, SERVER], input="\n".join(
            json.dumps(m) for m in lines) + "\n", capture_output=True, text=True,
            encoding="utf-8", env=env, cwd=self.directory, timeout=600)
        responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        return responses, proc.stderr, proc.stdout

    def call(self, arguments, name="recompute"):
        responses, stderr, stdout = self.exchange({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                                                   "params": {"name": name,
                                                              "arguments": arguments}})
        return responses[-1], stderr, stdout


class RecomputeServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m11-server-")
        cls.previous = os.environ.get(V.ENV_DIRECTORY)
        os.environ[V.ENV_DIRECTORY] = cls.directory
        cls.server = Server(cls.directory)
        synthesis = F.strict_set()
        C.kpi_statements(synthesis, F.shared_run(), F.DATASET_ID)
        cls.synthesis = synthesis
        cls.report = E.build(synthesis, {})
        cls.request_id = V.issue_recomputation(cls.report)
        cls.request_path = os.path.join(cls.directory, "requests", cls.request_id + ".json")
        cls.request_bytes = io.open(cls.request_path, "rb").read()

    @classmethod
    def tearDownClass(cls):
        if cls.previous is None:
            os.environ.pop(V.ENV_DIRECTORY, None)
        else:
            os.environ[V.ENV_DIRECTORY] = cls.previous
        shutil.rmtree(cls.directory, ignore_errors=True)

    def setUp(self):
        with io.open(self.request_path, "wb") as handle:
            handle.write(self.request_bytes)

    def envelope(self, response):
        content = response["result"]["content"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["type"], "text")
        self.assertFalse(response["result"]["isError"])
        body = json.loads(content[0]["text"])
        self.assertEqual(set(body), ENVELOPE_KEYS)
        self.assertEqual(body["protocol"], "bops.verifier.result/1")
        return body, content[0]["text"]

    def assert_clean(self, text, stderr):
        self.assertEqual(stderr, "", "the server writes nothing to stderr")
        lowered = text.lower()
        for leak in ("northwind", "sales.csv", "demo-data", "traceback", "error:", "exception",
                     self.directory.lower().replace("\\", "\\\\"), "sha256:"):
            self.assertNotIn(leak, lowered)
        for result in self.synthesis.registered_kpis():
            # Short values such as "0" occur inside any hex id; distinctive figures are checked.
            if result.available and len(str(result.value)) >= 5:
                self.assertNotIn(str(result.value), text)

    # -- protocol -------------------------------------------------------------------------

    def test_it_initialises_without_instructions_and_lists_exactly_one_tool(self):
        responses, stderr, _out = self.server.exchange(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        initialise, listing = responses[0]["result"], responses[1]["result"]
        self.assertNotIn("instructions", initialise)
        self.assertEqual(initialise["serverInfo"]["name"], "bops-verifier")
        self.assertEqual(initialise["capabilities"], {"tools": {}})
        self.assertEqual([t["name"] for t in listing["tools"]], ["recompute"])
        self.assertEqual(listing["tools"][0]["inputSchema"], {
            "type": "object", "additionalProperties": False, "required": ["request_id"],
            "properties": {"request_id": {"type": "string", "pattern": "^rcq-[0-9a-f]{16}$"}}})
        self.assertEqual(stderr, "")

    def test_the_tool_carries_annotations_that_match_its_behaviour(self):
        """BusinessOps M3: the directory policy asks for readOnlyHint, destructiveHint and title.

        `recompute` creates a new record file (create-only), so it is neither read-only nor
        destructive, and it never opens a network connection.
        """
        responses, _stderr, _out = self.server.exchange(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        annotations = responses[1]["result"]["tools"][0]["annotations"]
        self.assertEqual(annotations, {"title": "Recompute a BusinessOps verification request",
                                       "readOnlyHint": False, "destructiveHint": False,
                                       "openWorldHint": False})

    def test_a_valid_request_completes_and_writes_only_a_digest_record(self):
        response, stderr, _out = self.server.call({"request_id": self.request_id})
        body, text = self.envelope(response)
        self.assertEqual((body["request_id"], body["status"], body["error_code"]),
                         (self.request_id, "completed", None))
        self.assertRegex(body["record_id"], r"^rcr-[0-9a-f]{16}$")
        self.assert_clean(text, stderr)
        record_path = os.path.join(self.directory, "records", body["record_id"] + ".json")
        record = io.open(record_path, encoding="utf-8").read()
        for result in self.synthesis.registered_kpis():
            if result.available:
                self.assertNotIn('"%s"' % result.value, record)
        # the in-process verifier accepts the transported envelope
        self.assertTrue(V.verify(self.report, text).passed)

    def test_every_non_id_argument_is_refused_before_any_file_is_opened(self):
        valid = self.request_id
        cases = [
            {"request_id": valid, "source_path": F.DEMO},
            {"request_id": valid, "path": "/etc/passwd"},
            {"request_id": valid, "command": "cat sales.csv"},
            {"request_id": valid, "url": "https://example.com"},
            {"request_id": valid, "figure": "171450.93"},
            {"request_id": valid, "config": {"materiality": 1}},
            {"request_id": valid, "dataset_id": "ds-1"},
            {"request_id": "../requests/%s" % valid},
            {"request_id": "..\\..\\" + valid},
            {"request_id": valid + "; cat sales.csv"},
            {"request_id": "$(cat sales.csv)"},
            {"request_id": F.DEMO},
            {"request_id": valid.upper()},
            {"request_id": 12345},
            {"request_id": None},
            {},
            [valid],
            valid,
        ]
        for arguments in cases:
            response, stderr, _out = self.server.call(arguments)
            body, text = self.envelope(response)
            self.assertEqual((body["status"], body["error_code"], body["record_id"]),
                             ("failed", "request_id_invalid", None), arguments)
            self.assert_clean(text, stderr)

    def test_an_unknown_tool_gets_a_fixed_protocol_error(self):
        for name in ("read_file", "Bash", "recompute ", None):
            response, stderr, _out = self.server.call({"request_id": self.request_id}, name=name)
            self.assertEqual(response["error"], {"code": -32602, "message": "invalid params"})
            self.assertEqual(stderr, "")

    def test_unknown_forged_or_altered_requests_are_refused(self):
        response, stderr, _o = self.server.call({"request_id": "rcq-" + "a" * 16})
        self.assertEqual(self.envelope(response)[0]["error_code"], "request_not_found")
        with io.open(self.request_path, "ab") as handle:
            handle.write(b" ")
        response, stderr, _o = self.server.call({"request_id": self.request_id})
        self.assertEqual(self.envelope(response)[0]["error_code"], "request_invalid")
        # a well-formed request pointing at another file, filed under the original id
        request = json.loads(self.request_bytes.decode("utf-8"))
        request["runs"][0]["source_path"] = os.path.join(self.directory, "other.csv")
        with io.open(self.request_path, "wb") as handle:
            handle.write(runner_mod.canonical_json(request).encode("utf-8"))
        response, stderr, _o = self.server.call({"request_id": self.request_id})
        body, text = self.envelope(response)
        self.assertEqual(body["error_code"], "request_digest_mismatch")
        self.assert_clean(text, stderr)

    def test_an_internal_failure_returns_a_code_and_no_text(self):
        request = json.loads(self.request_bytes.decode("utf-8"))
        request["runs"][0]["command_id"] = "not-a-command"
        del request["request_id"]
        request_id = V._content_address("rcq-", request, 16)
        request = {"protocol": request["protocol"], "request_id": request_id,
                   "runs": request["runs"]}
        path = os.path.join(self.directory, "requests", request_id + ".json")
        with io.open(path, "wb") as handle:
            handle.write(runner_mod.canonical_json(request).encode("utf-8"))
        response, stderr, stdout = self.server.call({"request_id": request_id})
        body, text = self.envelope(response)
        self.assertEqual((body["status"], body["error_code"]), ("failed", "execution_error"))
        self.assert_clean(stdout, stderr)
        self.assertNotIn("not-a-command", stdout)

    # -- the code itself ---------------------------------------------------------------------

    def test_the_server_is_a_transport_with_no_network_or_shell(self):
        with io.open(SERVER, encoding="utf-8") as handle:
            body = handle.read()
        for token in ("socket", "urllib", "http.client", "requests", "subprocess", "os.system",
                      "popen", "eval(", "exec(", "print(", "sys.stderr.write", "instructions"):
            if token == "instructions":
                self.assertNotIn('"instructions"', body)
                continue
            self.assertNotIn(token, body, token)
        self.assertEqual(server_mod.TOOL["name"], "recompute")
        self.assertEqual(len(re.findall(r'"name":', json.dumps(server_mod.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})))), 1)

    def test_mcp_json_declares_exactly_the_approved_entry(self):
        """ADR-0035's server, launched through the ADR-0045 resolver as ADR-0052 declares."""
        with io.open(MCP_JSON, encoding="utf-8") as handle:
            declared = json.load(handle)
        self.assertEqual(declared, {"mcpServers": {"bops-verifier": {
            "type": "stdio", "command": "sh",
            "args": ["${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh", "--verifier"]}}})


#: A `python3` that is the real interpreter under another name. It is the only interpreter on the
#: PATH the declared entry is given, so the server can start only if the resolver finds `python3`.
PYTHON3_STUB = '#!/bin/sh\nexec "{real}" "$@"\n'


@unittest.skipUnless(shutil.which("sh"), "the declared entry runs the POSIX-shell resolver")
class DeclaredEntry(unittest.TestCase):
    """R-13: the server as `.mcp.json` declares it, on a host that has `python3` but no `python`."""

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m11-declared-")
        cls.previous = os.environ.get(V.ENV_DIRECTORY)
        os.environ[V.ENV_DIRECTORY] = cls.directory
        synthesis = F.strict_set()
        C.kpi_statements(synthesis, F.shared_run(), F.DATASET_ID)
        cls.synthesis = synthesis
        cls.request_id = V.issue_recomputation(E.build(synthesis, {}))
        cls.bin = os.path.join(cls.directory, "bin")
        os.makedirs(cls.bin)
        stub = os.path.join(cls.bin, "python3")
        with open(stub, "w", encoding="ascii", newline="\n") as handle:
            handle.write(PYTHON3_STUB.format(real=os.path.realpath(sys.executable)))
        os.chmod(stub, 0o755)

    @classmethod
    def tearDownClass(cls):
        if cls.previous is None:
            os.environ.pop(V.ENV_DIRECTORY, None)
        else:
            os.environ[V.ENV_DIRECTORY] = cls.previous
        shutil.rmtree(cls.directory, ignore_errors=True)

    def declared_command(self):
        with io.open(MCP_JSON, encoding="utf-8") as handle:
            entry = json.load(handle)["mcpServers"]["bops-verifier"]
        self.assertEqual(entry["command"], "sh")
        # The platform substitutes the plugin root; the shell is spawned by absolute path because
        # the PATH handed to it deliberately holds nothing but the python3 stub.
        return [shutil.which("sh")] + [a.replace("${CLAUDE_PLUGIN_ROOT}", REPO_ROOT)
                                       for a in entry["args"]]

    def exchange(self, *messages):
        env = {"PATH": self.bin, V.ENV_DIRECTORY: self.directory,
               "HOME": os.environ.get("HOME", self.directory)}
        lines = [{"jsonrpc": "2.0", "id": 0, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18"}},
                 {"jsonrpc": "2.0", "method": "notifications/initialized"}] + list(messages)
        proc = subprocess.run(self.declared_command(), input="\n".join(
            json.dumps(m) for m in lines) + "\n", capture_output=True, text=True,
            encoding="utf-8", env=env, cwd=self.directory, timeout=600)
        responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        return proc, responses

    def test_the_path_offers_python3_and_no_python(self):
        self.assertEqual(sorted(os.listdir(self.bin)), ["python3"])

    def test_the_declared_entry_starts_and_lists_exactly_one_tool(self):
        proc, responses = self.exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "bops-verifier")
        self.assertNotIn("instructions", responses[0]["result"])
        self.assertEqual([t["name"] for t in responses[1]["result"]["tools"]], ["recompute"])

    def test_the_declared_entry_completes_a_real_recomputation(self):
        proc, responses = self.exchange({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                                         "params": {"name": "recompute",
                                                    "arguments": {"request_id": self.request_id}}})
        self.assertEqual(proc.stderr, "")
        body = json.loads(responses[-1]["result"]["content"][0]["text"])
        self.assertEqual(set(body), ENVELOPE_KEYS)
        self.assertEqual((body["request_id"], body["status"], body["error_code"]),
                         (self.request_id, "completed", None))

    def test_the_verifier_entry_takes_no_argument_and_runs_no_code(self):
        """`--verifier` is exact: extra arguments are refused as usage, never passed on."""
        proc = subprocess.run(self.declared_command() + ["-c", "print(1)"],
                              capture_output=True, text=True, encoding="utf-8",
                              env={"PATH": self.bin}, cwd=self.directory, timeout=120,
                              stdin=subprocess.DEVNULL)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertIn("usage:", proc.stderr)


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
