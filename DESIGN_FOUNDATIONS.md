# Hermes Agency — Design Foundations

> Frozen design foundations that underpin the deterministic team composition system.
> These sources change slowly through strict proposal → impact analysis → test → approval.

---

## 1. Purpose

Hermes Agency is built on one principle: **every agent has a pure role**.

No agent drifts outside its role. No agent does work it wasn't assigned. No agent knows about other agents. The orchestrator is the sole communication channel.

Team composition must be **deterministic** and **grounded**. The same input, the same locked refs, the same mapping table → the same team.

---

## 2. Foundation Sources (v1)

### 2.1 Agent-Oriented Planning in Multi-Agent Systems

**Reference**: Classic multi-agent planning literature (Wooldridge, Jennings, Rao, Georgeff).

**Concepts applied**:
- **Solvability** — Can the team's composition solve the stated goal?
- **Completeness** — Are all necessary roles present?
- **Non-redundancy** — No unnecessary roles. Every role maps to a required capability.

### 2.2 LLM-based Multi-Agent Systems Survey

**Reference**: Survey taxonomies of LLM-based multi-agent systems.

**Concepts applied**:
- **Profile** — SOUL.md defines agent identity, mission, non-goals.
- **Perception** — policy.yaml bounds what an agent can see and do.
- **Self-action** — Autonomous operation within allowed scope.
- **Mutual interaction** — Handoff contracts structure agent communication.
- **Evolution** — agency-agents updates bring new/improved role definitions.

### 2.3 NIST RBAC / Sandhu "Role-Based Access Control Models"

**Reference**: Sandhu et al., IEEE Computer, 1996. ANSI INCITS 359.

**Concepts applied**:
- **Least privilege** — Every agent starts with minimum required permissions.
- **Role-permission mapping** — Explicit, auditable preset-to-role mapping.
- **Separation of duties** — Security reviewer ≠ implementer. Orchestrator ≠ developer.

### 2.4 Contract Net Protocol (CNP)

**Reference**: Smith, "The Contract Net Protocol", IEEE Trans. Computers, 1980.

**Concepts applied**:
- **Task contract** — Every task has formal inputs, outputs, validation.
- **Manager-contractor** — Orchestrator assigns; agent executes.
- **Structured reporting** — Handoff notes follow role-specific templates.
- **Human verification** — User approval is the final completion gate.

---

## 3. Foundation Lifecycle

Foundation sources are pinned in `.fleet/foundation.lock.yaml`:

```yaml
foundation_version: 1
sources:
  - id: agent_oriented_planning
    version: "v1"
    locked_at: "2026-05-03"
  - id: llm_mas_survey
    version: "v1"
    locked_at: "2026-05-03"
  - id: nist_rbac
    version: "v1"
    locked_at: "2026-05-03"
  - id: contract_net_protocol
    version: "v1"
    locked_at: "2026-05-03"
```

### Update Procedure

1. Proposal — Document which source to update and why
2. Impact analysis — Assess affected contracts and presets
3. Regression test — Verify unchanged inputs still produce identical outputs
4. Human approval — Explicit sign-off
5. Version bump — Increment foundation_version

The planner is **foundation-bound**. It cannot invent new principles, roles, or handoff protocols beyond what the locks define.
