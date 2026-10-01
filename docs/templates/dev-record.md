# Development Record Template

Copy to `docs/development/YYYY-MM-DD-<slug>.md`. Use the ISO date the work was done.

If more than one meaningful milestone lands on the same date, use distinct slugs —
never append to or overwrite an existing record. To correct an earlier record, write a new
one and add a `Supersedes:` line; leave the original intact.

---

```markdown
# YYYY-MM-DD — <Milestone or task title>

**Milestone:** <n — name>
**Status on completion:** <PLANNED | IN PROGRESS | BLOCKED | REVIEW | COMPLETED>
**Supersedes:** <path, or None>

## 1. Prompt / task performed
Verbatim or faithfully summarised request.

## 2. Objective
What this task set out to achieve.

## 3. Changes made
Narrative of the work, in the order it happened.

## 4. Files created
## 5. Files modified
## 6. Files deleted

## 7. Features implemented
Feature — location — user-reachable yet?

## 8. Tests performed
Exact commands.

## 9. Test results
Real output. "No tests run" plus the reason, if none.

## 10. Issues discovered
Including anything deferred, with an ID if it entered project_plan.md.

## 11. Decisions made
Link to any ADR created.

## 12. Architecture changes
What changed in architecture.md, or None.

## 13. Project-plan updates
Status transitions.

## 14. Documentation updates
## 15. Remaining work
## 16. Git commit reference
Branch, SHA, pushed or not. N/A if no commit.
```
