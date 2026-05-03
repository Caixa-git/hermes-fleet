# Hermes Fleet — Roadmap

---

## v0.1 — Generator and Validator

**Goal**: Self-contained CLI that generates secure, role-based Hermes Agent team configurations.
**Strengthens**: Role (role presets, SOUL.md), Boundary (policy.yaml, Docker Compose, safe-defaults)

### Features
- [x] Team presets: `general-dev`, `saas-medium`
- [x] Role definitions for all agents in presets
- [x] Permission presets (repo_readonly, frontend_worktree_rw, etc.)
- [x] CLI: `hermes-fleet init` — create `.fleet/fleet.yaml`
- [x] CLI: `hermes-fleet plan "<goal>"` — recommend team via keyword heuristic
- [x] CLI: `hermes-fleet generate` — generate all config
- [x] CLI: `hermes-fleet test safe-defaults` — validate output
- [x] SOUL.md generation (Python f-strings)
- [x] policy.yaml generation (Python f-strings + yaml.dump)
- [x] Docker Compose generation (per-agent services with security defaults)
- [x] Kanban handoff template generation
- [x] Safe-defaults validator (22 checks across 16 check functions)
- [x] Automated test suite (161 tests)

### Quality Bar
- All tests pass
- Generated files are deterministic
- v0.1 scope is respected
- No real secrets are generated
- No global Hermes config is modified
- No existing Hermes state is read or written
- Docker Compose is generated but not run
- Security defaults are conservative

---

## v0.2 — Team Expansion, Role Fidelity, and agency-agents Import (Current)

**Goal**: More team presets, user customization, agency-agents import, and role-fidelity infrastructure.
**Strengthens**: Role (agency-agents import, provenance metadata, preserve compiler), Completion (contract schemas, handoff contracts)

### Role Fidelity
- [x] agency-agents upstream import interface: fetch, parse, compile agency-agents YAML persona files into fleet roles
- [x] SOUL.md provenance metadata: `source_repository`, `source_ref`, `source_path`, `source_hash`
- [x] Preserve-mode compiler: original role specs included verbatim or near-verbatim with provenance fields
- [x] Role-diff view: show what changed when agency-agents ref is updated (`hermes-fleet agency diff`)

### Two Lock Layers
- **foundation.lock.yaml** (in `.fleet/`): pins four design foundation sources (see `DESIGN_FOUNDATIONS.md`). Updated via strict proposal → impact analysis → regression test → human approval → version bump.
- **agency.lock.yaml** (in `.fleet/`): pins upstream role inventory. Updated via lighter fetch → diff → compile → preserve test → policy impact check → handoff impact check → user approval → promote.
- The two layers are independent. Foundation updates are rare (months to years). Agency updates are frequent (weeks to months).
- The onboarding AI is a foundation-bound planner: it synthesizes teams within the locked boundaries. It does not improvise beyond the locks.

### agency-agents Update Model
- [x] Locked ref mechanism: commit SHA or release tag stored in `.fleet/agency.lock.yaml`
- [x] `hermes-fleet agency fetch` — pull latest upstream without applying
- [x] `hermes-fleet agency diff` — show role definition changes since locked ref
- [x] `hermes-fleet agency update` — compile + provenance metadata → custom roles → user approval → promote
- [x] Never auto-apply latest `main` (always requires explicit `agency update`)

### Team Expansion
- [x] Additional team presets: `iphone-app`, `ai-app`, `security-audit`, `research-writing`, `content-creator`, `devops-deployment` (8 total)
- [x] New role adoption gate: each new role must pass all three pillar checks (Role ✓, Boundary ✓, Completion ✓)
- [x] `hermes-fleet customize` — fleet configuration (roles, permissions, resources)
- [x] Custom role definitions from local YAML files (`.fleet/roles/`)
- [x] Permission preset customization (`.fleet/permissions/`)
- [x] Expanded safe-defaults checks (CPU/memory limits, task types)
- [x] Per-agent CPU/memory resource customization (fleet.yaml → Docker Compose)

