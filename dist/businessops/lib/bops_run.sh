# The one place BusinessOps chooses a Python interpreter (ADR-0045, amending ADR-0042's
# invocation form only; ADR-0046 amends ADR-0045's Windows-suffix rule under WSL).
# Every command and skill reaches the engine as:
#
#     sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "<code>"
#
# and this script resolves an interpreter, then hands off unchanged to the ADR-0042 launcher:
#
#     exec <interpreter> -I "<plugin root>/lib/python/bops_run.py" -c "<code>"
#
# Why a shell script. The interpreter name cannot be chosen by Python, because choosing it is
# what has to happen before Python runs. The command bodies are already POSIX-shell blocks, so
# the shell is the one layer guaranteed to be present, and resolution belongs there. It lives
# here once rather than in 26 command and skill bodies (ADR-0042 requirement 5, centralised).
#
# What it does NOT do: no network access, no download, no package installation, no PATH export,
# no shell-profile change, no `cd`, and no interpreter of its own. It selects an existing one or
# fails with an actionable message.
#
# Security. The launcher path comes from this file's own location, never from the environment.
# Candidates are found by scanning PATH ourselves and considering only absolute PATH elements, so
# a `.` or empty element in PATH can never make a file in the working directory the interpreter.
# Every candidate must satisfy the version contract under `-I` before it is used, which also
# rejects anything that is not Python. The handoff keeps `-I`, so ADR-0042's isolation,
# PYTHONPATH and working-directory protections are untouched.
#
# Exit status 78 (EX_CONFIG) means no usable interpreter was found. The launcher's own failures
# keep its exit status 2, so the two are distinguishable. On success `exec` replaces this shell,
# so the engine's exit status, stdout, stderr and working directory are its own.
#
# POSIX shell only: no bashism, so `sh`, `bash`, `dash` and Git Bash all run it.

set -eu

# --- The minimum interpreter contract. CLAUDE.md section 4: Python 3.9+, standard library only.
BOPS_MIN_MAJOR=3
BOPS_MIN_MINOR=9

