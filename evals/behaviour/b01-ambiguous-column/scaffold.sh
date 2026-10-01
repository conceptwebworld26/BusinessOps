# Stages this case's declared input into the eval sandbox. ADR-0039 F.6: a scaffold script
# does nothing but copy repository synthetic inputs into the scaffold directory, and E.5
# asserts it. tests/unit/test_m13_eval_cases.Scaffold is that assertion.
#
# The harness runs this as `bash <this file>` with the working directory set to the run's own
# directory, and an environment that does not include CLAUDE_PLUGIN_ROOT, so the repository
# root is derived from this file's own location: no absolute path is written down.
#
# Why it is needed: the prompt names `tests/fixtures/eval_inputs/s3_01_monthly_amounts.csv`, a path relative to the repository. The run's
# working directory is not the repository, so without this copy the path does not resolve and
# the case cannot reach the behaviour it tests (M13-DEF-07).
#
# It performs no network access, starts no server, calls no MCP tool, authenticates to
# nothing, runs no interpreter, and writes nothing outside the run's working directory.
set -eu
repo=$(cd "$(dirname "$0")/../../.." && pwd)
mkdir -p tests/fixtures/eval_inputs
cp "$repo/tests/fixtures/eval_inputs/s3_01_monthly_amounts.csv" tests/fixtures/eval_inputs/s3_01_monthly_amounts.csv