### Contract-Driven Team Composition
- [x] **Team Proposal schema**: onboarders (human or AI) output constrained to a fixed schema — `recommended_team_id`, `rationale`, optional `customizations` only
- [x] **Team Contract**: Pydantic schema for team YAML files with id, name, agents, optional_agents
- [x] **Role Contract**: Pydantic schema with provenance, permission_preset, handoff_contract, task types
- [x] **Handoff Contract**: Pydantic schema with from_roles, allowed_next_roles, required_fields, validation_rules — 4 YAML presets deployed
- [x] **foundation.lock.yaml / agency.lock.yaml**: dual lock layers with Pydantic contracts
- [x] **Cross-reference validation**: team→role, role→preset, role→handoff, handoff→role all verified
- [x] **Deterministic allocation**: same locks + same goal → same team every time

### Testing (v0.2+)
- [x] **Contract Schema Tests**: every contract validates against its Pydantic schema
- [x] **Cross-Reference Tests**: all role/handoff/preset references resolve
- [x] **Safety Invariant Tests**: hard rules that must never be violated (reviewers read-only, etc.)
- [x] **Deterministic Allocation Tests**: same input → identical output (8 teams, Docker Compose, resources)
- [x] **Handoff Validation Tests**: handoffs enforce their own required fields

---

## v0.3 — Container Lifecycle Management (Current)

**Goal**: Actually run the generated containers and manage agent lifecycles.
**Strengthens**: Boundary (container lifecycle, volume persistence)

### Container Lifecycle
- `hermes-fleet up` — start the fleet (docker compose up)
- `hermes-fleet down` — stop the fleet
- `hermes-fleet status` — check agent health (container-level: running/stopped/crashed)
- `hermes-fleet logs <agent>` — view agent logs
- `hermes-fleet restart <agent>` — restart individual agent
- Container health checks and restart policies
- Volume persistence management

### Validation
- `hermes-fleet validate` extended with handoff contract required_fields check:
  every handoff contract must define at least one required_field

---

## v0.4 — Agent Runtime and AI Onboarding

**Goal**: Agent-level state management (ACTIVE/IDLE), token budget enforcement, handoff contract runtime, and optional AI onboarding provider.
**Strengthens**: Completion (agent lifecycle, handoff contract runtime, AI onboarding)

### Token Budget and Agent Runtime
- fleet.yaml `max_iterations_per_session` field for per-agent token budget
- Agent lifecycle state machine: CREATED → ACTIVE → IDLE → COMPLETED → ARCHIVED
- IDLE agents reject messages; orchestrator must wake them explicitly
- Loop detection: tool-call output entropy monitoring (same input+output patterns trigger alert)
- Team presets annotated with token consumption class (light/medium/heavy) based on collected data

### AI Onboarding Provider (Optional)
- Plugin interface for LLM-backed team recommendation
- AI output constrained to the **Team Proposal schema**:
  `recommended_team_id`, `rationale`, optional `customizations` only
- Schema-validated: proposal rejected if team ID, roles, presets, or
  handoff contracts don't resolve against known inventories
- No auto-apply: every AI proposal must pass validation gates before
  generation proceeds
- The AI is a **foundation-bound planner**: it operates within the
  boundaries of `foundation.lock.yaml` and `agency.lock.yaml`

### Handoff Contract Runtime
- **Handoff contract validation at handoff time**: when agent A hands off
  to agent B, the handoff contract is checked against the runtime state
  of the handoff document
- **Handoff rejection**: if required fields are missing or validation
  rules fail, the handoff is rejected and the orchestrator is notified
- **from_roles enforcement**: agent A must be in the contract's
  `from_roles` list; agent B must be in `allowed_next_roles`

---

## v0.5 — Orchestrator Agent Integration

**Goal**: The orchestrator agent can manage the fleet autonomously — assign tasks, detect stalls, request status, and improve agent performance over time. The self-improving loop is the core value: orchestrator makes the fleet smarter, not just louder.
**Strengthens**: Completion (task orchestration, self-improvement loop, agent lifecycle management)