# --- The launcher, found from this script's own location and nothing else.
# --- The directory is taken by parameter expansion rather than `dirname`, and `cd`/`pwd` are
# --- shell built-ins, so this script needs no external command at all. That matters: with an
# --- unusable PATH, an external `dirname` would fail, the substitution would come back empty,
# --- and the launcher path would silently become working-directory-relative -- reintroducing
# --- exactly the class of defect M13-DEF-04 closed.
case $0 in
    */*) bops_self_dir=${0%/*} ;;
    *)   bops_self_dir=. ;;
esac
bops_lib=$(CDPATH= cd -- "$bops_self_dir" && pwd)
bops_launcher="$bops_lib/python/bops_run.py"

if [ ! -f "$bops_launcher" ]; then
    printf 'bops_run.sh: engine launcher not found at %s\n' "$bops_launcher" >&2
    printf 'bops_run.sh: this script must stay at <plugin root>/lib/bops_run.sh\n' >&2
    exit 78
fi

# --- Does one candidate satisfy the contract? Probed under -I so that no PYTHON* variable, user
# --- site directory or working directory can affect the answer. Output is discarded: a candidate
# --- may print anything, and only its exit status is trusted.
# --- The candidate must emit this exact marker. An exit status alone is not enough: a broken or
# --- hostile executable that exits 0 whatever it is given would pass a status-only check and then
# --- be handed the engine. Requiring the marker means the candidate really evaluated the version
# --- expression, so it is a Python that satisfies the contract and not merely something runnable.
BOPS_PROBE_MARKER=BOPS_RUNTIME_OK

bops_probe() {
    [ -f "$1" ] || return 1
    [ -x "$1" ] || return 1
    bops_probe_out=$("$1" -I -c 'import sys
sys.stdout.write("'"$BOPS_PROBE_MARKER"'" if sys.version_info[:2] >= ('"$BOPS_MIN_MAJOR"', '"$BOPS_MIN_MINOR"') else "unsupported")' 2>/dev/null) || return 1
    [ "$bops_probe_out" = "$BOPS_PROBE_MARKER" ] || return 1
    return 0
}

# --- An explicit, deliberate override: an absolute path to an interpreter the user chose. It is
# --- never silent (it is announced on stderr), it is validated like any other candidate, and it
# --- never falls back, so it cannot quietly redirect execution somewhere unintended.
if [ "${BOPS_PYTHON-}" != "" ]; then
    case "$BOPS_PYTHON" in
        /*|[A-Za-z]:[/\\]*) ;;
        *)
            printf 'bops_run.sh: BOPS_PYTHON must be an absolute path to a Python interpreter\n' >&2
            exit 78
            ;;
    esac
    if bops_probe "$BOPS_PYTHON"; then
        printf 'bops_run.sh: using the interpreter named by BOPS_PYTHON\n' >&2
        exec "$BOPS_PYTHON" -I "$bops_launcher" "$@"
    fi
    printf 'bops_run.sh: BOPS_PYTHON does not name a usable Python %s.%s or newer interpreter\n' \
        "$BOPS_MIN_MAJOR" "$BOPS_MIN_MINOR" >&2
    exit 78
fi

# --- Candidate names, in order. `python` first, which keeps ADR-0042's contract wherever it
# --- holds; then `python3`, for the platforms that ship Python 3 under that name only. A
# --- `python` that is Python 2 fails the probe and the search continues, so an old system does
# --- not stop at it. `py` is deliberately absent: it takes a version selector argument and so
# --- would need a different invocation shape. BOPS_PYTHON covers it and anything else exotic.
bops_names='python python3'
# --- Executable suffixes to try, in order. `-` is the sentinel for no suffix, so the bare Unix
# --- name is always tried first; the rest are the Windows ones, for Git Bash and similar shells
# --- where PATH holds Windows directories. A leading empty field cannot be written directly,
# --- because the shell drops it when the list is split into words.
bops_suffixes='- .exe .com .bat .cmd'

# --- Is this shell running inside WSL? Read from procfs with the `read` built-in, so the check
# --- needs no external command and cannot be steered by the environment. WSL 1 and WSL 2 both put
# --- "Microsoft" or "microsoft" in the kernel release string. A host with no readable osrelease is
# --- not Linux -- a native Windows shell has no procfs -- so the answer there is "not WSL", which
# --- leaves the Windows suffixes enabled and keeps that platform's behaviour unchanged.
bops_is_wsl=no
if [ -r /proc/sys/kernel/osrelease ]; then
    bops_osrelease=''
    read -r bops_osrelease < /proc/sys/kernel/osrelease || bops_osrelease=''
    case $bops_osrelease in
        *icrosoft*|*WSL*) bops_is_wsl=yes ;;
    esac
fi

# --- Under WSL a Windows suffix on PATH resolves through interop to a *Windows* interpreter, and
# --- that interpreter is not one for this engine: it passes the probe, because it really is Python
# --- 3.9 or newer, and then cannot open a Linux path -- it reads /mnt/d/... as D:\mnt\d\... and
# --- fails. The automatic search must therefore not offer it (M13-DEF-12, ADR-0046). Native
# --- candidates are unaffected, and BOPS_PYTHON can still name a Windows interpreter explicitly.
if [ "$bops_is_wsl" = yes ]; then
    bops_suffixes='-'
fi

bops_found=''
for bops_name in $bops_names; do
    # PATH is scanned here rather than with `command -v` so that only absolute elements are
    # considered. An empty, `.` or otherwise relative element is skipped, which is what stops a
    # file in the working directory from being chosen as the interpreter.
    bops_rest=$PATH
    while [ -n "$bops_rest" ]; do
        case $bops_rest in
            *:*) bops_dir=${bops_rest%%:*}; bops_rest=${bops_rest#*:} ;;
            *)   bops_dir=$bops_rest; bops_rest='' ;;
        esac
        case $bops_dir in
            /*|[A-Za-z]:[/\\]*) ;;
            *) continue ;;
        esac
        for bops_suffix in $bops_suffixes; do
            case $bops_suffix in
                -) bops_candidate="$bops_dir/$bops_name" ;;
                *) bops_candidate="$bops_dir/$bops_name$bops_suffix" ;;
            esac
            if bops_probe "$bops_candidate"; then
                bops_found=$bops_candidate
                break
            fi
        done
        [ -n "$bops_found" ] && break
    done
    [ -n "$bops_found" ] && break
done

if [ -n "$bops_found" ]; then
    exec "$bops_found" -I "$bops_launcher" "$@"
fi

# --- No usable interpreter. The message names what was looked for and what to do, and never
# --- prints PATH or any other environment value.
printf 'bops_run.sh: no usable Python interpreter found.\n' >&2
printf 'bops_run.sh: BusinessOps needs Python %s.%s or newer on PATH, as python or python3.\n' \
    "$BOPS_MIN_MAJOR" "$BOPS_MIN_MINOR" >&2
printf 'bops_run.sh: install Python %s.%s or newer, or set BOPS_PYTHON to the absolute path of an\n' \
    "$BOPS_MIN_MAJOR" "$BOPS_MIN_MINOR" >&2
printf 'bops_run.sh: existing interpreter, for example BOPS_PYTHON=/usr/bin/python3.\n' >&2
exit 78
