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
