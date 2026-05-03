"""
Kanban handoff contract template generation.
"""



def generate_kanban_templates() -> dict[str, str]:
    """
    Generate Kanban template dicts (task, handoff, completion gates).

    Returns a dict with keys: 'task-template', 'handoff-template', 'completion-gates'.
    """
    return {
        "task-template": _render_task_template(),
        "handoff-template": _render_handoff_template(),
        "completion-gates": _render_completion_gates(),
    }


def _render_task_template() -> str:
    """Render a task contract template as markdown."""
    required_outputs_str = "- [ ] summary\n- [ ] files_changed"

    return f"""# Task Contract

## Task ID
`TASK-001`

## Type
<!-- e.g., frontend_implementation, code_review, qa_testing, documentation -->

## Owner
<!-- Agent ID assigned to this task -->

## Goal
<!-- What needs to be accomplished -->

## Context
<!-- Links, references, required reading for this task -->

## Allowed Paths
<!-- Files/directories the agent may modify -->
-

## Forbidden Paths
<!-- Files/directories the agent must NOT modify -->
-

## Required Inputs
- [ ] Context gathered
- [ ] Dependencies available

## Required Outputs
{required_outputs_str}

## Next Agent
<!-- Who receives this work after completion -->

---

## Status
- [ ] Assigned
- [ ] In Progress
- [ ] Ready for Handoff
- [ ] Completed
"""


def _render_handoff_template() -> str:
    """Render a handoff note template as markdown."""
    return """# Handoff Note

## What I Did
<!-- Summary of work completed -->

## Files Changed
<!-- List all files created or modified -->
- 

## Decisions Made
<!-- Key design or implementation decisions -->

## Assumptions
<!-- What assumptions were made that the next agent should know -->

## Tests Run
<!-- What tests were executed and their results -->
- [ ] All tests passed
- [ ] Some tests failed (see below)

## Known Risks
<!-- Security concerns, edge cases, incomplete work -->
- 

## Blockers
<!-- What prevented full completion -->
- None

---

## 🧠 Context Handoff (optional)

> This section is not validated. It exists to carry context that doesn't
> fit structured fields. Filling it builds trust; skipping it doesn't
> block completion.

### Decisions Considered
<!-- Key choices and why this path was taken -->

### Open Questions
<!-- Unresolved issues the receiver should know about -->

### Confidence Signals
<!-- What feels solid, and what feels uncertain -->

---

## Recommended Next Agent
<!-- Who should take this work next -->
- 

---

## Handoff Checklist
- [ ] Required outputs are complete
- [ ] Context is documented
- [ ] No role drift (stayed within allowed work)
- [ ] Forbidden paths were not modified
"""


def _render_completion_gates() -> str:
    """Render a completion gates template as YAML."""
    return """# Completion Gates
# These conditions must be met before a task is considered complete

gates:
  task_scope:
    - name: task_goal_achieved
      description: The original task goal has been met
      required: true
    - name: no_scope_creep
      description: Work did not extend beyond the task scope
      required: true

  quality:
    - name: tests_passed
      description: All relevant tests pass
      required: true
    - name: no_regressions
      description: No existing functionality was broken
      required: false

  handoff:
    - name: handoff_note_provided
      description: A complete handoff note was written
      required: true
    - name: next_agent_identified
      description: The next responsible agent is specified
      required: true

  security:
    - name: no_secrets_exposed
      description: No secrets or credentials were exposed
      required: true
    - name: forbidden_paths_not_touched
      description: No files outside allowed paths were modified
      required: true

  identity:
    - name: stayed_in_role
      description: The agent did not perform work outside its role
      required: true
    - name: no_role_drift
      description: The agent's final state matches its assigned role
      required: true
"""
