# Hermes Fleet

**A secure team bootstrapper for isolated Hermes Agent fleets.**

> **Status**: v0.1 — Generator and Validator. Generates configuration only. Does not execute agents or require an existing Hermes installation.

Prompt is not a permission boundary. Container is.

```
  ╔═══════════════════════════════════╗
  ║  Isolation.                       ║
  ║                                   ║
  ║  Every agent has its own room.    ║
  ║  Only the orchestra conductor     ║
  ║  holds all the keys.              ║
  ╚═══════════════════════════════════╝
```

Hermes Fleet helps you turn a vague goal into a safe, role-based Hermes Agent team. Instead of manually wiring profiles, SOUL.md files, Kanban templates, Docker containers, workspaces, and permissions, Hermes Fleet generates a secure team scaffold with least-privilege defaults.

---

## The Problem

Hermes Agent is powerful, but multi-agent work becomes difficult when:

- Multiple roles share the same memory, workspace, permissions, and secrets.
- A single long-running agent starts forgetting its role.
- Handoffs between agents are informal and incomplete.
- Orchestrators start doing worker work.
- Reviewers accidentally become implementers.
- Permissions are described in prompts but not actually enforced.

A role prompt is not enough. The runtime must make unsafe behavior impossible or at least detectable.

---

## The Solution

Hermes Fleet generates a complete, isolated team configuration from a single goal description:

```bash
hermes-fleet plan "Build a medium-sized SaaS MVP"
hermes-fleet generate
hermes-fleet test safe-defaults
```

Each agent gets:
- Its own **SOUL.md** — identity declaration and role boundaries
- Its own **policy.yaml** — machine-readable, enforceable permissions
- Its own **Docker container** — filesystem, network, and secret isolation
- Its own **worktree** — no accidental file conflicts
- Its own **Kanban handoff contracts** — structured, validated handoffs

---

## What v0.1 Does

v0.1 is a **local CLI tool** that generates team configuration as text files. It is a generator and validator — nothing more.

| Capability | Status |
|-----------|--------|
| Read a goal and recommend a team preset | Done |
| Generate SOUL.md for each agent | Done |
| Generate policy.yaml for each agent | Done |
| Generate Docker Compose with security defaults | Done |
| Generate Kanban handoff templates | Done |
| Validate generated config against 22 safe-default rules | Done |
| Deterministic output (same input → same output) | Done |
| Run Docker containers | Not yet (v0.3) |
| Execute Hermes agents | Not yet (v0.3) |
| Validate handoffs at runtime | Not yet (v0.4) |
| AI-powered team recommendation | Not yet (v0.3 optional) |

---

## Single Pillar: Isolation

Hermes Fleet is built on one non-negotiable principle: **every agent is isolated**.

No agent can see another agent's memory, files, network, or secrets. No agent can talk to another agent directly. Even the user cannot talk to sub-agents directly. Every message, every piece of data, every network request must pass through **the orchestrator** — the sole entity that holds all the keys.

From this single pillar, four facets emerge:

### Facet 1: Role — Who lives in each room

Every agent's identity is traceable to an upstream role specification (agency-agents). The compiler preserves the original spec — no AI summarization, no drift. Provenance metadata is recorded in every SOUL.md.

*Key question: "Who is this agent, and what should it do?"*

### Facet 2: Boundary — The walls of the room

Role identity is aspirational; isolation is enforced. policy.yaml defines filesystem, network, secret, and command permissions. Docker enforces with `cap_drop`, `read_only`, `network: none`. Each agent gets its own container, its own memory volume, its own workspace.

*Key question: "What can this agent do, and what is off-limits?"*

### Facet 3: Completion — How work passes between rooms

Handoff is a role-specific contract, not a generic message. Each role defines its own required outputs, validation rules, and completion gates. The receiving agent must be able to continue from the handoff alone. All handoffs pass through the orchestrator.

Done = output + verification + record + handoff.

*Key question: "Is the work really done, and can the next person pick it up?"*

### Facet 4: Orchestrator — The only one who opens doors

The orchestrator is not a separate pillar. It is the runtime agent that can cross isolation boundaries — the sole communication channel between any two entities in the fleet.

