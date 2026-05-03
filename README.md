# Hermes Fleet — DEPRECATED

> **This project has been deprecated and replaced by [Hermes Agency](https://github.com/Caixa-git/hermes-agency).**
>
> **hermes-agency** is the successor. It takes a goal and produces a team — with roles, policies, and a task graph — ready for execution by Hermes Agent Kanban.
>
> Hermes Fleet (v0.1–v0.4) attempted to build an independent container orchestration layer for multi-agent work. That approach duplicated functionality that [Hermes Agent Kanban](https://github.com/NousResearch/hermes-agent) already provides. Hermes Agency takes the opposite approach: **planning only, zero execution, complete delegation to Kanban.**

---

## Migration

```bash
# Old
pip install hermes-fleet
hermes-fleet plan "Build a SaaS MVP"

# New
pip install hermes-agency
hermes-agency plan "Build a SaaS MVP"
```

---

## What Was Here

| Version | Focus | Status |
|---------|-------|--------|
| v0.1 | Generator and Validator | Deprecated |
| v0.2 | Contract-driven composition, agency-agents import | Deprecated |
| v0.3 | Container lifecycle (up/down/status/logs) | Deprecated |
| v0.4 | Isolation runtime (memory/network/state) | Deprecated |

All four versions are superseded by hermes-agency v0.1+.

---

## License

MIT — see [LICENSE](./LICENSE)
