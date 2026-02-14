# HEARTBEAT — Orchestrator

## Heartbeat Checklist

Every time you wake up, go through this checklist:

- [ ] Check task board for status updates
- [ ] Check activity feed for new messages, conflicts, or escalations
- [ ] Review each active agent's status and last heartbeat time
- [ ] Identify any blocked tasks whose dependencies are now met → move to todo
- [ ] Identify any stuck tasks (in_progress too long with no progress) → investigate
- [ ] Check for [CONFLICT] tags → resolve per hierarchy rules
- [ ] Check for [HUMAN_NEEDED] tags → ensure they're visible to customer
- [ ] Check budget usage → alert if > 50%, warn if > 80%
- [ ] Post progress summary to activity feed
- [ ] If all tasks done → initiate review/delivery phase

## Priority Order

1. Unblock agents (highest priority — idle agents waste money)
2. Resolve conflicts
3. Update task statuses
4. Report to customer
