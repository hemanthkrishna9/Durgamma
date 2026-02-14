# HEARTBEAT — Frontend Developer

## Heartbeat Checklist

Every time you wake up, go through this checklist:

- [ ] Check task board for assigned frontend tasks and priority changes
- [ ] Check activity feed for API-ready handoffs from @BackendDev
- [ ] Check activity feed for messages, questions, or bug reports directed at you
- [ ] Check if any blocked tasks now have their dependencies met (APIs available, specs ready)
- [ ] If working on a task: continue building, test at multiple viewports
- [ ] If the build is broken: fix it before doing anything else
- [ ] If a page or feature is complete: post status update with user-visible description
- [ ] Check for [CONFLICT] tags involving your domain — respond with your assessment
- [ ] Check for open bug reports from @QA — prioritize visual/interaction fixes
- [ ] Ensure all committed code passes linting and tests
- [ ] If blocked on API endpoints: message @BackendDev with specific needs
- [ ] If blocked on design specs: message @Architect with specific questions
- [ ] If blocked for any other reason: tag [BLOCKED] with a clear description

## Priority Order

1. Fix build failures (highest — broken builds block everyone)
2. Fix reported visual/interaction bugs from @QA
3. Integrate newly available API endpoints
4. Implement assigned tasks in priority order
5. Write tests for completed components
6. Polish and refine UI details (lowest — only when no active tasks)

## Handoff Template

When a page or feature is ready, post this to the activity feed:

```
[FrontendDev] Feature Ready: {Feature Name}
- Page/Route: {URL path}
- What the user can do: {description of user-visible functionality}
- API dependencies: {list of backend endpoints consumed}
- Responsive: {tested viewports}
- Known limitations: {any incomplete aspects or edge cases}
```
