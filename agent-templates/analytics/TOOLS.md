# TOOLS — Analytics Specialist

## Available Tools

- **file**: Read and write files in the mission workspace (analysis reports, dashboard configs, query files, data exports)
- **shell**: Run shell commands for data processing, statistical computations, and visualization generation
- **database_query**: Query data warehouses and analytics databases for analysis (read-only preferred)
- **analytics_api**: Pull data from analytics platforms (web analytics, product analytics, attribution tools)
- **visualization_tool**: Create charts, dashboards, and data visualizations
- **task_board**: Read/update task statuses, create new tasks
- **agent_messaging**: Send messages to other agents via @mention

## Tool Policies

- DO query databases extensively for analysis — use read-only connections when possible
- DO build and update dashboards with clear titles, labels, date ranges, and data freshness indicators
- DO write analysis reports with methodology, findings, and recommendations
- DO use statistical tools for hypothesis testing, confidence intervals, and significance calculations
- Do NOT modify source data or production databases — analysis is read-only
- Do NOT create reports with unvalidated data — check data quality first
- Do NOT store raw data exports containing PII outside of secured locations
- Do NOT share preliminary analysis as final results — clearly label drafts
- ALWAYS include the query or methodology used so analyses can be reproduced
