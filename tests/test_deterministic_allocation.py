"""Tests: Deterministic allocation — same input → same output.

These tests verify that the planner produces identical results
when given the same inputs.
"""

from hermes_agency.planner import recommend_team


class TestDeterministicAllocation:
    """Same goal + same presets → same team proposal every time."""

    def test_same_goal_same_team(self):
        """Calling recommend_team twice with the same goal returns the same team."""
        id1, def1 = recommend_team("Build an AI chatbot")
        id2, def2 = recommend_team("Build an AI chatbot")
        assert id1 == id2
        assert def1["agents"] == def2["agents"]

    def test_same_goal_multiple_times(self):
        """Three calls with the same goal produce identical results."""
        results = [recommend_team("Set up Kubernetes deployment") for _ in range(3)]
        ids = [r[0] for r in results]
        agents = [tuple(r[1]["agents"]) for r in results]
        assert len(set(ids)) == 1
        assert len(set(agents)) == 1

    def test_empty_goal_consistently_defaults(self):
        """Empty goal always returns general-dev."""
        for _ in range(5):
            team_id, team_def = recommend_team("")
            assert team_id == "general-dev"
            assert len(team_def["agents"]) >= 3

    def test_different_goals_different_teams(self):
        """Different goals should map to different teams when keywords differ."""
        id_saas, _ = recommend_team("Build a SaaS platform with billing")
        id_ios, _ = recommend_team("Build an iOS app with Swift")
        assert id_saas != id_ios

    def test_all_8_teams_deterministic(self):
        """All 8 team presets produce identical results on repeated calls."""
        goals = [
            "Build a SaaS platform",
            "Build an iPhone app with Swift",
            "Build an AI chatbot with RAG",
            "Security audit penetration test",
            "Research whitepaper literature",
            "Content blog marketing strategy",
            "CI/CD deployment Kubernetes",
            "General web development",
        ]
        for goal in goals:
            id1, def1 = recommend_team(goal)
            id2, def2 = recommend_team(goal)
            assert id1 == id2
            assert def1["agents"] == def2["agents"]
