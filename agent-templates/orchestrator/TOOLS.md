# TOOLS — Orchestrator

## Available Tools

- **file**: Read and write files in the mission workspace
- **shell**: Run shell commands for checking project status
- **git**: View git log, diffs, check repository status
- **task_board**: Read/update task statuses, create new tasks
- **agent_messaging**: Send messages to other agents via @mention

## Tool Policies

- Do NOT run build/test commands — that's the dev agents' job
- Do NOT modify source code — that's the dev agents' job
- DO read files to understand project state
- DO check git log to verify progress
- DO update task statuses based on what you observe
- DO send clear messages with context when communicating with agents
