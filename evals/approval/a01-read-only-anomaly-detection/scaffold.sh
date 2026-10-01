# Stages this case's declared input into the eval sandbox. ADR-0039 F.6: a scaffold script
# does nothing but copy repository synthetic inputs into the scaffold directory, and E.5
# asserts it. tests/unit/test_m13_eval_cases.Scaffold is that assertion.
#
# Claude Code 2.1.278 runs this as `bash <this file>` with the working directory set to the
# run's own directory, and an environment of PATH, HOME, TMPDIR, TERM, GIT_CONFIG_NOSYSTEM,
# USER_TYPE and NODE_ENV only. CLAUDE_PLUGIN_ROOT is not among them, so the repository root
# is derived from this file's own location: no absolute path is written down.
#
# Why it is needed: the prompt names `assets/demo-data/northwind_sales.csv`, a path relative
# to the repository. The run's working directory is not the repository, so without this copy
# the path does not resolve and the case cannot reach the command it tests (M13-DEF-07).
#
# It performs no network access, starts no server, calls no MCP tool, authenticates to
# nothing, runs no interpreter, and writes nothing outside the run's working directory.
set -eu
repo=$(cd "$(dirname "$0")/../../.." && pwd)
mkdir -p assets/demo-data
cp "$repo/assets/demo-data/northwind_sales.csv" assets/demo-data/northwind_sales.csv
