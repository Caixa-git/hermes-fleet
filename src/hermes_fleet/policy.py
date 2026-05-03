"""
Policy — resolve permission presets and compose policy.yaml content.
"""

from pathlib import Path
from typing import Dict

import yaml

from hermes_fleet.teams import load_role


def _get_permissions_dir() -> Path:
    """Return the presets/permissions directory."""
    return Path(__file__).resolve().parent.parent.parent / "presets" / "permissions"


def _load_permission_presets() -> Dict[str, dict]:
    """Load all permission presets from presets/permissions/*.yaml."""
    from hermes_fleet.contracts import ContractValidationError, permission_preset_from_dict

    presets_dir = _get_permissions_dir()
    presets: Dict[str, dict] = {}
    if not presets_dir.exists():
        return presets
    for f in sorted(presets_dir.glob("*.yaml")):
        preset_id = f.stem
        with open(f) as fh:
            data = yaml.safe_load(fh) or {}
        # Validate against contract schema
        try:
            permission_preset_from_dict(data)
        except ContractValidationError as e:
            raise RuntimeError(
                f"Permission preset '{preset_id}' is invalid: {e}"
            ) from e
        presets[preset_id] = data
    return presets


def get_permission_preset(preset_id: str) -> dict:
    """Get a permission preset by ID from YAML files."""
    presets = _load_permission_presets()
    preset = presets.get(preset_id)
    if not preset:
        return {}
    return dict(preset)


def compose_policy(role_id: str) -> dict:
    """
    Compose a complete policy.yaml dict for a given role.

    Merges the role definition from presets/roles with the appropriate
    permission preset.
    """
    role_data = load_role(role_id) or {}
    preset_id = role_data.get("permission_preset", "repo_readonly")
    preset = get_permission_preset(preset_id)

    # Build the policy dict
    policy = {
        "agent_id": role_id,
        "role": role_data.get("name", role_id),
        "task_policy": {
            "allowed_task_types": role_data.get("allowed_tasks", preset.get("allowed_tasks", [])),
            "forbidden_task_types": role_data.get(
                "forbidden_tasks",
                ["implementation", "deployment", "product_scope_decision"],
            ),
        },
        "filesystem": {
            "writable_paths": role_data.get("filesystem", {}).get(
                "writable_paths", preset.get("filesystem", {}).get("writable_paths", [])
            ),
            "readonly_paths": role_data.get("filesystem", {}).get(
                "readonly_paths", preset.get("filesystem", {}).get("readonly_paths", ["**"])
            ),
            "forbidden_paths": role_data.get("filesystem", {}).get(
                "forbidden_paths", preset.get("filesystem", {}).get("forbidden_paths", [])
            ),
        },
        "network": {
            "mode": role_data.get("network_access", preset.get("network_access", "none")),
        },
        "secrets": {
            "allow": role_data.get("secret_allowlist", preset.get("secret_allowlist", [])),
        },
        "commands": {
            "allow": role_data.get("allowed_commands", preset.get("allowed_commands", [])),
            "deny": role_data.get("denied_commands", preset.get("denied_commands", [])),
        },
        "handoff": role_data.get("handoff", {
            "required_outputs": ["summary", "files_changed", "next_agent"],
        }),
        "completion_gate": role_data.get("completion_gates", {
            "required": ["task_complete", "handoff_note"],
        }),
    }

    return policy


def list_presets() -> list[str]:
    """List all available permission preset IDs from YAML files."""
    return sorted(
        f.stem for f in _get_permissions_dir().glob("*.yaml")
        if f.stem != "__init__"
    )
