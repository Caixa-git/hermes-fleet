# Hermes Fleet

**A secure team bootstrapper for isolated Hermes Agent fleets.**

> **Status**: v0.1 — Generator and Validator. Generates configuration only. Does not execute agents or require an existing Hermes installation.

Prompt is not a permission boundary. Container is.

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

## Quickstart

### Installation

```bash
pip install hermes-fleet
```

### Usage

```bash
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

## Example

```bash
$ hermes-fleet plan "Build a medium-sized SaaS MVP"
Recommended team: saas-medium

Agents:
  - orchestrator
  - product-manager
  - ux-designer
  - frontend-developer
  - backend-developer
  - database-architect
  - qa-tester
  - security-reviewer
  - technical-writer

Defaults:
  - Each agent runs in its own Docker container
  - Each agent has its own /opt/data
  - Developers get isolated worktrees
  - Reviewers are read-only
  - Security reviewers have no network
  - Deployer is disabled by default
  - Production secrets are not injected
  - Kanban handoff contracts are enabled

Press Enter to continue with safe defaults.
```

---

## Core Philosophy

| Principle | Meaning |
|-----------|---------|
| Prompt is not a permission boundary | A prompt can be ignored or forgotten. A container cannot. |
| Every agent is a container | No shared memory, workspace, or secrets across agents. |
| Every role has a SOUL.md and a policy.yaml | Identity + enforceable boundaries. |
| Docker/container isolation is the real boundary | The runtime enforces what the prompt describes. |
| Every task is a contract | Tasks have required inputs and required outputs. |
| Every handoff is validated | Handoffs must contain required fields. |
| Memory is private; handoff is public | Each agent's memory stays in its own container. |
| Least privilege by default | Agents start with minimal permissions. |
| The orchestrator coordinates, but does not execute | Orchestrators manage Kanban; they do not write code. |
| Enter should choose the safe default | The default path is always the most restrictive one. |

---

## Team Presets

### General Development Team (general-dev)
A small, general-purpose development team for ordinary software tasks.

- orchestrator
- fullstack-developer
- reviewer
- qa-tester
- technical-writer

### Medium SaaS Team (saas-medium)
A balanced team for a medium-sized SaaS MVP.

- orchestrator
- product-manager
- ux-designer
- frontend-developer
- backend-developer
- database-architect
- qa-tester
- security-reviewer
- technical-writer

Optional (disabled by default): deployer, growth-marketer, customer-support-specialist

---

## What This Project Is

A secure team bootstrapper and configuration generator for role-based Hermes Agent fleets.

## What This Project Is Not (v0.1)

- Not a replacement for Hermes Agent
- Not a new LLM agent runtime
- Not a full dashboard or Kanban application
- Not a deployment platform
- Not a production secret manager
- Not a system that executes real long-running agents

The first MVP is a **generator and validator**.

---

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for the full development plan.

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the system design.

---

## Specification

See [SPEC.md](./SPEC.md) for the detailed technical specification.

---

## License

MIT
