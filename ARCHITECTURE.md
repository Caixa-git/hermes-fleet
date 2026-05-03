# Hermes Fleet — Architecture

## System Overview

Hermes Fleet is a **config generator and validator** for multi-agent Hermes Agent teams. It reads team and role definitions, applies safe-default templates, and outputs complete team configurations ready for deployment.

It operates in two modes:

| Mode | Input | Output |
|------|-------|--------|
| **New Project** | User goal text | Generated team config in `.fleet/generated/` |
| **Existing Repo (Fleet Mode)** | GitHub repo URL + goal | Fleeted repo + team + first issue |

This document covers the New Project architecture. See
`REPO_FLEET_MODE.md` for the Fleet Mode design.

```
User goal text
      │
      ▼
┌─────────────┐
│   Planner   │ ──► Team recommendation (general-dev / saas-medium)
└─────────────┘
      │
      ▼
┌─────────────┐
│  Generator  │ ──► .fleet/generated/
│             │       ├─ docker-compose.generated.yaml
│   ┌───────┐ │       ├─ agents/orchestrator/SOUL.md
│   │Roles  │ │       ├─ agents/orchestrator/policy.yaml
│   ├───────┤ │       ├─ agents/frontend-developer/SOUL.md
│   │Teams  │ │       ├─ agents/frontend-developer/policy.yaml
│   ├───────┤ │       ├─ agents/.../
│   │Policy │ │       └─ kanban/
│   ├───────┤ │          ├─ task-template.md
│   │Docker │ │          ├─ handoff-template.md
│   ├───────┤ │          └─ completion-gates.yaml
│   │Kanban │ │
│   └───────┘ │
└─────────────┘
      │
      ▼
┌────────────────┐
│   Validator    │ ──► Safe-defaults report
│  (test-safe-   │       ✓ No privileged containers
│   defaults)    │       ✓ No docker.sock mounts
│                │       ✓ All agents have separate /opt/data
│                │       ✓ Security reviewer has no network
│                │       ✓ Deployer disabled by default
│                │       ✓ ...
└────────────────┘
```

## Layer Architecture

### 1. Definition Layer (presets/ + .lock files)

Static YAML files that define what teams and roles exist. The definitions
are grounded in two lock layers:

| Lock File | Contents | Update Cadence | Location |
|-----------|----------|----------------|----------|
| `foundation.lock.yaml` | Design foundations: Agent-Oriented Planning, LLM MAS Survey, NIST RBAC, Contract Net Protocol | Months to years (strict process) | See `DESIGN_FOUNDATIONS.md` |
| `agency.lock.yaml` | Upstream role inventory from agency-agents | Weeks to months (lighter process) | See agency-agents update model |

- `presets/teams/` — Team compositions (which roles belong to which team)
- `presets/roles/` — Individual role definitions (permissions, allowed tasks, network policy)

### 2. Schema Layer (src/hermes_fleet/schema.py)

Pydantic models for all data structures:

- `RoleDefinition` — identity, mission, non-goals, allowed/forbidden work, permissions
- `TeamDefinition` — team name, description, list of roles with assignments
- `PermissionPreset` — reusable permission templates (repo_readonly, frontend_worktree_rw, etc.)
- `NetworkPolicy` — network access mode (none, web_readonly, package_registry, internal_only)
- `SecretPolicy` — per-agent secret allowlist
- `DockerServiceConfig` — per-agent Docker Compose service definition
- `KanbanTemplate` — handoff contract template structure
- `FleetConfig` — top-level config stored in `.fleet/fleet.yaml`
- `SafeDefaultsResult` — validation result structure

### 3. Planning Layer (src/hermes_fleet/planner.py)

Heuristic-driven team recommender (foundation-bound planner):

- Parse user goal text for keywords
- Match against team descriptions
- Return recommended team + rationale
- v0.1: keyword matching; future: AI-powered recommendation constrained by locked foundations
- The planner is **foundation-bound**: it synthesizes teams within the boundaries of `foundation.lock.yaml` and `agency.lock.yaml`. It does not improvise new principles or role taxonomies beyond the locks.

### 4. Generator Layer (src/hermes_fleet/generator.py)

Python f-string driven rendering + data assembly:

- Load team definition → resolve roles → assemble agent configs
- Render each agent's SOUL.md via `_render_soul_md()` (f-string)
- Render each agent's policy.yaml via `yaml.dump()`
- Render docker-compose via `yaml.dump()` from `generate_docker_compose()`
- Render kanban templates from `kanban.py` (hardcoded templates)

### 5. Policy Layer (src/hermes_fleet/policy.py)

Permission preset resolution and composition:

- Apply permission preset to role definition
- Compose filesystem rules, network rules, secret rules, command allow/deny lists
- Generate complete policy.yaml content

### 6. Docker Compose Layer (src/hermes_fleet/docker_compose.py)

Per-service Docker Compose generation:

- One service per agent
- Security-hardened defaults (cap_drop ALL, no-new-privileges, read-only root fs, tmpfs)
- Per-agent volume mounts (separate /opt/data, separate worktree)
- Network isolation (per-network or no network)
- Resource limits (CPU, memory)

### 7. Kanban Layer (src/hermes_fleet/kanban.py)

Handoff contract template generation:

- Task contract template with required inputs/outputs
- Handoff note template with required sections
- Completion gate template with validation criteria

### 8. Validation Layer (src/hermes_fleet/safe_defaults.py)

Built-in validation checks run against generated output:

- File-based checks (no privileged containers, no docker.sock, etc.)
- Policy checks (every agent has separate /opt/data, reviewer is read-only, etc.)
- Network checks (security-reviewer has no network)
- Secret checks (no production secrets injected by default)
- Isolation checks (no ~/.hermes mutation, no Hermes profile dependency)

### 9. CLI Layer (src/hermes_fleet/cli.py)

Typer-based command-line interface:

- `init` — create `.fleet/fleet.yaml`
- `plan` — recommend a team for a goal
- `generate` — generate all agent configurations
- `test safe-defaults` — validate generated configuration

## Data Flow

```
fleet.yaml (config) ─┐
                     ├──► Planner ──► Team YAML ──► Generator ──► Rendered files
User goal ───────────┘                              │
                                                    │
                                                    ▼
                                              .fleet/generated/
```

## File Output Structure

```
.fleet/
├─ fleet.yaml                        # Project config
└─ generated/
   ├─ docker-compose.generated.yaml  # Multi-service Docker Compose
   ├─ agents/
   │  ├─ orchestrator/
   │  │  ├─ SOUL.md
   │  │  └─ policy.yaml
   │  ├─ frontend-developer/
   │  │  ├─ SOUL.md
   │  │  └─ policy.yaml
   │  ├─ backend-developer/
   │  │  ├─ SOUL.md
   │  │  └─ policy.yaml
   │  └─ .../
   └─ kanban/
      ├─ task-template.md
      ├─ handoff-template.md
      └─ completion-gates.yaml
```

## Design Principles

### Core Pillars

Hermes Fleet is built on three non-negotiable pillars, themselves grounded
in four design foundation sources (see `DESIGN_FOUNDATIONS.md`):

| Pillar | Foundation Source |
|--------|-------------------|
| Role Fidelity | Agent-Oriented Planning (solvability, completeness, non-redundancy); LLM MAS Survey (profile, evolution) |
| Isolation | NIST RBAC / Sandhu RBAC (least privilege, role-permission mapping, separation of duties) |
| Handoff | Contract Net Protocol (task contract, manager-contractor assignment, structured reporting) |

#### 1. Role Fidelity

The framework's most important responsibility is preserving the integrity of each role's source specification.

- **agency-agents** is the upstream role specification dependency. It is not optional decoration — it is the authoritative source for occupational role definitions.
- The compiler's default mode is **preserve**. Role specifications from agency-agents must not be arbitrarily summarized or paraphrased by AI.
- The original role specification is included in SOUL.md **verbatim or near-verbatim**.
- Every SOUL.md records **provenance metadata**:
  - `source_repository` — URL of the agency-agents repository
  - `source_ref` — commit SHA or release tag
  - `source_path` — path to the role spec within the repository
  - `source_hash` — content hash of the original spec

This ensures that the connection between a fleet agent's identity and its upstream role definition is traceable, auditable, and never silently degraded.

#### 2. Isolation

Role identity declared in SOUL.md is aspirational. The actual boundary is enforced by policy.yaml and Docker.

- Every agent gets separate filesystem, memory, network, secret, and command permissions.
- Permission boundaries are expressed in **policy.yaml** — machine-readable, testable, and eventually enforceable at runtime.
- The runtime boundary is the **container**, not the prompt. A prompt can be ignored or forgotten. A container with `cap_drop: ALL`, `read_only: true`, and `network: none` cannot.
- Isolation must be **verifiable**. The safe-defaults validator and future policy enforcer must be able to prove that agent A cannot access agent B's data.

For v0.1, isolation is expressed as generated configuration. In future versions, it will be enforced at runtime.

#### 3. Handoff

Handoff between agents is not a generic message — it is a **role-specific contract**.

