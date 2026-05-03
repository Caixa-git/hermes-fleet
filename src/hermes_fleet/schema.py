"""
Pydantic schemas for Hermes Fleet data models.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NetworkAccess(str, Enum):
    """Network access policy levels."""
    NONE = "none"
    WEB_READONLY = "web_readonly"
    PACKAGE_REGISTRY = "package_registry"
    INTERNAL = "internal"
    DEPLOY_ONLY = "deploy_only"
    CONTROL_PLANE = "control_plane_only"


class WorkspaceAccess(str, Enum):
    """Workspace access levels."""
    READONLY = "readonly"
    OWN_WORKTREE_RW = "own_worktree_rw"
    DOCS_WRITE = "docs_write"
    KANBAN_ONLY = "kanban_only"
    READONLY_OR_TEST_TMP = "readonly_or_test_tmp"
    NONE = "none"
    FULL = "full"


class TaskType(str, Enum):
    """Types of tasks agents can perform."""
    SECURITY_REVIEW = "security_review"
    RISK_ANALYSIS = "risk_analysis"
    DEPENDENCY_REVIEW = "dependency_review"
    IMPLEMENTATION = "implementation"
    DEPLOYMENT = "deployment"
    PRODUCT_SCOPE = "product_scope_decision"
    CODE_REVIEW = "code_review"
    QA_TESTING = "qa_testing"
    DOCUMENTATION = "documentation"
    DESIGN = "design"
    DATABASE_SCHEMA = "database_schema"
    ORCHESTRATION = "orchestration"
    RESEARCH = "research"
    FRONTEND = "frontend"
    BACKEND = "backend"


class CompletionGate(BaseModel):
    """Conditions that must be met before marking a task complete."""
    required: List[str] = Field(default_factory=list)


class HandoffContract(BaseModel):
    """Expected outputs when handing off work to another agent."""
    required_outputs: List[str] = Field(default_factory=list)


class CommandPolicy(BaseModel):
    """Allowed and denied shell commands."""
    allow: List[str] = Field(default_factory=list)
    deny: List[str] = Field(default_factory=list)


class FilesystemPolicy(BaseModel):
    """Filesystem access rules."""
    writable_paths: List[str] = Field(default_factory=list)
    readonly_paths: List[str] = Field(default_factory=list)
    forbidden_paths: List[str] = Field(default_factory=list)


class SecretPolicy(BaseModel):
    """Secret allowlist for an agent."""
    allow: List[str] = Field(default_factory=list)


class RoleDefinition(BaseModel):
    """Complete definition of an agent role."""
    id: str
    name: str
    description: str = ""
    mission: str = ""
    non_goals: str = ""
    allowed_tasks: List[str] = Field(default_factory=list)
    forbidden_tasks: List[str] = Field(default_factory=list)
    allowed_workspaces: WorkspaceAccess = WorkspaceAccess.READONLY
    filesystem: FilesystemPolicy = Field(default_factory=FilesystemPolicy)
    network_access: NetworkAccess = NetworkAccess.NONE
    secret_allowlist: List[str] = Field(default_factory=list)
    commands: CommandPolicy = Field(default_factory=CommandPolicy)
    handoff: HandoffContract = Field(default_factory=HandoffContract)
    completion_gates: CompletionGate = Field(default_factory=CompletionGate)


class TeamDefinition(BaseModel):
    """Definition of a team composition."""
    id: str
    name: str
    description: str = ""
    agents: List[str] = Field(default_factory=list)
    optional_agents: Dict[str, bool] = Field(default_factory=dict)


class DockerServiceConfig(BaseModel):
    """Docker Compose service configuration for a single agent."""
    image: str = "nousresearch/hermes-agent:latest"
    container_name: str = ""
    cap_drop: List[str] = Field(default_factory=lambda: ["ALL"])
    cap_add: List[str] = Field(default_factory=lambda: ["DAC_OVERRIDE", "CHOWN", "FOWNER"])
    security_opt: List[str] = Field(default_factory=lambda: ["no-new-privileges:true"])
    pids_limit: int = 256
    read_only: bool = True
    tmpfs: List[str] = Field(default_factory=lambda: [
        "/tmp:rw,noexec,nosuid,size=512m",
        "/run:rw,noexec,nosuid,size=64m",
    ])
    volumes: List[Dict[str, Any]] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)
    networks: List[str] = Field(default_factory=list)
    deploy: Dict[str, Any] = Field(
        default_factory=lambda: {
            "resources": {
                "limits": {
                    "cpus": "0.5",
                    "memory": "512M",
                }
            }
        }
    )


class FleetConfig(BaseModel):
    """Top-level fleet project configuration."""
    fleet_version: str = "0.1.0"
    name: str = "unnamed-fleet"
    team: str = "general-dev"
    output_dir: str = ".fleet/generated"


class SafeDefaultsResult(BaseModel):
    """Result of a single safe-defaults check."""
    check: str
    status: str  # "passed", "failed", "skipped"
    message: str = ""


# ──────────────────────────────────────────────
# v0.2+ Contract Schemas
# These models define the formal contract types
# for deterministic team composition.
# ──────────────────────────────────────────────


class RoleFidelityMode(str, Enum):
    """How closely the SOUL.md must follow the upstream spec."""
    PRESERVE = "preserve"
    """Original spec included verbatim. Default for all roles."""
    NEAR_VERBATIM = "near_verbatim"
    """Minor formatting changes allowed; meaning preserved."""
    SUMMARIZE = "summarize"
    """AI may summarize. Used only when upstream spec is too large."""


class SourceProvenance(BaseModel):
    """Provenance metadata tracing a role back to its upstream spec."""
    repository: str = ""
    """URL of the upstream repository (e.g. agency-agents)."""
    ref: str = ""
    """Commit SHA or release tag."""
    path: str = ""
    """Path to the spec within the repository."""
    hash: str = ""
    """Content hash of the original spec."""


class IdentityDriftGuard(BaseModel):
    """Pre-work and post-work self-check questions."""
    pre_work: List[str] = Field(default_factory=lambda: [
        "Is this task allowed for my role?",
        "Do I have the required context?",
        "Do I have permission for the requested action?",
        "Should this be handed off to another agent?",
    ])
    post_work: List[str] = Field(default_factory=lambda: [
        "Did I stay inside my role?",
        "Did I touch only allowed paths?",
        "Did I produce required outputs?",
        "Did I leave a clear handoff?",
    ])


class ValidationRule(BaseModel):
    """A single validation rule for a handoff field."""
    field: str
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    enum: Optional[List[str]] = None
    """If set, the field value must be one of these."""
    min_items: Optional[int] = None
    """For list fields: minimum number of items."""
    regex: Optional[str] = None


class TeamProposalCustomizations(BaseModel):
    """Optional overrides to a Team Contract's defaults."""
    agents: List[str] = Field(default_factory=list)
    """Subset of the role_inventory. Empty = use all."""
    permission_overrides: Dict[str, str] = Field(default_factory=dict)
    """role_id → alternative preset_id."""
    handoff_overrides: Dict[str, str] = Field(default_factory=dict)
    """contract_id → alternative contract_id."""


