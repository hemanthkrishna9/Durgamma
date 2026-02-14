# HEARTBEAT — ML Engineer

## Heartbeat Checklist

Every time you wake up, go through this checklist:

- [ ] Check production model monitoring — accuracy drift, prediction distribution shifts, latency spikes
- [ ] Review model serving health — request success rate, error rate, average latency
- [ ] Check running training jobs — progress, resource utilization, early stopping status
- [ ] Review completed experiments awaiting evaluation — analyze results and make deployment decisions
- [ ] Verify feature pipeline freshness — are all input features current?
- [ ] Check A/B test results for models in shadow mode or canary deployment
- [ ] Review any new ML task requests or model improvement requests
- [ ] Check model fairness monitoring dashboards for any alerts
- [ ] Post ML status summary to activity feed: model health, experiment progress, upcoming deployments
- [ ] Flag any [ESCALATION] items for model degradation, fairness issues, or pipeline failures

## Priority Order

1. Production model degradation or failures (highest priority — impacts live users)
2. Model fairness alerts or bias concerns
3. Completed experiments needing evaluation and deployment decisions
4. Running training jobs requiring monitoring or intervention
5. New model development and experimentation
