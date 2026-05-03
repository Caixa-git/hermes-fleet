"""
Tests: Planner recommendations.
"""

import pytest

from hermes_fleet.planner import recommend_team

# (goal, expected_team_id)
KEYWORD_TEAMS = [
    ("Build a medium-sized SaaS MVP", "saas-medium"),
    ("Build a subscription-based platform", "saas-medium"),
    ("Create a customer dashboard with billing", "saas-medium"),
    ("Build a public API with authentication", "saas-medium"),
    ("Create an online marketplace", "saas-medium"),
    ("Build an iOS app with Swift", "iphone-app"),
    ("Create a native mobile app with push notifications", "iphone-app"),
    ("Build an AI chatbot with RAG", "ai-app"),
    ("Train and deploy an ML model", "ai-app"),
    ("Conduct a security audit and penetration test", "security-audit"),
    ("Run a compliance risk assessment", "security-audit"),
    ("Write a research report on compiler design", "research-writing"),
    ("Create a technical whitepaper", "research-writing"),
    ("Develop a content marketing strategy", "content-creator"),
    ("Write SEO-optimized blog posts", "content-creator"),
    ("Set up CI/CD pipeline and infrastructure", "devops-deployment"),
    ("Deploy to Kubernetes cluster", "devops-deployment"),
    ("Build a simple CLI tool", "general-dev"),
    ("", "general-dev"),
]


class TestPlanner:
    """Tests for the goal-to-team planner."""

    @pytest.mark.parametrize("goal,expected_team", KEYWORD_TEAMS)
    def test_goal_maps_to_expected_team(self, goal, expected_team):
        team_id, team_def = recommend_team(goal)
        assert team_id == expected_team
        assert team_def is not None

    def test_team_def_has_agents(self):
        _, team_def = recommend_team("Refactor this Python project")
        assert "agents" in team_def
        assert len(team_def["agents"]) >= 1
