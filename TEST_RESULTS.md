# Test Results — Hermes Fleet v0.1

Tests run: 2026-05-03

---

## Full Test Suite

```bash
$ python -m pytest tests/ -q
........................................................................ [ 94%]
....                                                                     [100%]
76 passed in 1.29s
```

**Result: 76 passed, 0 failed**

---

## Smoke Tests

### CLI Help
```
$ hermes-fleet --help
Usage: hermes-fleet [OPTIONS] COMMAND [ARGS]...

A secure team bootstrapper for isolated Hermes Agent fleets.

Commands:
  init            Initialize Hermes Fleet in a project directory
  plan            Analyze a goal and recommend a team
  generate        Generate all agent configuration files
  test            Run validation checks against generated configurations
```

### General Dev Team (end-to-end)

```bash
$ cd examples/general-dev

$ hermes-fleet init
✓ Initialized Hermes Fleet in /workspace/hermes-fleet/examples/general-dev

$ hermes-fleet plan "Refactor a Python project" --show-details
Recommended team: general-dev
  (5 agents displayed)

$ hermes-fleet generate --force
  [write] .fleet/generated/agents/orchestrator/SOUL.md
  [write] .fleet/generated/agents/orchestrator/policy.yaml
  ... (14 files total)

$ hermes-fleet test safe-defaults --verbose
Safe-defaults validation results:
  Passed: 20
  Failed: 0
  Skipped: 1
All safe-defaults checks PASSED.
```

### SaaS Medium Team (end-to-end)

```bash
$ cd examples/saas-medium

$ hermes-fleet init
✓ Initialized Hermes Fleet in /workspace/hermes-fleet/examples/saas-medium

$ hermes-fleet plan "Build a SaaS MVP with billing"
Recommended team: saas-medium
  (9 agents displayed)

$ hermes-fleet generate --force
  [write] .fleet/generated/agents/orchestrator/SOUL.md
  ... (27 files total)

$ hermes-fleet test safe-defaults --verbose
Safe-defaults validation results:
  Passed: 20
  Failed: 0
  Skipped: 1
All safe-defaults checks PASSED.
```

---

## Test Categories

| Category | Test File | Count |
|----------|-----------|-------|
| Team presets | `test_team_presets.py` | 6 |
| SOUL.md generation | `test_soul_generation.py` | 11 |
| Policy generation | `test_policy_generation.py` | 10 |
| Docker Compose security | `test_docker_compose_generation.py` | 13 |
| Safe-defaults validator | `test_safe_defaults.py` | 8 |
| Kanban templates | `test_kanban_templates.py` | 7 |
| Planner heuristics | `test_planner.py` | 8 |
| End-to-end integration | `test_end_to_end.py` | 7 |
| **Total** | | **76** |

---

## Patch Verification

On 2026-05-03, the following patches were applied (no code changes before user approval):

| Issue | Status | Detail |
|-------|--------|--------|
| M1 | Done | templates/ dir deleted; jinja2 removed from pyproject.toml; ARCHITECTURE.md and SPEC.md updated |
| L1 | Done | `test_default_output_is_not_verbose` now properly asserts no passing results leak in non-verbose mode |
| L2 | Done | Unused imports removed from safe_defaults.py (`re`), docker_compose.py (`Any`), cli.py (`os`, `sys`) |
| L3 | Done | `cli.py:_load_role()` delegates to `teams.load_role()` instead of duplicating file I/O |
| L5 | Noted | `no_real_secrets_in_output` strengthened (secrets directory check); policy.yaml scanning already covered by `no_production_secrets_injected` |
| L6 | Done | SPEC.md shows Python 3.10+ (matches pyproject.toml); classifier added for Python 3.10 |
| L4 | Deferred | `plan --apply` — deferred to v0.2 |
| C1 | Deferred | Compose `version:` field — deferred to v0.2 |
| C2 | Deferred | Placeholder image — deferred to v0.2 |
| C3 | Won't fix | `print()` in _write_if_not_exists is deliberate CLI feedback |

All patches are within v0.1 scope. No changes touch ~/.hermes, existing Hermes profiles, or hermes-agent/venv.
