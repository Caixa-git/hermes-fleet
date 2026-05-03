# Hermes Fleet — Roadmap

---

## v0.1 — Generator and Validator (Current)

**Goal**: Self-contained CLI that generates secure, role-based Hermes Agent team configurations.
**Strengthens**: Role (role presets, SOUL.md), Boundary (policy.yaml, Docker Compose, safe-defaults)

### Features
- [x] Team presets: `general-dev`, `saas-medium`
- [ ] Role definitions for all agents in presets
- [ ] Permission presets (repo_readonly, frontend_worktree_rw, etc.)
- [ ] CLI: `hermes-fleet init` — create `.fleet/fleet.yaml`
- [ ] CLI: `hermes-fleet plan "<goal>"` — recommend team via keyword heuristic
- [ ] CLI: `hermes-fleet generate` — generate all config
- [ ] CLI: `hermes-fleet test safe-defaults` — validate output
- [x] SOUL.md generation (Python f-strings)
- [x] policy.yaml generation (Python f-strings + yaml.dump)
- [ ] Docker Compose generation (per-agent services with security defaults)
- [ ] Kanban handoff template generation
- [ ] Safe-defaults validator (20+ checks)
- [ ] Automated test suite

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

## v0.2 — Team Expansion, Role Fidelity, and agency-agents Import

**Goal**: More team presets, user customization, agency-agents import, and role-fidelity infrastructure.
**Strengthens**: Role (agency-agents import, provenance metadata, preserve compiler), Completion (contract schemas, handoff contracts)

### Role Fidelity
- agency-agents upstream import interface: fetch, parse, compile agency-agents YAML persona files into fleet roles
- SOUL.md provenance metadata: `source_repository`, `source_ref`, `source_path`, `source_hash`
- Preserve-mode compiler: original role specs included verbatim or near-verbatim
- Role-diff view: show what changed when agency-agents ref is updated

### Two Lock Layers
- **foundation.lock.yaml** (in `.fleet/`): pins four design foundation sources (see `DESIGN_FOUNDATIONS.md`). Updated via strict proposal → impact analysis → regression test → human approval → version bump.
- **agency.lock.yaml** (in `.fleet/`): pins upstream role inventory. Updated via lighter fetch → diff → compile → preserve test → policy impact check → handoff impact check → user approval → promote.
- The two layers are independent. Foundation updates are rare (months to years). Agency updates are frequent (weeks to months).
- The onboarding AI is a foundation-bound planner: it synthesizes teams within the locked boundaries. It does not improvise beyond the locks.

### agency-agents Update Model
- Locked ref mechanism: commit SHA or release tag stored in `.fleet/agency-agents.lock`
- `hermes-fleet agency fetch` — pull latest upstream without applying
- `hermes-fleet agency diff` — show role definition changes since locked ref
- `hermes-fleet agency update` — compile + preserve test + policy impact check + handoff impact check → user approval → promote
- Never auto-apply latest `main`

### Team Expansion
- Additional team presets: `iphone-app`, `ai-app`, `security-audit`, `research-writing`, `content-creator`, `devops-deployment`
- New role adoption gate: each new role must pass all three pillar checks (Role ✓, Boundary ✓, Completion ✓)
- `hermes-fleet customize` — interactive agent configuration
- Custom role definitions from local YAML files
- Permission preset customization
- Expanded safe-defaults checks
- Per-agent CPU/memory resource customization

