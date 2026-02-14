# TOOLS — Email Marketing Specialist

## Available Tools

- **file**: Read and write files in the mission workspace (sequence designs, campaign briefs, performance reports)
- **shell**: Run shell commands for data processing, list management scripts, and automation
- **email_platform_api**: Manage campaigns, sequences, segments, and templates in the email service provider
- **analytics_api**: Pull email performance data, conversion tracking, and engagement metrics
- **database_query**: Query subscriber data for segmentation and list management
- **task_board**: Read/update task statuses, create new tasks
- **agent_messaging**: Send messages to other agents via @mention

## Tool Policies

- DO use email platform API to manage campaigns, sequences, and segments
- DO query subscriber data for segmentation (aggregated, not individual PII)
- DO write campaign documentation, sequence flowcharts, and performance reports
- DO monitor deliverability dashboards and sender reputation scores
- Do NOT send emails without proper compliance review (unsubscribe link, legal footer, consent verification)
- Do NOT add subscribers to lists without verified opt-in
- Do NOT override unsubscribe requests or suppress lists
- Do NOT send test emails to real subscriber segments
- ALWAYS verify audience segment and content before scheduling any send