- Each role defines its own handoff requirements. A common template alone is insufficient.
- Examples of role-specific handoff differences:
  - **Product Manager** hands off: requirements doc, acceptance criteria, priority score, stakeholder notes.
  - **Backend Developer** hands off: changed files, API contracts, migration status, test results, known edge cases.
  - **Security Reviewer** hands off: risk summary, severity labels, recommended fixes, explicit approve/block decision.
  - **QA Tester** hands off: test results, bug reports, reproduction steps, test coverage gaps.
- Handoff is a **contract**, not a note. The receiving agent must be able to start work from the handoff alone, without reading the sending agent's full history.
- Completion gates validate that the handoff contract is fulfilled before the task moves to the next agent.

---

### General Principles

1. **Self-contained** — No dependency on existing Hermes installation.
2. **Deterministic** — Same input always produces same output.
3. **Verifiable** — Every generated configuration can be validated.
4. **Least privilege** — Defaults are always the most restrictive option.
5. **Composable** — Teams are composed of roles; policies are composed of presets.
6. **Progressive** — Simple defaults work; customization is additive.

## Future Architecture (Post-v0.1)

### Fleet Runtime (v0.3+)

```
                     ┌──────────────────┐
                     │  Fleet Runtime   │
                     │  (Agent Runner)  │
                     └──────┬───────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Container  │    │  Container  │    │  Container  │
│  Manager    │    │  Network    │    │  Volume     │
│  (Docker)   │    │  (compose)  │    │  (persist)  │
└─────────────┘    └─────────────┘    └─────────────┘

┌─────────────────────────────────────────────────┐
│              Policy Enforcer                     │
│  (Reads policy.yaml → Intercepts violations)     │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              Audit Logger                        │
│  (Agent actions, role drift, violations)         │
└─────────────────────────────────────────────────┘
```

### Agency-Agents Update Model

Updating from the upstream `agency-agents` repository follows a controlled, auditable process:

```
1. Fetch ──► git fetch upstream main
2. Diff  ──► Show changed role definitions since locked ref
3. Compile ──► Run fleet compiler against new specs
4. Preserve test ──► Verify existing role integrity is preserved
5. Policy impact check ──► Detect any permission changes (new/removed capabilities)
6. Handoff impact check ──► Detect any handoff requirement changes
7. User approval ──► Present diff summary; require explicit confirmation
8. Promote ──► Update locked ref; regenerate affected agents
```

Key rules:
- **Never auto-apply** `main`. Always lock to a specific commit SHA or release tag.
- The locked ref is stored in the project's `fleet.yaml` or a dedicated `.fleet/agency-agents.lock` file.
- New roles from upstream are only adopted after they pass all three pillar checks:
  - Role Fidelity: Provenance metadata is complete.
  - Isolation: policy.yaml and Docker boundaries are defined.
  - Handoff: Role-specific handoff requirements exist.
- If an upstream update breaks a contract, the compiler blocks promotion and reports the issue.

---

### Fleet Mode Architecture (v0.5+)

See `REPO_FLEET_MODE.md` for the complete design. In brief:

```
Source Repo (read-only)
    │ clone
    ▼
┌─────────────────────┐
│  Fingerprint Engine │──► .fleet/fingerprint.yaml
└─────────────────────┘         (lang, deps, CI, risk flags)
    │
    ▼
┌─────────────────────┐
│  Planner            │──► Team Proposal (fingerprint + goal)
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  GitHub API Layer   │──► Create fleeted repo
│  (Fleet Orchestrator)│──► Open first issue
└─────────────────────┘   │
                          ▼
                   PR-based agent workflow
                   (issue → branch → commit → PR → merge gate)
```

The Fleet Mode adds three new components:

1. **Fingerprint Engine** — analyzes source repo to produce
   `.fleet/fingerprint.yaml` with language, complexity, security posture,
   and risk flags.
2. **GitHub API Layer** — creates the fleeted repo, manages issues,
   branches, and PRs via GitHub API.
3. **Merge Gate** — classifies each PR by risk level and decides
   whether to auto-merge or request human approval.

---

## Contract Architecture (v0.2+)

The framework is moving toward a contract-driven team composition model. Every team, role, and handoff is a formal, testable contract.

### Why Contracts

A human or AI onboarding agent must not freely invent team structures. Every team composition must be:
- **Deterministic**: same input → same team, every time
- **Verifiable**: team structure can be validated against schemas
- **Traceable**: every role has a provenance chain back to an upstream spec
- **Testable**: each contract has its own test category

### Team Contract

A Team Contract declares the required capabilities of a team and the roles that fulfill them.

