# Task Report Template

Copy this structure verbatim into the chat at the end of every meaningful implementation
task. Write `N/A` where a section genuinely does not apply — do not delete sections.

**Accuracy rules**

- Report what happened, not what was intended.
- Never write "tests passed" unless the tests were run in this session; include the output.
- Never write that a feature works unless it was verified; say how it was verified.
- If a step was skipped or scope was reduced, say so and say why.

---

```
TASK REPORT

1. Objective
   One or two sentences: what this task was asked to achieve.

2. Work Completed
   What was actually done, in order.

3. Files Created
   Full repo-relative paths, one per line. N/A if none.

4. Files Modified
   Path — what changed and why. N/A if none.

5. Files Deleted
   Path — why. N/A if none.

6. Features Implemented
   Feature — where it lives — whether it is user-reachable yet.

7. Architecture Changes
   What changed in architecture.md, and which ADR covers it. N/A if none.

8. Tests Performed
   Exact commands run.

9. Test Results
   Real output, pass/fail counts. If nothing was run, say "No tests run" and why.

10. Issues / Risks
    Discovered problems, open questions, new risks (with project_plan.md IDs).

11. Documentation Updated
    Which docs changed, including the dated development record path.

12. Project Plan Updated
    Which statuses moved, from what to what.

13. Git Status / Commit
    Branch, working tree state, commit SHA if one was made, whether anything was pushed.

14. Remaining Work
    What is left in this milestone.

15. Recommended Next Step
    The single next thing, stated as a proposal — not an action taken.
```
