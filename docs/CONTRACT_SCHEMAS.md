## 15. Contract Schemas (v0.2+)

### 15.1 Overview

Teams, roles, and handoffs are expressed as formal, testable contracts. These schemas replace ad-hoc YAML presets with typed, cross-referenced data structures. An AI or human onboarding agent cannot freely invent team structures — its output is constrained to a `Team Proposal` schema that references known contracts.

### 15.2 Team Contract

```yaml
team_contract:
  id: str                          # unique identifier
  required_capabilities: [str]     # what the team must be able to do
  role_inventory: [str]            # ordered list of role IDs
  permission_preset_mapping:       # role_id → preset_id
    role_id: preset_id
  handoff_contract_inventory:      # list of handoff contract IDs
    - contract_id
```

Validation rules:
- `id` must be unique across all team contracts
- Every entry in `role_inventory` must have a corresponding `permission_preset_mapping`
- Every `permission_preset_mapping` value must reference a known permission preset
- Every entry in `handoff_contract_inventory` must reference a known Handoff Contract
- All `required_capabilities` must be covered by at least one role

### 15.3 Role Contract

```yaml
role_contract:
  id: str
  source:
    repository: str                 # URL of upstream repo
    ref: str                        # commit SHA or release tag
    path: str                       # path to spec within repo
    hash: str                       # content hash of original spec
  role_fidelity_mode: preserve | near_verbatim | summarize
  allowed_task_types: [str]
  forbidden_task_types: [str]
  permission_preset: str            # reference to permission preset
  handoff_contract: str             # reference to handoff contract
  identity_drift_guards:
    pre_work: [str]
    post_work: [str]
```

Validation rules:
- `role_fidelity_mode` must be one of the three enumerated values
- `preserve` mode requires that `source.hash` matches the hash of the up-to-date fetched spec
- `allowed_task_types` and `forbidden_task_types` must not overlap
- `permission_preset` must reference a known permission preset
- `handoff_contract` must reference a known Handoff Contract

### 15.4 Handoff Contract

```yaml
handoff_contract:
  id: str
  from_roles: [str]                 # which roles may originate this handoff
  allowed_next_roles: [str]         # which roles may receive this handoff
  required_fields: [str]            # fields that must be present in the handoff document
  validation_rules:
    - field: str
      required: bool
      min_length: int               # (optional)
      max_length: int               # (optional)
      enum: [str]                   # (optional) if set, value must be in this list
      min_items: int                # (optional) if field is a list
      regex: str                    # (optional) pattern to match
  completion_gate:
    required: [str]
```

Validation rules:
- Every entry in `from_roles` and `allowed_next_roles` must reference a known role contract
- `from_roles` and `allowed_next_roles` must not overlap (no self-handoffs without explicit intent)
- `required_fields` must be a subset of fields that have a `required: true` validation rule
- `validation_rules` must not conflict (e.g., `enum` and `regex` on the same field)
- `completion_gate.required` lists the conditions checked after handoff delivery

### 15.5 Team Proposal Schema

When the Planner or an AI onboarding agent creates a team, its output schema:

```yaml
team_proposal:
  goal: str
  recommended_team_id: str          # must match a known Team Contract
  rationale: str
  customizations:
    agents: [str]                   # optional subset of role_inventory
    permission_overrides:           # optional role_id → preset_id
      role_id: preset_id
    handoff_overrides:              # optional contract_id → new contract_id
      contract_id: new_contract_id
```

Proposal is rejected if:
- `recommended_team_id` does not match a known Team Contract
- Any role in `customizations.agents` is not in the Team Contract's `role_inventory`
- Any `permission_overrides` references an unknown preset
- Any `handoff_overrides` references an unknown contract

### 15.6 Test Categories

All tests use mocked inputs. No real AI API calls, Docker execution, or Hermes agent execution.

| Category | Scope |
|----------|-------|
| Contract Schema Tests | Each contract validates against its Pydantic schema |
| Cross-Reference Tests | All role/handoff/preset references between contracts resolve |
| Safety Invariant Tests | Hard rules that can never be violated under any valid configuration |
| Deterministic Allocation Tests | Same input → identical output across multiple runs |
| Handoff Validation Tests | Handoff contracts enforce their validation rules at runtime |

---