### Contract-Driven Team Composition
- **Team Proposal schema**: onboarders (human or AI) output constrained to a fixed schema — `recommended_team_id`, `rationale`, optional `customizations` only
- **Team Contract**: formal contract type with `required_capabilities`, `role_inventory`, `permission_preset_mapping`, `handoff_contract_inventory`
- **Role Contract**: formal contract type with `source` provenance, `role_fidelity_mode`, `allowed/forbidden_task_types`, `permission_preset`, `handoff_contract`, `identity_drift_guards`
- **Handoff Contract**: formal contract type with `from_roles`, `allowed_next_roles`, `required_fields`, `validation_rules`, `completion_gate`
- **foundation.lock.yaml**: pins four design foundation sources (Agent-Oriented Planning, LLM MAS Survey, NIST RBAC, Contract Net Protocol). See `DESIGN_FOUNDATIONS.md`.
- **Foundation-bound planner**: the Planner is constrained by the locked foundations. It cannot invent new principles or role taxonomies beyond the locks.
- **Two lock layers**: `foundation.lock.yaml` (rarely updated, strict process) vs `agency.lock.yaml` (more frequent, lighter process)
- Proposal validation gates: team ID must exist, all roles in inventory, all presets known, all handoff contracts known
- Deterministic allocation: same `foundation.lock.yaml` + same `agency.lock.yaml` + same goal → same team every time

### Testing (v0.2+)
- **Contract Schema Tests**: every contract validates against its Pydantic schema
- **Cross-Reference Tests**: all role/handoff/preset references resolve
- **Safety Invariant Tests**: hard rules that must never be violated (reviewers read-only, etc.)
- **Deterministic Allocation Tests**: same input → identical output
- **Handoff Validation Tests**: handoffs enforce their own required fields

---

## v0.3 — Container Lifecycle Management, AI Onboarding, and Preserve Compiler

**Goal**: Actually run the generated containers, manage agent lifecycles,
introduce an optional AI onboarding provider, and implement the
agency-agents preserve compiler.
**Strengthens**: Boundary (container lifecycle, volume persistence), Completion (handoff contract runtime, AAP tracking)

### Container Lifecycle
- `hermes-fleet up` — start the fleet (docker compose up)
- `hermes-fleet down` — stop the fleet
- `hermes-fleet status` — check agent health
- `hermes-fleet logs <agent>` — view agent logs
- `hermes-fleet restart <agent>` — restart individual agent
- Container health checks and restart policies
- Volume persistence management

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

### agency-agents Preserve Compiler
- Fetch upstream agency-agents role definitions
- Compile to fleet Role Contracts with provenance metadata
- Preserve mode: original spec included verbatim or near-verbatim
- Role-diff view: show what changed when agency-agents ref is updated

### Handoff Contract Runtime
- **Handoff contract validation at handoff time**: when agent A hands off
  to agent B, the handoff contract is checked against the runtime state
  of the handoff document
- **Handoff rejection**: if required fields are missing or validation
  rules fail, the handoff is rejected and the orchestrator is notified
- **from_roles enforcement**: agent A must be in the contract's
  `from_roles` list; agent B must be in `allowed_next_roles`

---

## v0.4 — Policy Enforcement, Runtime Handoff, and Recovery

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

## v0.5 — Kanban Runtime and Fleet Mode

**Goal**: Built-in Kanban board for task handoff between agents. First
version of Repo Fleet Mode — ingest an existing repo, create a fleeted
workspace, and run a PR-based team workflow.
**Strengthens**: Completion (kanban runtime, task handoff validation)

### Kanban Runtime
- `hermes-fleet task create` — create a task
- `hermes-fleet task assign <agent>` — assign task to agent
- `hermes-fleet task handoff <from> <to>` — handoff with validation
- `hermes-fleet task complete <id>` — complete task with gates
- Task contract validation (required inputs/outputs)
- Blocker reporting and escalation
- Orchestrator dashboard (terminal-based)

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

---

## v0.6 — Orchestrator Agent Integration

**Goal**: The orchestrator agent can manage the fleet autonomously.

- Fleet event bus for agent-to-agent communication
- Orchestrator SOUL.md with Kanban management capabilities
- Orchestrator can create, assign, handoff tasks
- Orchestrator can detect stalled agents
- Orchestrator can request fleet status
- Integration with Hermes Agent delegation system

---

## v1.0 — Production-Ready

- Web dashboard (fleet overview, agent logs, Kanban board)
- Secret management integration (no placeholders)
- Audit log export
- Multiple parallel active fleets
- CI/CD integration
- Comprehensive documentation
- Published to PyPI
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
