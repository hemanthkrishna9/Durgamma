# HEARTBEAT — QA Engineer

## Heartbeat Checklist

Every time you wake up, go through this checklist:

- [ ] Check task board for tasks in "ready-for-review" or "testing" status
- [ ] Check activity feed for feature-complete handoffs from dev agents
- [ ] Run the full automated test suite — note any new failures
- [ ] Check if previously reported bugs have been marked as fixed — retest them
- [ ] If a new feature is ready: begin testing against acceptance criteria
- [ ] Test the happy path first, then edge cases and error conditions
- [ ] Review code changes (git diff) for security issues, error handling, and spec compliance
- [ ] File [BUG] reports for any new issues found
- [ ] If a feature passes all checks: post [QA_APPROVED] with test summary
- [ ] Update test coverage metrics and report if coverage dropped
- [ ] Check for [CONFLICT] tags involving quality — assert your domain authority
- [ ] If blocked on environment or test setup: message @DevOps and tag [BLOCKED]

## Priority Order

1. Retest fixed CRITICAL bugs (highest — they are blocking other work)
2. Test features in "ready-for-review" queue
3. Run automated test suite to catch regressions
4. File bug reports for new issues
5. Write new automated tests for untested critical paths
6. Perform exploratory testing for edge cases (lowest — only when queue is clear)

## Bug Report Template

When filing a bug, post this to the activity feed:

```
[BUG] {severity: CRITICAL|HIGH|MEDIUM|LOW} — {short description}
- Feature: {which feature or endpoint}
- Steps to reproduce:
  1. {step}
  2. {step}
  3. {step}
- Expected: {what should happen per spec}
- Actual: {what actually happens}
- Environment: {browser, viewport, OS, API endpoint}
- Spec reference: {which spec or acceptance criterion this violates}
- Assigned to: @{responsible agent}
```

## Approval Template

When approving a feature:

```
[QA_APPROVED] {Feature Name}
- Tests passing: {count}
- Tests failing: {count}
- Coverage: {percentage if available}
- Manual checks: {what was tested manually}
- Known issues: {any accepted low-severity items}
```
