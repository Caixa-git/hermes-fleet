# Hermes Agency

**From goal to team. Where Kanban meets agency-agents.**

> **Status**: v0.1 — Pre-alpha. Goal-to-team composition only.
> Execution is delegated entirely to [Hermes Agent Kanban](https://github.com/NousResearch/hermes-agent).

```
Goal ──→ Hermes Agency ──→ Team + Roles + Task DAG
                                   │
                                   ▼
                          Hermes Kanban (execution)
```

---

## What This Is

**Hermes Agency** accepts a goal and produces a team — with roles, policies, and a task graph — ready for execution by Hermes Agent Kanban.

It sits exactly at the intersection of two projects:

| | Project | What it provides |
|---|---|---|
| **Kanban** | [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Multi-agent execution runtime. Task state machine, dispatcher, worker pool, workspace management, failure handling, circuit breakers. |
| **Agency** | [agency-agents](https://github.com/msitarzewski/agency-agents) | Upstream role specifications. Occupational definitions for every agent type — identity, mission, permitted work, boundaries. |

Hermes Agency is the bridge between them: it reads goal language, composes the right team from agency-agents roles, generates SOUL.md identity and policy.yaml boundaries per role, and outputs a Kanban task DAG ready for execution.

---

## Why Not Just Use Kanban Directly?

Kanban is excellent at executing tasks — it manages states, dependencies, workspaces, dispatcher routing, and failure recovery. But Kanban has no concept of **team composition**. It doesn't know which roles should work together on a SaaS app versus a security audit. It doesn't generate SOUL.md identity declarations or policy.yaml permission boundaries.

agency-agents has the role definitions — detailed, proven occupational specs — but no execution layer. A role spec on its own does nothing.

Hermes Agency closes the gap:

- **planner** — goal analysis + team composition (which roles, which order)
- **generator** — SOUL.md (identity) + policy.yaml (boundaries) per role
- **bridge** — task DAG → Kanban API calls (`kanban_create`)

Everything after that is pure Kanban.

---

## Quickstart

```bash
# Install from source
pip install -e .

# Plan a team for your goal
hermes-agency plan "Build a SaaS MVP with subscription billing"

# Apply the plan to Kanban (creates tasks with roles + policies)
hermes-agency apply
```

---

## CLI

```
hermes-agency init          Create project configuration
hermes-agency plan <goal>   Analyze goal → recommend team + task DAG
hermes-agency apply         Register plan with Hermes Kanban
```

---

## Project Dependencies

This project builds on and acknowledges two upstream projects:

| Dependency | License | Source |
|---|---|---|
| **Hermes Agent** (Kanban) | MIT | [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) |
| **agency-agents** (Role specs) | MIT | [github.com/msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) |

Both are MIT-licensed. This project uses MIT as well. See [LICENSE](./LICENSE) for the full text including both copyright notices.

---

## Design Foundations

The team composition logic in Hermes Agency is grounded in academic research:

1. **Agent-Oriented Planning** — Wooldridge, Jennings, Rao, Georgeff (solvability, completeness, non-redundancy)
2. **LLM-based Multi-Agent Systems Survey** — Profile, perception, self-action, mutual interaction, evolution
3. **NIST RBAC / Sandhu "Role-Based Access Control Models"** — IEEE Computer, 1996 (least privilege, separation of duties)
4. **Contract Net Protocol** — Smith, IEEE Trans. Computers, 1980 (task contracts, structured handoff)

See [DESIGN_FOUNDATIONS.md](./DESIGN_FOUNDATIONS.md) for detailed references.

---

## Where This Came From

Hermes Agency replaces [Hermes Fleet](https://github.com/Caixa-git/hermes-fleet) (v0.1–v0.4), which attempted to build an independent container orchestration layer for multi-agent work. That approach duplicated what Kanban already does. Hermes Agency takes the opposite approach: delegate execution to Kanban entirely, focus exclusively on what Kanban lacks — goal-to-team composition with role-pure identity injection.

---

## License

MIT. Includes copyright notices from Nous Research (Hermes Agent) and AgentLand Contributors (agency-agents). See [LICENSE](./LICENSE).
