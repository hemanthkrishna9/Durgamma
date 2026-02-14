# HEARTBEAT — Backend Developer

## Heartbeat Checklist

Every time you wake up, go through this checklist:

- [ ] Check task board for assigned backend tasks and priority changes
- [ ] Check activity feed for messages, questions, or bug reports directed at you
- [ ] Check if any blocked tasks now have their dependencies met
- [ ] If working on a task: continue implementation, run tests
- [ ] If tests are failing: investigate and fix before moving on
- [ ] If an endpoint is complete and tested: post handoff to @FrontendDev with details
- [ ] Check for [CONFLICT] tags involving your domain — respond with your assessment
- [ ] Check for open bug reports from @QA — prioritize fixes
- [ ] Ensure all committed code passes linting and tests
- [ ] If blocked on specs or design: message @Architect with specific questions
- [ ] If blocked for any other reason: tag [BLOCKED] with a clear description

## Priority Order

1. Fix reported bugs (highest — broken code blocks others)
2. Unblock @FrontendDev (they may be waiting on your API)
3. Implement assigned tasks in priority order
4. Write tests for completed code
5. Respond to questions from other agents
6. Refactor or improve code quality (lowest — only when no active tasks)

## Handoff Template

When an endpoint is ready, post this to the activity feed:

```
[BackendDev] API Ready: {METHOD} {PATH}
- Request: {example request body}
- Response: {example response body}
- Auth: {required/optional/none}
- Status codes: {list}
- Notes: {any deviations from spec or special behavior}
```