class TeamProposal(BaseModel):
    """Constrained schema for AI or human team proposals."""
    goal: str
    recommended_team_id: str
    rationale: str = ""
    customizations: TeamProposalCustomizations = Field(
        default_factory=TeamProposalCustomizations
    )


class HandoffContractSchema(BaseModel):
    """A formal handoff contract between roles."""
    id: str
    from_roles: List[str] = Field(default_factory=list)
    """Which roles may originate this handoff."""
    allowed_next_roles: List[str] = Field(default_factory=list)
    """Which roles may receive this handoff."""
    required_fields: List[str] = Field(default_factory=list)
    """Fields that must be present in the handoff document."""
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    completion_gate: CompletionGate = Field(default_factory=CompletionGate)


class RoleContract(BaseModel):
    """A formal role contract between upstream spec and fleet agent."""
    id: str
    source: SourceProvenance = Field(default_factory=SourceProvenance)
    role_fidelity_mode: RoleFidelityMode = RoleFidelityMode.PRESERVE
    allowed_task_types: List[str] = Field(default_factory=list)
    forbidden_task_types: List[str] = Field(default_factory=list)
    permission_preset: str = "repo_readonly"
    """Reference to a known permission preset."""
    handoff_contract: str = ""
    """Reference to a known Handoff Contract."""
    identity_drift_guards: IdentityDriftGuard = Field(
        default_factory=IdentityDriftGuard
    )


class TeamContract(BaseModel):
    """A formal team contract declaring required capabilities and role inventory."""
    id: str
    required_capabilities: List[str] = Field(default_factory=list)
    role_inventory: List[str] = Field(default_factory=list)
    permission_preset_mapping: Dict[str, str] = Field(default_factory=dict)
    """role_id → preset_id mapping."""
    handoff_contract_inventory: List[str] = Field(default_factory=list)
