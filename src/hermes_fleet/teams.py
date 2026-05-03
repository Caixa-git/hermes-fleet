"""
Team definitions — load team and role data from YAML presets.
"""

from pathlib import Path
from typing import Optional

import yaml

from hermes_fleet.contracts import (
    handoff_from_dict,
    role_from_dict,
    team_from_dict,
)


def _get_presets_dir() -> Path:
    """Return the presets directory."""
    return Path(__file__).resolve().parent.parent.parent / "presets"


def _get_custom_dir(subdir: str, project_dir: Path | None = None) -> Path | None:
    """Return a custom overrides directory (.fleet/<subdir>/), if it exists."""
    base = project_dir or Path.cwd()
    custom_dir = base / ".fleet" / subdir
    return custom_dir if custom_dir.exists() else None


def load_team(team_id: str) -> Optional[dict]:
    """Load a team definition from presets/teams/<team_id>.yaml."""
    team_path = _get_presets_dir() / "teams" / f"{team_id}.yaml"
    if not team_path.exists():
        return None
    with open(team_path) as f:
        data = yaml.safe_load(f)
    # Validate against TeamContract schema
    team_from_dict(data)
    return data


def load_role(role_id: str, project_dir: Path | None = None) -> Optional[dict]:
    """Load a role definition, checking .fleet/roles/ first, then presets/roles/.

    Custom roles in .fleet/roles/ take precedence over built-in presets.
    Validates against RoleContract schema on successful load.
    """
    # Check custom roles first
    custom_dir = _get_custom_dir("roles", project_dir)
    if custom_dir:
        role_path = custom_dir / f"{role_id}.yaml"
        if role_path.exists():
            with open(role_path) as f:
                data = yaml.safe_load(f)
            role_from_dict(data)
            return data
    # Fall back to built-in presets
    role_path = _get_presets_dir() / "roles" / f"{role_id}.yaml"
    if not role_path.exists():
        return None
    with open(role_path) as f:
        data = yaml.safe_load(f)
    role_from_dict(data)
    return data


def load_role_raw(role_id: str, project_dir: Path | None = None) -> Optional[dict]:
    """Load a role dict without schema validation (for customize/display)."""
    custom_dir = _get_custom_dir("roles", project_dir)
    if custom_dir:
        role_path = custom_dir / f"{role_id}.yaml"
        if role_path.exists():
            with open(role_path) as f:
                return yaml.safe_load(f)
    role_path = _get_presets_dir() / "roles" / f"{role_id}.yaml"
    if not role_path.exists():
        return None
    with open(role_path) as f:
        return yaml.safe_load(f)


def list_available_roles(project_dir: Path | None = None) -> list[str]:
    """List all available role preset IDs (built-in + custom)."""
    roles: set[str] = set()
    # Built-in presets
    roles_dir = _get_presets_dir() / "roles"
    if roles_dir.exists():
        roles.update(f.stem for f in roles_dir.glob("*.yaml") if f.stem != "__init__")
    # Custom overrides
    custom_dir = _get_custom_dir("roles", project_dir)
    if custom_dir:
        roles.update(f.stem for f in custom_dir.glob("*.yaml") if f.stem != "__init__")
    return sorted(roles)


def list_available_teams() -> list[str]:
    """List all available team preset IDs."""
    teams_dir = _get_presets_dir() / "teams"
    if not teams_dir.exists():
        return []
    return sorted(
        f.stem for f in teams_dir.glob("*.yaml") if f.stem != "__init__"
    )


def load_handoff(handoff_id: str) -> Optional[dict]:
    """Load a handoff contract from presets/handoffs/<handoff_id>.yaml."""
    handoff_path = _get_presets_dir() / "handoffs" / f"{handoff_id}.yaml"
    if not handoff_path.exists():
        return None
    with open(handoff_path) as f:
        data = yaml.safe_load(f)
    handoff_from_dict(data)
    return data


def list_available_handoffs() -> list[str]:
    """List all available handoff contract preset IDs."""
    handoffs_dir = _get_presets_dir() / "handoffs"
    if not handoffs_dir.exists():
        return []
    return sorted(
        f.stem for f in handoffs_dir.glob("*.yaml") if f.stem != "__init__"
    )


def list_available_permission_presets(project_dir: Path | None = None) -> list[str]:
    """List all available permission presets (built-in + custom)."""
    presets: set[str] = set()
    presets_dir = _get_presets_dir() / "permissions"
    if presets_dir.exists():
        presets.update(f.stem for f in presets_dir.glob("*.yaml") if f.stem != "__init__")
    custom_dir = _get_custom_dir("permissions", project_dir)
    if custom_dir:
        presets.update(f.stem for f in custom_dir.glob("*.yaml") if f.stem != "__init__")
    return sorted(presets)
