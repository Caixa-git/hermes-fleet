## 14. Agency-Agents Update Model

### 14.1 Two Lock Layers

Hermes Fleet maintains two independent lock layers:

| Lock File | Purpose | Update Cadence | Process |
|-----------|---------|----------------|---------|
| `foundation.lock.yaml` | Pins design foundation sources (see `DESIGN_FOUNDATIONS.md`) | Months to years | Strict proposal → impact analysis → regression test → human approval → version bump |
| `agency.lock.yaml` | Pins upstream role inventory from agency-agents | Weeks to months | Lighter fetch → diff → compile → preserve test → policy impact check → handoff impact check → user approval → promote |

The onboarding AI is a **foundation-bound planner**: it synthesizes teams
within the boundaries of both lock layers. It does not improvise new
principles, role taxonomies, or handoff protocols beyond what the locks
allow. New research or new principles are recorded as proposals only and
never auto-applied.

### 14.2 Update Process

Updating from the upstream `agency-agents` repository follows a controlled, auditable process:

```
1. Fetch     git fetch upstream main
2. Diff      Show changed role definitions since locked ref
3. Compile   Run fleet compiler against new specs
4. Preserve test     Verify existing role integrity is preserved
5. Policy impact check       Detect any permission changes
6. Handoff impact check      Detect any handoff requirement changes
7. User approval     Present diff summary; require explicit confirmation
8. Promote   Update locked ref; regenerate affected agents
```

### 14.3 Locking

- The framework **never auto-applies** `main`. Always lock to a specific commit SHA or release tag.
- The locked ref is stored in the project's `fleet.yaml` or a dedicated `.fleet/agency-agents.lock` file.
- The locked ref is validated before any compile operation.

### 14.4 New Role Adoption Gate

New roles from upstream are only adopted after they pass all three pillar checks:

| Pillar | Gate |
|--------|------|
| Role | Provenance metadata is complete (`source_repository`, `source_ref`, `source_path`, `source_hash`) |
| Boundary | policy.yaml filesystem, network, secret, and command boundaries are defined |
| Completion | Role-specific handoff requirements exist (not just common template fallback) |

If any gate fails, the compiler blocks promotion and reports the specific deficiency.

### 14.5 CLI Interface (Future)

```text
hermes-fleet agency fetch       # Pull latest upstream (no apply)
hermes-fleet agency diff         # Show role changes since locked ref
hermes-fleet agency update       # Full update workflow with gates
hermes-fleet agency lock <ref>   # Pin to specific commit/tag
```

---

