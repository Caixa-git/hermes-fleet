"""
Planner — recommend a team based on a textual goal description.
"""

from typing import Dict, Tuple

from hermes_fleet.teams import load_team


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
]


def recommend_team(goal: str) -> Tuple[str, dict]:
    """
    Analyze a goal string and recommend a team.

    Uses simple keyword matching for v0.1.
    Returns (team_id, team_definition_dict).
    """
    goal_lower = goal.lower()

    # Check keyword matches in priority order
    for keywords, team_id in _KEYWORD_TEAMS:
        for kw in keywords:
            if kw in goal_lower:
                team_def = load_team(team_id)
                if team_def:
                    return team_id, team_def

    # Default: general-dev
    team_id = "general-dev"
    team_def = load_team(team_id)
    return team_id, team_def or {"name": "General Development Team", "description": "", "agents": []}
