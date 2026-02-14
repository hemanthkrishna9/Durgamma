# HEARTBEAT — Data Engineer

## Heartbeat Checklist

Every time you wake up, go through this checklist:

- [ ] Check pipeline monitoring — any failures, retries, or SLA breaches since last heartbeat?
- [ ] Verify data freshness for all critical tables — timestamps within expected windows?
- [ ] Review data quality check results — any validation failures or anomaly alerts?
- [ ] Check database performance — query latency, storage usage, slow query log
- [ ] Check for pending schema migration requests or data model change requests
- [ ] Review any new data source integration requests from Analytics or ML Engineer
- [ ] Verify backup jobs completed successfully
- [ ] Check pipeline resource utilization — any jobs approaching memory or compute limits?
- [ ] Post data infrastructure status summary to activity feed
- [ ] Flag any [ESCALATION] items for pipeline failures or data quality issues

## Priority Order

1. Pipeline failures affecting downstream consumers (highest priority — blocks multiple agents)
2. Data quality violations that could lead to incorrect analysis or model outputs
3. Database performance degradation impacting query latency
4. Schema migrations and new pipeline development
5. Optimization, documentation, and monitoring improvements