- It assigns tasks to sub-agents. They execute in isolation.
- It receives completed work. Verifies. Aggregates.
- It reports to the user. The user approves or redirects.
- It reassigns. The cycle continues.
- If a sub-agent needs temporary network access, it requests the orchestrator. The orchestrator asks the user. User grants a time-limited exception. Isolation is restored automatically on expiry.

```
Agent ──task complete──→ Orchestrator (verify + aggregate)
                           Orchestrator ──report──→ User
                           User ──approve or redirect──→ Orchestrator
                           Orchestrator ──next task or reassign──→ Agent
```

- Sub-agents never contact the user directly. The orchestrator is the sole intermediary.
- No per-agent approval gates. No approval thresholds.
- Policy violations are handled by policy.yaml enforcement, not by user approval.

*Key question: "Who manages the fleet, and how does the user stay in control?"*

The answer: the orchestrator manages. The user controls. They are never the same entity.

---

## What This Project Is

A secure team bootstrapper and configuration generator for role-based
Hermes Agent fleets. It generates team configurations with least-privilege
defaults so that human or AI operators can bootstrap safe multi-agent
work without manually wiring every detail.

## What This Project Is Not (v0.1)

- Not a replacement for Hermes Agent
- Not a new LLM agent runtime or model provider
- Not a full dashboard or Kanban application
- Not a deployment or CI/CD platform
- Not a production secret manager
- Not a system that executes real long-running agents
- Not an AI that reads the latest research and auto-updates team strategy
- Not a Docker container orchestrator (generates Compose files only)

---

## Roadmap

| Version | Focus |
|---------|-------|
| **v0.1** | Generator and validator. Team/role presets, safe-defaults checks. |
| **v0.2** | Contract-driven composition. Pydantic schemas, dual lock layers, agency-agents import. |
| **v0.3** (current) | Container lifecycle: up/down/status/logs/restart. Runtime validation. |
| **v0.4** | Agent runtime. Token budgets, agent lifecycle state machine, handoff contract runtime. |
| **v0.5** | Orchestrator integration. Task assignment, user approval gate, sub-agent autonomy. |
| **v0.6** | Policy enforcement. Runtime handoff validation, violation detection, recovery. |
| **v0.7** | Kanban runtime. Fleet mode with repo ingestion, task tracking, handoff visualization. |
| **v1.0** | Production-ready: audit logging, secret management, CI/CD, web dashboard. |

See [ROADMAP.md](./ROADMAP.md) for the full development plan.

---

## Quickstart

```bash
# Install (from source)
pip install -e .

# Create project configuration
hermes-fleet init

# Describe your goal and get a team recommendation
hermes-fleet plan "Build a medium-sized SaaS MVP with subscription billing"

# Generate all agent configurations
hermes-fleet generate

# Validate safe defaults
hermes-fleet test safe-defaults
```

Generated output goes to `.fleet/generated/` in your project directory. Nothing touches `~/.hermes` or any global Hermes configuration.

---

## Example Flow

```bash
$ hermes-fleet plan "Build a medium-sized SaaS MVP"
Recommended team: saas-medium
  - orchestrator, product-manager, ux-designer, frontend-developer
  - backend-developer, database-architect, qa-tester
  - security-reviewer, technical-writer

$ hermes-fleet generate --force
  [write] .fleet/generated/agents/orchestrator/SOUL.md
  [write] .fleet/generated/agents/orchestrator/policy.yaml
  ... (27 files total)

$ hermes-fleet test safe-defaults --verbose
Safe-defaults validation results:
  Passed: 21  Failed: 0  Skipped: 1
All safe-defaults checks PASSED.
```

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the system design. Key layers:

- **Definition Layer**: Team/role YAML presets + lock files
- **Schema Layer**: Pydantic models for all data structures
- **Planner**: Keyword-based team recommender (foundation-bound)
- **Generator**: Renders SOUL.md, policy.yaml, Docker Compose
- **Validator**: 21 safe-defaults checks
- **CLI**: Typer-based interface

---

## Design Foundations

See [DESIGN_FOUNDATIONS.md](./DESIGN_FOUNDATIONS.md) for the four academic
and standards-based sources that underpin the framework's design principles.

---

## License

MIT

---

## About the Author

Hi, I'm **Caixa-git** — a Korean developer building secure multi-agent systems.
I'm currently open to new opportunities.

If you'd like to reach out: **wjsfund@gmail.com**
