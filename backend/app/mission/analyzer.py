"""Mission Analyzer — turns a customer's goal into an agent spawn plan and task graph.

Uses LLM (Claude API) when available, falls back to rule-based analysis.
"""

import json
import logging
import random
from typing import Any

from app.config import settings
from app.workspace.registry import registry

logger = logging.getLogger(__name__)

# Keyword mappings for rule-based analysis
SOFTWARE_KEYWORDS = [
    "app", "application", "website", "web", "platform", "tool", "software",
    "build", "develop", "create", "saas", "api", "system", "dashboard",
    "mobile", "ios", "android", "react", "vue", "angular", "django",
    "flask", "fastapi", "node", "express", "database", "frontend", "backend",
]
MOBILE_KEYWORDS = ["mobile", "ios", "android", "react native", "flutter", "phone"]
BUSINESS_KEYWORDS = [
    "grow", "growth", "marketing", "seo", "content", "blog", "email",
    "retention", "churn", "customers", "users", "revenue", "sales",
    "social media", "newsletter", "campaign",
]
DATA_KEYWORDS = [
    "data", "analytics", "dashboard", "pipeline", "etl", "ml", "machine learning",
    "ai", "model", "training", "analysis", "kpi", "metrics",
]
DESIGN_KEYWORDS = ["design", "ui", "ux", "mockup", "wireframe", "figma", "visual"]


