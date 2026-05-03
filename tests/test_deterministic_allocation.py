"""Tests: Deterministic allocation — same input → same output.

These tests verify that the planner and generator produce identical
results when given the same inputs, regardless of external state.
No mock overrides needed due to deterministic YAML loading order.
"""

from hermes_fleet.planner import recommend_team


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
