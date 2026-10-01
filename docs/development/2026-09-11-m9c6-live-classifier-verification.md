# 2026-09-11 — M9-C.6: live classifier verification and policy-question record

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.6, supplementary)
**Status on completion:** `COMPLETED`
**Supersedes:** None. **Extends**
`docs/development/2026-09-11-m9c6-tier-classifier-hardening.md`, which remains the record of
the fix itself. That record stated live re-verification was not required; the owner
subsequently asked for a minimal live check, so this record adds it rather than editing the
earlier one.

---

## 1. Prompt / task performed

The M9-C.6 brief was re-issued with two additions to the work already completed: perform a
**minimal live verification** of source-classification behaviour, and record the
whole-namespace trust question as a **separate policy question** rather than changing it.
Explicitly out of scope: the scout output-formatting issue, which must stay unfixed and
fail-closed; and any sibling skill or command.

## 2. What was already done

The fix itself landed in the preceding task and is unchanged here: `_matches_domain()`,
hardened `_host()`, both elevation loops switched from substring to label-boundary matching,
and four bare keyword fragments removed. 39 focused tests, 601 M9 tests, 1,764 full suite.
See the primary record.

This task adds only the live check, the policy-question record, and two documentation
clarifications.

## 3. Live verification

One narrow Tier-0 retrieval, gated normally, dispatched once:

```
query      logistics 2026 gross margin benchmark
gate       ALLOW / tier 0 / failed_checks []
dispatch   businessiq:biq-research-scout x1  (6 tool uses, 80s)
```

**Scope was classification only.** No evidence set was built and no analysis produced,
because doing so would have required compensating for the scout's output formatting — which
this milestone is forbidden to touch.

### Classification of the hostnames the retrieval actually returned

| Host | Tier | `inferred` |
|---|---|---|
| `csimarket.com` | C | True |
| `www.eaglerockcfo.com` | C | True |
| `www.clearlyacquired.com` (HTTP 403, not retrieved) | C | True |

All three correctly unrecognised, each with the honest basis string — *"not on the recognised
A or B lists; classified C (corroboration only) rather than assumed authoritative."*

**The honest limitation of this check: it did not exercise the defect.** None of the three
hostnames contains a trusted substring, so the old and new rules agree on all of them. This
was verified by simulating the old rule against the same hosts — identical results. The live
check confirms the classifier behaves correctly on real, unchosen hostnames; it is **not**
independent evidence that the vulnerability is closed.

### Where the real live evidence is

The M9-C.5 corpus did exercise it, and those are real hostnames from a real retrieval:

| Host | Before | After |
|---|---|---|
| `www.microsoft.com` | **B** via `ft.com` | **C** |
| `news.microsoft.com` | **B** via `ft.com` | **C** |
| `www.sec.gov` | A | A |
| `www.microteklearning.com`, `finance.yahoo.com`, `en.wikipedia.org` | C | C |

That corpus is pinned deterministically by `TestTheLiveRegressionCase`, so it re-runs on
every suite execution rather than depending on a live retrieval.

### Fail-closed behaviour confirmed, uncompensated

The scout again returned fenced JSON wrapped in trailing prose. As instructed, this was **not**
worked around. Fed to the parser as received:

```
records = []   failure = ResearchFailure(unavailable/retrieval_unavailable)
```

Fail-closed preserved. The formatting issue remains open and untouched, for the separate
milestone.

## 4. Files created

- `docs/development/2026-09-11-m9c6-live-classifier-verification.md` — this record

## 5. Files modified

| File | Change |
|---|---|
| `project_plan.md` | New known-issue row **R-11**, the namespace policy question |
| `reference/research-policy.md` | Two clarifications: boundary matching is an implementation correction rather than a policy change; and host trust is separate from path logic |

No implementation code, test, skill, command, agent or ADR was modified in this task.

## 6. Files deleted

None.

## 7. Features implemented

None. Verification and documentation.

## 8. Tests performed

```bash
PYTHONPATH=lib/python python -m unittest tests.negative.test_m9c6_tier_boundary
PYTHONPATH=lib/python python -m unittest <all thirteen M9 suites>
python tests/run_tests.py
```

## 9. Test results

```
focused (M9-C.6)   Ran 39 tests    OK
all M9 suites      Ran 601 tests   OK
full regression    Ran 1764 tests in 269.711s   OK (skipped=19)
                   ran 1764 | failures 0 | errors 0 | skipped 19
```

**0 failures, 0 errors, 19 skips** — the same pre-existing skip set, unchanged since M8.

## 10. Issues discovered

**R-11, recorded not fixed.** `TIER_A_PATTERNS` elevates the whole `.gov`, `.gov.uk`, `.mil`
and `.europa.eu` namespaces, and `TIER_B_PATTERNS` the whole of `.ac.uk` and `.edu` — not
merely the named institutions inside them. A student page under a university domain therefore
carries the same tier as that university's research office. M9-C.6 corrected *how* patterns
match; *which* namespaces are trusted is a policy decision for the owner, and changing it
under a security fix would be the same silent-broadening error in reverse.

**The live check is weaker evidence than the deterministic regression**, and §3 says so
plainly rather than presenting a passing live run as proof the vulnerability is closed.

## 11. Decisions made

**No ADR**, unchanged from the primary record and re-examined against the brief's explicit
prompt. This fix introduces no new load-bearing decision: the security property — a source
cannot assert its own tier — is stated in `reference/research-policy.md`, in ADR-0009 and in
the classifier's own comment. The implementation failed to enforce it; enforcing it is a bug
fix, which the ADR bar excludes by name.

R-11 is the decision that *would* need an ADR, and it has deliberately not been taken.

## 12. Architecture changes

None in this task. The architecture paragraph was added in the primary M9-C.6 task.

## 13. Project-plan updates

One row: **R-11** in Known issues. The M9-C.6 completion row was added in the primary task
and is unchanged. **M9-C.5 keeps its `APPROVED WITH LIMITATIONS` verdict.**

## 14. Documentation updates

`reference/research-policy.md` now states that boundary matching is an implementation
correction rather than a change to the tier policy, points at R-11 for the open question, and
separates host trust from path logic — a host is not the SEC because its URL contains
`edgar`, though a genuine SEC filing under `/Archives/edgar/` is fine once the host is
trusted.

## 15. Remaining work

1. **Scout output formatting** — the live scout still wraps its envelope in prose despite
   M9-C.1. Untouched here by instruction; its own milestone, after this fix is reviewed.
2. **R-11** — the namespace policy question, for the owner.
3. **The three sibling skills** and **M9-D** — not started, and not started here.

## 16. Git commit reference

N/A. Branch `main`, no commit created, nothing staged, nothing pushed.

**Final status: `M9-C.6 COMPLETED`, live verification performed with its limitation stated.**
