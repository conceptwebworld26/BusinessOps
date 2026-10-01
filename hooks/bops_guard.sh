# BusinessOps write guard: the Claude Code hook entry (ADR-0051).
#
# hooks/hooks.json runs this for PreToolUse, UserPromptSubmit and UserPromptExpansion:
#
#     sh "${CLAUDE_PLUGIN_ROOT}/hooks/bops_guard.sh" <event>
#
# with the event's JSON on stdin. The decision is made in Python, reached through the one
# interpreter resolver (lib/bops_run.sh, ADR-0045) and the one engine launcher
# (lib/python/bops_run.py --guard, ADR-0042), so the guard runs under the same isolation as the
# engine and needs no interpreter choice of its own.
#
# This file exists for one reason: to fail closed. Claude Code treats a hook that exits with a
# status other than 0 or 2 as a non-blocking error and runs the tool anyway. If the guard
# cannot start - no usable Python, a broken installation - a PreToolUse call is blocked with
# exit status 2 and a message saying why. A prompt is never blocked: when the guard cannot run
# no approval is granted, which is itself closed.
#
# POSIX shell only, no external command beyond the resolver it calls.

set -u

case ${1-} in
    pre-tool-use|user-prompt-submit|user-prompt-expansion) bops_event=$1 ;;
    *)
        printf 'bops_guard.sh: unknown event %s\n' "${1-}" >&2
        exit 2
        ;;
esac

case $0 in
    */*) bops_hooks_dir=${0%/*} ;;
    *)   bops_hooks_dir=. ;;
esac
bops_root=$(CDPATH= cd -- "$bops_hooks_dir/.." && pwd) || bops_root=

bops_status=0
bops_out=$(sh "$bops_root/lib/bops_run.sh" --guard "$bops_event") || bops_status=$?

if [ "$bops_status" -eq 0 ]; then
    if [ -n "$bops_out" ]; then
        printf '%s\n' "$bops_out"
    fi
    exit 0
fi

if [ "$bops_event" = pre-tool-use ]; then
    printf 'BusinessOps write guard could not start (exit status %s), so this tool call was blocked before it ran. BusinessOps needs Python 3.9 or newer (see the message above). To stop BusinessOps guarding this session, disable the plugin: claude plugin disable businessops\n' "$bops_status" >&2
    exit 2
fi
exit 0