def _has_keywords(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _pick_name(role: str) -> str:
    names = registry.get_role_names(role)
    return random.choice(names) if names else role.title()


def analyze_mission_rules(goal: str, specification: str = "") -> dict[str, Any]:
    """Rule-based mission analysis (fallback when no LLM available).

    Returns:
        {
            "agents": [{role, name, model, authority_level}],
            "tasks": [{title, description, assignee_role, dependencies, priority}],
            "estimated_cost": {min, max, model_breakdown},
            "clarification_needed": bool,
            "questions": [str],
        }
    """
    combined = f"{goal} {specification}".lower()
    agents = []
    tasks = []

    # Always spawn orchestrator
    agents.append({
        "role": "orchestrator",
        "name": _pick_name("orchestrator"),
        "model": registry.get_model("orchestrator"),
        "authority_level": registry.get_authority_level("orchestrator"),
    })

    is_software = _has_keywords(combined, SOFTWARE_KEYWORDS)
    is_mobile = _has_keywords(combined, MOBILE_KEYWORDS)
    is_business = _has_keywords(combined, BUSINESS_KEYWORDS)
    is_data = _has_keywords(combined, DATA_KEYWORDS)
    is_design = _has_keywords(combined, DESIGN_KEYWORDS)

    # Software development agents and tasks
    if is_software:
        agents.append({
            "role": "architect",
            "name": _pick_name("architect"),
            "model": registry.get_model("architect"),
            "authority_level": registry.get_authority_level("architect"),
        })
        agents.append({
            "role": "backend-dev",
            "name": _pick_name("backend-dev"),
            "model": registry.get_model("backend-dev"),
            "authority_level": registry.get_authority_level("backend-dev"),
        })
        agents.append({
            "role": "frontend-dev",
            "name": _pick_name("frontend-dev"),
            "model": registry.get_model("frontend-dev"),
            "authority_level": registry.get_authority_level("frontend-dev"),
        })
        agents.append({
            "role": "qa",
            "name": _pick_name("qa"),
            "model": registry.get_model("qa"),
            "authority_level": registry.get_authority_level("qa"),
        })
        agents.append({
            "role": "devops",
            "name": _pick_name("devops"),
            "model": registry.get_model("devops"),
            "authority_level": registry.get_authority_level("devops"),
        })

        tasks.extend([
            {
                "title": "Design System Architecture",
                "description": "Design the overall system architecture, tech stack, API contracts, and database schema",
                "assignee_role": "architect",
                "dependencies": [],
                "priority": 100,
                "requires_approval": False,
            },
            {
                "title": "Build Backend APIs",
                "description": "Implement the REST API endpoints, database models, and server logic",
                "assignee_role": "backend-dev",
                "dependencies": ["Design System Architecture"],
                "priority": 90,
                "requires_approval": False,
            },
            {
                "title": "Build Frontend UI",
                "description": "Implement the user interface components, pages, and routing",
                "assignee_role": "frontend-dev",
                "dependencies": ["Design System Architecture"],
                "priority": 90,
                "requires_approval": False,
            },
            {
                "title": "Integrate Frontend and Backend",
                "description": "Connect the frontend to the backend APIs, handle auth flow",
                "assignee_role": "frontend-dev",
                "dependencies": ["Build Backend APIs", "Build Frontend UI"],
                "priority": 80,
                "requires_approval": False,
            },
            {
                "title": "QA Testing",
                "description": "Run automated tests, manual testing, code review, bug reporting",
                "assignee_role": "qa",
                "dependencies": ["Integrate Frontend and Backend"],
                "priority": 70,
                "requires_approval": False,
            },
            {
                "title": "Deploy to Staging",
                "description": "Dockerize the application, set up CI/CD, deploy to staging environment",
                "assignee_role": "devops",
                "dependencies": ["QA Testing"],
                "priority": 60,
                "requires_approval": True,
            },
            {
                "title": "Deploy to Production",
                "description": "Deploy to production after staging verification",
                "assignee_role": "devops",
                "dependencies": ["Deploy to Staging"],
                "priority": 50,
                "requires_approval": True,
            },
        ])

    if is_mobile and not any(a["role"] == "mobile-dev" for a in agents):
        agents.append({
            "role": "mobile-dev",
            "name": _pick_name("mobile-dev"),
            "model": registry.get_model("mobile-dev"),
            "authority_level": registry.get_authority_level("mobile-dev"),
        })
        tasks.append({
            "title": "Build Mobile App",
            "description": "Implement the mobile application",
            "assignee_role": "mobile-dev",
            "dependencies": ["Design System Architecture"] if is_software else [],
            "priority": 85,
            "requires_approval": False,
        })

    # Business growth agents and tasks
    if is_business:
        if _has_keywords(combined, ["seo", "search", "ranking", "keyword"]):
            agents.append({
                "role": "seo",
                "name": _pick_name("seo"),
                "model": registry.get_model("seo"),
                "authority_level": registry.get_authority_level("seo"),
            })
            tasks.append({
                "title": "SEO Audit and Strategy",
                "description": "Perform SEO audit, keyword research, and create optimization plan",
                "assignee_role": "seo",
                "dependencies": [],
                "priority": 80,
                "requires_approval": False,
            })

        if _has_keywords(combined, ["content", "blog", "article", "social"]):
            agents.append({
                "role": "content-writer",
                "name": _pick_name("content-writer"),
                "model": registry.get_model("content-writer"),
                "authority_level": registry.get_authority_level("content-writer"),
            })
            tasks.append({
                "title": "Content Strategy and Creation",
                "description": "Develop content strategy and create initial content pieces",
                "assignee_role": "content-writer",
                "dependencies": [],
                "priority": 70,
                "requires_approval": False,
            })

        if _has_keywords(combined, ["retention", "churn", "re-engage"]):
            agents.append({
                "role": "retention",
                "name": _pick_name("retention"),
                "model": registry.get_model("retention"),
                "authority_level": registry.get_authority_level("retention"),
            })

        if _has_keywords(combined, ["email", "newsletter", "drip", "campaign"]):
            agents.append({
                "role": "email-marketing",
                "name": _pick_name("email-marketing"),
                "model": registry.get_model("email-marketing"),
                "authority_level": registry.get_authority_level("email-marketing"),
            })

        # Always add researcher for business missions
        agents.append({
            "role": "researcher",
            "name": _pick_name("researcher"),
            "model": registry.get_model("researcher"),
            "authority_level": registry.get_authority_level("researcher"),
        })
        tasks.insert(0, {
            "title": "Market Research and Analysis",
            "description": "Research competitors, market trends, and customer insights",
            "assignee_role": "researcher",
            "dependencies": [],
            "priority": 95,
            "requires_approval": False,
        })

    if is_data:
        if _has_keywords(combined, ["pipeline", "etl", "data engineer"]):
            agents.append({
                "role": "data-engineer",
                "name": _pick_name("data-engineer"),
                "model": registry.get_model("data-engineer"),
                "authority_level": registry.get_authority_level("data-engineer"),
            })

        if _has_keywords(combined, ["ml", "machine learning", "model", "training", "ai"]):
            agents.append({
                "role": "ml-engineer",
                "name": _pick_name("ml-engineer"),
                "model": registry.get_model("ml-engineer"),
                "authority_level": registry.get_authority_level("ml-engineer"),
            })

        if _has_keywords(combined, ["analytics", "dashboard", "kpi", "metrics"]):
            agents.append({
                "role": "analytics",
                "name": _pick_name("analytics"),
                "model": registry.get_model("analytics"),
                "authority_level": registry.get_authority_level("analytics"),
            })

    if is_design:
        agents.append({
            "role": "designer",
            "name": _pick_name("designer"),
            "model": registry.get_model("designer"),
            "authority_level": registry.get_authority_level("designer"),
        })
        # Add design task before frontend
        design_task = {
            "title": "UI/UX Design",
            "description": "Create UI mockups, design system, and visual identity",
            "assignee_role": "designer",
            "dependencies": ["Design System Architecture"] if is_software else [],
            "priority": 92,
            "requires_approval": False,
        }
        tasks.insert(1 if tasks else 0, design_task)
        # Make frontend depend on design
        for task in tasks:
            if task["title"] == "Build Frontend UI":
                if "UI/UX Design" not in task["dependencies"]:
                    task["dependencies"].append("UI/UX Design")

    # Cost estimation
    num_agents = len(agents)
    est_heartbeats = 20 * num_agents  # ~20 heartbeats per agent
    cost_per_heartbeat = 0.05  # rough estimate
    min_cost = est_heartbeats * cost_per_heartbeat * 0.7
    max_cost = est_heartbeats * cost_per_heartbeat * 1.5

    # Determine if clarification is needed
    questions = []
    if not is_software and not is_business and not is_data:
        questions.append("Could you describe your goal in more detail? What specific outcome are you looking for?")
    if is_software and not specification:
        questions.append("What platform should this be built for? (web, mobile, both)")
        questions.append("Do you have any tech stack preferences?")
        questions.append("Who are the target users?")

    return {
        "agents": agents,
        "tasks": tasks,
        "estimated_cost": {
            "min": round(min_cost, 2),
            "max": round(max_cost, 2),
            "num_agents": num_agents,
            "estimated_heartbeats": est_heartbeats,
        },
        "clarification_needed": len(questions) > 0,
        "questions": questions,
    }


async def analyze_mission_llm(goal: str, specification: str = "") -> dict[str, Any]:
    """LLM-powered mission analysis using Claude API.

    Falls back to rule-based if no API key configured.
    """
    if not settings.anthropic_api_key:
        logger.info("No Anthropic API key, using rule-based analyzer")
        return analyze_mission_rules(goal, specification)

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        roles_summary = json.dumps(registry.to_summary(), indent=2)

        prompt = f"""You are a Mission Analyzer for an AI Agent Squad Platform.
Given a customer's goal, you need to:

1. Determine which AI agents to spawn (from the available roles)
2. Create a task breakdown with dependencies
3. Estimate costs

Available agent roles:
{roles_summary}

Customer's Goal: {goal}
Additional Specification: {specification or "None provided"}

Respond in this exact JSON format:
{{
    "agents": [
        {{"role": "role_key", "name": "agent_name"}},
        ...
    ],
    "tasks": [
        {{
            "title": "Task Title",
            "description": "What needs to be done",
            "assignee_role": "role_key",
            "dependencies": ["Title of dependency task"],
            "priority": 100,
            "requires_approval": false
        }},
        ...
    ],
    "clarification_needed": false,
    "questions": []
}}

Rules:
- Always include an orchestrator
- Order tasks by dependency (no circular deps)
- Mark deploy tasks as requires_approval: true
- Dependencies reference task titles
- Priority: 100 = highest, 0 = lowest
- If the goal is vague, set clarification_needed to true and provide questions
"""

        message = await client.messages.create(
            model=settings.default_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

        # Parse the JSON from the response
        # Handle case where response includes markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text)

        # Enrich agents with registry data
        for agent in result.get("agents", []):
            role = agent["role"]
            agent["model"] = registry.get_model(role)
            agent["authority_level"] = registry.get_authority_level(role)

        # Add cost estimate
        num_agents = len(result.get("agents", []))
        est_heartbeats = 20 * num_agents
        cost_per_heartbeat = 0.05
        result["estimated_cost"] = {
            "min": round(est_heartbeats * cost_per_heartbeat * 0.7, 2),
            "max": round(est_heartbeats * cost_per_heartbeat * 1.5, 2),
            "num_agents": num_agents,
            "estimated_heartbeats": est_heartbeats,
        }

        return result

    except Exception as e:
        logger.error(f"LLM analysis failed: {e}, falling back to rules")
        return analyze_mission_rules(goal, specification)