- **Fleet event bus** for agent-to-agent communication
- **Orchestrator SOUL.md** with fleet management capabilities: create, assign, handoff tasks
- **Orchestrator can detect stalled agents** — agents exceeding budget or producing no output
- **Orchestrator can request fleet status** — `hermes-fleet status` integration
- **Orchestrator can improve agents** — rewrite agent SOUL.md, skills, and config based on observed performance (Hermes Alpha-style meta-agent pattern)
- **Integration with Hermes Agent delegation system** (`delegate_task` for subagent spawning)
- **Terminal-based orchestrator dashboard** — real-time view of agent states, tasks, and health

---

## v0.6 — Policy Enforcement, Runtime Handoff, and Recovery

**Goal**: Runtime policy enforcement at the container boundary. Role-specific handoff contracts validated at runtime. Self-healing from violations.
**Strengthens**: Boundary (policy enforcer, runtime enforcement), Completion (runtime handoff validation, recovery)

### Policy Enforcement
- Policy enforcer sidecar per container
- Filesystem write allow/deny enforcement
- Command execution allow/deny enforcement
- Network access enforcement
- Secret injection with allowlist enforcement
- Violation detection and logging
- Soft/medium/hard/critical violation levels
- Role drift detection and alerting

### Runtime Handoff Validation
- **Role-specific handoff validation**: each agent's handoff contract is validated against its role's required outputs (not just common template)
- **Isolation audit**: periodic verification that agent A cannot access agent B's data, files, or secrets

### Recovery and Self-Healing
- Soft violations: request correction, document in audit log
- Medium violations: block task, notify orchestrator
- Hard violations: pause container, preserve workspace snapshot, require review
- Critical violations: kill container, redact output, create security incident, recommend secret rotation
- Workspace snapshot preservation for forensic analysis

---

## v0.7 — Kanban Runtime and Fleet Mode

**Goal**: Built-in Kanban board for task tracking and handoff visualization. Repo Fleet Mode — ingest an existing repo, create a fleeted workspace, and run a PR-based team workflow.
**Strengthens**: Completion (kanban visualization, task tracking), Integration (repo ingestion, GitHub workflow)

### Kanban Runtime
- `hermes-fleet task create` — create a task
- `hermes-fleet task assign <agent>` — assign task to agent
- `hermes-fleet task handoff <from> <to>` — handoff with validation
- `hermes-fleet task complete <id>` — complete task with gates
- Task contract validation (required inputs/outputs)
- Blocker reporting and escalation
- Kanban board visualization (terminal-based web UI)

### Fleet Mode (New Project)
- `hermes-fleet fleet new "<goal>"` — create new fleeted repo from goal
- Team proposal from goal only (no fingerprint needed)
- Auto-create fleeted repo on GitHub

### Fleet Mode (Existing Repo)
- `hermes-fleet fleet ingest <repo-url> "<goal>"` — ingest existing repo
- Read-only source clone, fleeted repo creation
- Repository fingerprint generation
- Team proposal from fingerprint + goal
- First issue auto-created for orchestrator

|---

## v1.0 — Production-Ready

- CI/CD integration (GitHub Actions, automated releases)
- Published to PyPI
- Comprehensive documentation
- Web dashboard (fleet overview, agent logs, Kanban board)
- Secret management integration (no placeholders)
- Audit log export
- Multiple parallel active fleets
- Helm chart for Kubernetes deployment
- **Agency-agents lifecycle management**: full update workflow with automatic contract validation
- **Role-fidelity certification**: guaranteed provenance chain for every agent's role specification

---

## Future Ideas

- **Self-healing agents**: detect violations and recover automatically
- **Dynamic scaling**: add/remove agents mid-project
- **Fleet templates**: save and share team configurations
- **Marketplace**: community role definitions
- **Hermes-native mode**: integrate directly with Hermes Agent gateway
- **Multi-project orchestration**: coordinate across multiple repositories
