# Hermes Fleet

**A secure team bootstrapper for isolated Hermes Agent fleets.**

> **Status**: v0.1 — Generator and Validator. Generates configuration only. Does not execute agents or require an existing Hermes installation.

Prompt is not a permission boundary. Container is.

```
  ╔═══════════════════════════════════╗
  ║  Role.  Boundary.  Completion.    ║
  ║                                   ║
  ║  A simple knife is the most       ║
  ║  deadly.                          ║
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

## Core Pillars

Hermes Fleet gives every agent a role to preserve, a boundary it cannot
cross, and a completion contract it must satisfy.

### 1. Role — Who the agent is

Every agent's identity is traceable to an upstream role specification
(agency-agents). The compiler preserves the original spec — no AI
summarization, no drift. Provenance metadata is recorded in every SOUL.md.

*Key question: "Who is this agent, and what should it do?"*

### 2. Boundary — What the agent can and cannot do

Role identity is aspirational; the container is the boundary. policy.yaml
defines filesystem, network, secret, and command permissions. Docker
enforces them with `cap_drop`, `read_only`, `network: none`, and similar
hardware-enforced mechanisms.

*Key question: "What can this agent do, and what is off-limits?"*

### 3. Completion — When work is truly done

Handoff is a role-specific contract, not a generic message. Each role
defines its own required outputs, validation rules, and completion gates.
The receiving agent must be able to continue from the handoff alone.

Done = output + verification + record + handoff.

*Key question: "Is the work really done, and can the next person pick it up?"*

> **Future**: v0.3+ will add formal work-lifecycle tracking and verifiable
> completion definitions under the Agent Accountability Protocol
> (`docs/design/AGENT_ACCOUNTABILITY_PROTOCOL.md`).

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
| **v0.1** (current) | Generator and validator. Team/role presets, safe-defaults checks. |
| **v0.2** (next) | Contract-driven team composition. Team/Role/Handoff Contract schemas. `agency.lock.yaml` and `foundation.lock.yaml`. Deterministic onboarding protocol. |
| **v0.3** | Container lifecycle management. Optional AI onboarding provider. Schema-validated Team Proposal. agency-agents preserve compiler. |
| **v0.4** | Runtime policy enforcement. Isolated Hermes agent execution. Runtime handoff validation. Recovery and self-healing. |
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
