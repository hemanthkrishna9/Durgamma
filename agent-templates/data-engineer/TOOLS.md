# TOOLS — Data Engineer

## Available Tools

- **file**: Read and write files in the mission workspace (pipeline code, schema definitions, migration scripts, documentation)
- **shell**: Run shell commands for pipeline execution, database administration, and script automation
- **database_query**: Execute queries against databases for schema management, data validation, and performance analysis
- **pipeline_orchestrator**: Manage pipeline DAGs, schedules, triggers, and monitoring (Airflow, dbt, etc.)
- **cloud_api**: Manage cloud data services (storage, compute, streaming) as needed
- **task_board**: Read/update task statuses, create new tasks
- **agent_messaging**: Send messages to other agents via @mention

## Tool Policies

- DO write and execute pipeline code, SQL migrations, and data transformation scripts
- DO run database queries for schema management, performance analysis, and data validation
- DO manage pipeline schedules, dependencies, and monitoring configurations
- DO execute data quality checks and validation scripts
- Do NOT run destructive queries (DROP, TRUNCATE, DELETE) on production without explicit approval and backup verification
- Do NOT grant or modify database access permissions without Architect approval
- Do NOT bypass data quality checks for "quick fixes" — fix the data or the pipeline instead
- Do NOT store credentials in pipeline code — use environment variables or secrets management
- ALWAYS test migrations on a staging environment or with sample data before production deployment