```yaml
team_contract:
  id: saas-medium
  required_capabilities:
    - product_management
    - frontend_development
    - backend_development
    - database_architecture
    - quality_assurance
    - security_review
    - technical_writing
  role_inventory:
    - orchestrator
    - product-manager
    - frontend-developer
    - backend-developer
    - database-architect
    - qa-tester
    - security-reviewer
    - technical-writer
  permission_preset_mapping:
    orchestrator: orchestrator_safe
    product-manager: docs_rw_repo_ro
    frontend-developer: frontend_worktree_rw
    backend-developer: backend_worktree_rw
    security-reviewer: readonly_no_network
  handoff_contract_inventory:
    - product-manager_to_frontend-developer
    - product-manager_to_backend-developer
    - frontend-developer_to_reviewer
    - backend-developer_to_security-reviewer
    - developer_to_qa-tester
```

### Role Contract

Each role is a formal contract between the source specification and the fleet agent.

```yaml
role_contract:
  id: security-reviewer
  source:
    repository: https://github.com/agency-agents/agency-agents
    ref: v1.2.0
    path: roles/security-reviewer.yaml
    hash: sha256:a1b2c3...
  role_fidelity_mode: preserve  # or: near-verbatim, summarize
  allowed_task_types:
    - security_review
    - risk_analysis
    - dependency_review
  forbidden_task_types:
    - implementation
    - deployment
    - product_scope_decision
  permission_preset: readonly_no_network
  handoff_contract: security-reviewer_handoff
  identity_drift_guards:
    pre_work:
      - Is this task allowed for my role?
      - Do I have the required context?
      - Do I have permission for the requested action?
      - Should this be handed off?
    post_work:
      - Did I stay inside my role?
      - Did I touch only allowed paths?
      - Did I produce required outputs?
      - Did I leave a clear handoff?
```

### Handoff Contract

Handoffs between specific roles are formal contracts with validation rules.

```yaml
handoff_contract:
  id: security-reviewer_handoff
  from_roles:
    - backend-developer
    - fullstack-developer
  allowed_next_roles:
    - orchestrator
    - technical-writer
  required_fields:
    - risk_summary
    - severity_labels
    - recommended_fixes
    - approval_or_block
    - findings_report
  validation_rules:
    - field: risk_summary
      min_length: 50
      required: true
    - field: severity_labels
      enum: [critical, high, medium, low, info]
      min_items: 1
    - field: approval_or_block
      enum: [approve, block, needs_discussion]
      required: true
  completion_gate:
    required:
      - explicit_approve_or_block
      - no_code_modification
      - all_findings_documented
```

### Team Proposal Schema

When the Planner or an AI onboarding agent proposes a team, its output is limited to a Team Proposal that conforms to a fixed schema:

```yaml
team_proposal:
  goal: "string"
  recommended_team_id: "string"  # must match a known Team Contract
  rationale: "string"
  customizations:              # optional, empty for default
    agents: []                 # subset or superset of role_inventory
    permission_overrides: {}   # role_id → alternative preset
    handoff_overrides: {}      # contract_id → alternative contract
```

The proposal is validated before acceptance:
1. `recommended_team_id` must match a known Team Contract
2. All referenced role IDs must exist in the role inventory
3. All referenced permission presets must exist
4. All referenced handoff contracts must exist
5. Safe-defaults validator runs against the generated output

### Deterministic Allocation

With the same inputs, the same team composition must be produced every time:

- `foundation.lock.yaml` pins the design foundation sources (see `DESIGN_FOUNDATIONS.md`)
- `agency.lock.yaml` pins the upstream role specification versions
- Role inventory is an immutable ordered list (not a set)
- Permission preset mapping is a fixed table
- Handoff contract inventory maps handoffs by ID
- No randomness: no shuffled lists, no randomized agent selection
- No AI-dependent variability: the Team Proposal schema removes free-form team invention; the planner is foundation-bound

### Test Categories (v0.2+)

Tests are organized into five categories:

| Category | What It Tests | Example |
|----------|--------------|---------|
| **Contract Schema Tests** | Every contract validates against its schema | Team Contract has all required fields; Handoff Contract has valid `from_roles` references |
| **Cross-Reference Tests** | All references between contracts resolve | Every role in team contract exists in role inventory; handoff contract references valid roles |
| **Safety Invariant Tests** | Safety rules that must never be violated | Reviewers are always read-only; security reviewers never have network; no privileged containers |
| **Deterministic Allocation Tests** | Same input produces identical output | Same agency lock + same goal → same team, same agents, same policies, same handoffs |
| **Handoff Validation Tests** | Handoff contracts enforce their rules | Security reviewer handoff fails if `approval_or_block` is missing; Product Manager handoff fails without `acceptance_criteria` |

All tests run against **mocked inputs only** — no real AI API calls, no real Docker execution, no real Hermes agent execution. This keeps the test suite fast, deterministic, and dependency-free.
