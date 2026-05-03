"""
Planner — recommend a team based on a textual goal description.
"""

from hermes_agency.teams import load_team


# Keyword → team mapping for v0.1 heuristic
_KEYWORD_TEAMS: list[tuple[list[str], str]] = [
    # SaaS / web app keywords
    (
        [
            "saas", "subscription", "dashboard", "auth", "billing",
            "payment", "web app", "platform", "marketplace", "portal",
            "api", "crm", "erp", "multi-tenant", "tenant",
        ],
        "saas-medium",
    ),
    # iOS / iPhone app
    (
        ["ios", "iphone", "apple", "swift", "mobile app", "native app", "app store"],
        "iphone-app",
    ),
    # AI / ML app
    (
        ["ai", "machine learning", "ml", "llm", "rag", "chatbot", "gpt",
         "neural", "artificial intelligence", "deep learning", "nlp"],
        "ai-app",
    ),
    # Security audit
    (
        ["security audit", "penetration test", "vulnerability", "compliance",
         "security review", "threat model", "risk assessment"],
        "security-audit",
    ),
    # Research / writing
    (
        ["research", "whitepaper", "literature review", "study", "report",
         "technical writing", "academic", "publication"],
        "research-writing",
    ),
    # Content / marketing
    (
        ["content", "blog", "marketing", "social media", "copywriting",
         "seo", "brand", "content strategy"],
        "content-creator",
    ),
    # DevOps / deployment
    (
        ["devops", "ci/cd", "deployment", "infrastructure", "terraform",
         "kubernetes", "docker compose", "pipeline", "production ops"],
        "devops-deployment",
    ),
]


def recommend_team(goal: str) -> tuple[str, dict]:
    """
    Analyze a goal string and recommend a team.

    Uses keyword matching with start-of-word boundaries.
    Prevents false positives for short keywords ("ai" matching
    "maintenance") while allowing compound matches ("web app"
    matching "web application").
    Returns (team_id, team_definition_dict).
    """
    import re

    goal_lower = goal.lower()

    # Check keyword matches in priority order
    for keywords, team_id in _KEYWORD_TEAMS:
        for kw in keywords:
            # Start-of-word boundary prevents false positives for short
            # keywords like "ai" (no match in "maintenance" or "email")
            # without breaking compound matches like "web app" in
            # "web application". Use re.escape for hyphenated terms.
            pattern = r'\b' + re.escape(kw)
            if re.search(pattern, goal_lower):
                team_def = load_team(team_id)
                if team_def:
                    return team_id, team_def

    # Default: general-dev
    team_id = "general-dev"
    team_def = load_team(team_id)
    return team_id, team_def or {"name": "General Development Team", "description": "", "agents": []}


def plan_to_dag(goal: str, team_id: str, team_def: dict) -> list[dict]:
    """Generate a task DAG from a team definition.

    Returns ordered list of steps with assignee, title, description, parents.
    The orchestator is always the first step (planning) and last step
    (delivery verification). Intermediate steps are ordered by role convention.
    """
    from hermes_agency.teams import load_role

    agents = team_def.get("agents", [])
    dag = []
    step_counter = 0

    # Step 1: Orchestrator assigns work
    if "orchestrator" in agents:
        step_counter += 1
        dag.append({
            "step": f"step_{step_counter}",
            "assignee": "orchestrator",
            "title": f"Plan and assign work for: {goal[:80]}",
            "description": "Analyze goal, decompose into tasks, assign to agents via Kanban.",
            "parents": [],
        })

    # Intermediate steps: non-orchestrator agents in conventional order
    role_order = _get_role_order()
    for role_id in role_order:
        if role_id == "orchestrator":
            continue
        if role_id not in agents:
            continue
        step_counter += 1
        role_data = load_role(role_id) or {}
        name = role_data.get("name", role_id)
        mission = role_data.get("mission", "")
        dag.append({
            "step": f"step_{step_counter}",
            "assignee": role_id,
            "title": f"{name}: {mission[:120] if mission else 'Execute assigned work'}",
            "description": (
                f"Role: {name}. "
                f"{'Mission: ' + mission[:200] if mission else ''}"
            ),
            "parents": [f"step_{step_counter - 1}"],
        })

    # Final step: Orchestrator verifies delivery
    if "orchestrator" in agents:
        step_counter += 1
        dag.append({
            "step": f"step_{step_counter}",
            "assignee": "orchestrator",
            "title": "Verify delivery and report to user",
            "description": "Aggregate all agent outputs, verify against goal, present summary to user.",
            "parents": [f"step_{step_counter - 1}"],
        })

    return dag


def _get_role_order() -> list[str]:
    """Conventional role execution order within a team pipeline."""
    return [
        "product-manager",
        "ux-designer",
        "fullstack-developer",
        "frontend-developer",
        "backend-developer",
        "database-architect",
        "qa-tester",
        "security-reviewer",
        "deployer",
        "reviewer",
        "technical-writer",
    ]
