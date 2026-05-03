"""
Team definitions — load team and role data from YAML presets.
"""

from pathlib import Path
from typing import Dict, Optional

import yaml


def _get_presets_dir() -> Path:
    """Return the presets directory."""
    return Path(__file__).resolve().parent.parent.parent / "presets"


def load_team(team_id: str) -> Optional[dict]:
    """Load a team definition from presets/teams/<team_id>.yaml."""
    team_path = _get_presets_dir() / "teams" / f"{team_id}.yaml"
    if not team_path.exists():
        return None
    with open(team_path) as f:
        return yaml.safe_load(f)


def load_role(role_id: str) -> Optional[dict]:
    """Load a role definition from presets/roles/<role_id>.yaml."""
    role_path = _get_presets_dir() / "roles" / f"{role_id}.yaml"
    if not role_path.exists():
        return None
    with open(role_path) as f:
        return yaml.safe_load(f)


def list_available_teams() -> list[str]:
    """List all available team preset IDs."""
    teams_dir = _get_presets_dir() / "teams"
    if not teams_dir.exists():
        return []
    return sorted(
        f.stem for f in teams_dir.glob("*.yaml") if f.stem != "__init__"
    )


def list_available_roles() -> list[str]:
    """List all available role preset IDs."""
    roles_dir = _get_presets_dir() / "roles"
    if not roles_dir.exists():
        return []
    return sorted(
        f.stem for f in roles_dir.glob("*.yaml") if f.stem != "__init__"
    )
