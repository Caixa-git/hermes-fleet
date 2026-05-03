# Hermes Agency — Architecture

## System Overview

Hermes Agency is a **planning layer** for multi-agent work. It accepts a goal, composes a team, and outputs a task DAG ready for Kanban execution.

It does **nothing** that Kanban already does. It only does what Kanban lacks.

## Data Flow

```
User Goal
    │
    ▼
┌──────────────┐     ┌─────────────────┐     ┌───────────────┐
│   Planner    │────►│   Generator     │────►│  Plan Output  │
│ (keyword)    │     │ (SOUL.md +      │     │  (YAML spec)  │
│              │     │  policy.yaml)   │     │               │
└──────────────┘     └─────────────────┘     └───────┬───────┘
                                                      │
                                              ┌───────▼───────┐
                                              │ Kanban Bridge │ (v0.2+)
                                              │ kanban_create │
                                              └───────────────┘
                                                      │
                                                      ▼
                                              ┌───────────────┐
                                              │ Hermes Kanban │
                                              │ (execution)    │
                                              └───────────────┘
```

## Layers

### 1. Definition Layer — `presets/`
Static YAML: teams, roles, permission presets. Grounded in `foundation.lock.yaml` (academic sources) and `agency.lock.yaml` (role inventory).

### 2. Schema Layer — `contracts.py`
Pydantic models: TeamContract, RoleContract, PermissionPresetContract, HandoffContract, PlanOutput.

### 3. Planning Layer — `planner.py`
Goal → team recommendation → task decomposition. Foundation-bound.

### 4. Generation Layer — `generator.py`
SOUL.md (f-string templates) + policy.yaml (permission preset merge) per role.

### 5. Kanban Bridge — `kanban_bridge.py` (v0.2+)
Plan → Kanban API calls. Not a runtime — just one-shot registration.

## Design Principles

1. **Zero execution** — Planning only. Kanban does the rest.
2. **Role purity** — Every agent has a clear identity (SOUL.md) and boundaries (policy.yaml). Role drift is prevented by design.
3. **Deterministic** — Same input → same plan.
4. **Delegated isolation** — Role boundaries are enforced by policy.yaml + Kanban workspace management, not by containers.
5. **Attributed** — Every role traces back to an upstream agency-agents spec. Every design choice traces back to a locked foundation source.

## What This Project Is Not

- Not a replacement for Hermes Agent
- Not a replacement for Kanban
- Not a container orchestrator
- Not an agent runtime
- Not a policy enforcer
