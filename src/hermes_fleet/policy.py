"""
Policy — resolve permission presets and compose policy.yaml content.
"""

from typing import Dict, List

from hermes_fleet.teams import load_role

# Permission presets as Python data structures
_PERMISSION_PRESETS: Dict[str, dict] = {
    "orchestrator_safe": {
        "allowed_workspaces": "kanban_only",
        "filesystem": {
            "writable_paths": [".fleet/**", "kanban/**"],
            "readonly_paths": ["**"],
            "forbidden_paths": ["src/**", "app/**", "**/application/**"],
        },
        "network_access": "control_plane_only",
        "secret_allowlist": [],
    },
    "repo_readonly": {
        "allowed_workspaces": "readonly",
        "filesystem": {
            "writable_paths": [],
            "readonly_paths": ["**"],
            "forbidden_paths": [".env", "secrets/**", "other-agents/**"],
        },
        "network_access": "none",
        "secret_allowlist": [],
    },
    "docs_rw_repo_ro": {
        "allowed_workspaces": "docs_write",
        "filesystem": {
            "writable_paths": ["docs/**", "design/**", "README.md"],
            "readonly_paths": ["**"],
            "forbidden_paths": [".env", "src/**", "other-agents/**"],
        },
        "network_access": "none",
        "secret_allowlist": [],
    },
    "frontend_worktree_rw": {
        "allowed_workspaces": "own_worktree_rw",
        "filesystem": {
            "writable_paths": ["frontend/**", "ui/**", "public/**"],
            "readonly_paths": ["**"],
            "forbidden_paths": ["backend/**", "infra/**", ".env*"],
        },
        "network_access": "package_registry",
        "secret_allowlist": ["PUBLIC_SUPABASE_URL", "PUBLIC_STRIPE_KEY"],
    },
    "backend_worktree_rw": {
        "allowed_workspaces": "own_worktree_rw",
        "filesystem": {
            "writable_paths": ["backend/**", "api/**", "src/**"],
            "readonly_paths": ["**"],
            "forbidden_paths": ["frontend/**", "infra/**", ".env.production"],
        },
        "network_access": "package_registry",
        "secret_allowlist": ["DATABASE_URL_DEV", "OPENAI_API_KEY_DEV"],
    },
    "readonly_no_network": {
        "allowed_workspaces": "readonly",
        "filesystem": {
            "writable_paths": [],
            "readonly_paths": ["**"],
            "forbidden_paths": [".env", "secrets/**", "other-agents/**"],
        },
        "network_access": "none",
        "secret_allowlist": [],
    },
    "test_runner": {
        "allowed_workspaces": "readonly_or_test_tmp",
        "filesystem": {
            "writable_paths": ["tmp/**", "test-results/**"],
            "readonly_paths": ["**"],
            "forbidden_paths": [".env", "secrets/**"],
        },
        "network_access": "none",
        "secret_allowlist": [],
    },
    "schema_worktree_rw": {
        "allowed_workspaces": "own_worktree_rw",
        "filesystem": {
            "writable_paths": ["db/**", "migrations/**", "schema/**"],
            "readonly_paths": ["**"],
            "forbidden_paths": [".env.production", "infra/**", "frontend/**"],
        },
        "network_access": "package_registry",
        "secret_allowlist": ["DATABASE_URL_DEV"],
    },
}


def get_permission_preset(preset_id: str) -> dict:
    """Get a permission preset by ID."""
    preset = _PERMISSION_PRESETS.get(preset_id)
    if not preset:
        return {}
    return preset.copy()


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
    """List all available permission preset IDs."""
    return sorted(_PERMISSION_PRESETS.keys())
