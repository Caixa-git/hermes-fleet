"""Tests: Handoff contract runtime validation.

Pure data tests -- no file I/O, no Docker.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from hermes_fleet.contracts import (
    HandoffContract,
    HandoffValidationRule,
    validate_handoff_doc,
)


# ── HandoffContract Schema ────────────────────────────────────────────


class TestHandoffContractSchema:
    def test_minimal_valid(self):
        contract = HandoffContract(id="dev-to-review")
        assert contract.id == "dev-to-review"
        assert contract.from_roles == []
        assert contract.allowed_next_roles == []
        assert contract.required_fields == []

    def test_full_valid(self):
        contract = HandoffContract(
            id="dev-to-review",
            name="Dev to Review",
            description="Handoff from developer to reviewer",
            from_roles=["frontend-developer", "backend-developer"],
            allowed_next_roles=["code-reviewer"],
            required_fields=["summary", "files", "tests_passed"],
            validation_rules=[
                HandoffValidationRule(field="summary", required=True, min_length=10),
                HandoffValidationRule(field="priority", enum=["low", "medium", "high"]),
            ],
        )
        assert contract.from_roles == ["frontend-developer", "backend-developer"]
        assert len(contract.validation_rules) == 2

    def test_id_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            HandoffContract(id="")

    def test_id_whitespace_only_rejected(self):
        with pytest.raises(ValidationError):
            HandoffContract(id="   ")


# ── validate_handoff_doc ─────────────────────────────────────────────


class TestValidateHandoffDoc:
    @pytest.fixture
    def sample_contract(self) -> HandoffContract:
        return HandoffContract(
            id="dev-to-review",
            from_roles=["frontend-developer", "backend-developer"],
            allowed_next_roles=["code-reviewer"],
            required_fields=["summary", "files"],
            validation_rules=[
                HandoffValidationRule(field="summary", required=True, min_length=5),
                HandoffValidationRule(field="priority", enum=["low", "medium", "high"]),
            ],
        )

    def test_passes_valid_handoff(self, sample_contract):
        doc = {
            "summary": "Implemented login feature",
            "files": ["login.py", "auth.py"],
            "priority": "medium",
        }
        result = validate_handoff_doc(doc, sample_contract, "frontend-developer", "code-reviewer")
        assert result["passed"] is True
        assert all(c["status"] == "passed" for c in result["checks"])

    def test_fails_wrong_from_agent(self, sample_contract):
        doc = {"summary": "x", "files": ["x.py"]}
        result = validate_handoff_doc(doc, sample_contract, "qa-tester", "code-reviewer")
        assert result["passed"] is False
        # Find the from_roles check
        from_check = [c for c in result["checks"] if "from_roles" in c["check"]][0]
        assert from_check["status"] == "failed"
        assert "not in contract's from_roles" in from_check["message"]

    def test_fails_wrong_to_agent(self, sample_contract):
        doc = {"summary": "x", "files": ["x.py"]}
        result = validate_handoff_doc(doc, sample_contract, "frontend-developer", "qa-tester")
        assert result["passed"] is False
        to_check = [c for c in result["checks"] if "allowed_next_roles" in c["check"]][0]
        assert to_check["status"] == "failed"
        assert "not in contract's allowed_next_roles" in to_check["message"]

    def test_fails_missing_required_field(self, sample_contract):
        doc = {"summary": "Implemented login"}  # missing "files"
        result = validate_handoff_doc(doc, sample_contract, "frontend-developer", "code-reviewer")
        assert result["passed"] is False
        req_check = [c for c in result["checks"] if "required_field:files" in c["check"]][0]
        assert req_check["status"] == "failed"
        assert "missing or empty" in req_check["message"]

    def test_fails_validation_rule_min_length(self, sample_contract):
        doc = {
            "summary": "ok",  # min_length is 5
            "files": ["x.py"],
            "priority": "high",
        }
        result = validate_handoff_doc(doc, sample_contract, "frontend-developer", "code-reviewer")
        assert result["passed"] is False
        rule_check = [c for c in result["checks"] if "rule:summary" in c["check"]][0]
        assert rule_check["status"] == "failed"
        assert "min length" in rule_check["message"]

    def test_fails_validation_rule_enum(self, sample_contract):
        doc = {
            "summary": "Implemented login feature",
            "files": ["x.py"],
            "priority": "urgent",  # not in enum
        }
        result = validate_handoff_doc(doc, sample_contract, "frontend-developer", "code-reviewer")
        assert result["passed"] is False
        enum_check = [c for c in result["checks"] if "rule:priority" in c["check"]][0]
        assert enum_check["status"] == "failed"
        assert "must be one of" in enum_check["message"]

    def test_handoff_with_no_contract_restrictions(self):
        """Empty from_roles/allowed_next_roles means no role restrictions."""
        contract = HandoffContract(
            id="generic",
            required_fields=["note"],
        )
        doc = {"note": "hello"}
        result = validate_handoff_doc(doc, contract, "any-agent", "any-agent")
        assert result["passed"] is True

    def test_handoff_with_only_rules(self):
        contract = HandoffContract(
            id="strict",
            validation_rules=[
                HandoffValidationRule(field="version", min_length=3, max_length=10),
                HandoffValidationRule(field="count", min_items=1),
            ],
        )
        doc = {"version": "v1.0", "count": [1, 2, 3]}
        result = validate_handoff_doc(doc, contract, "dev", "reviewer")
        assert result["passed"] is True

    def test_rule_regex_match(self):
        contract = HandoffContract(
            id="semver",
            validation_rules=[
                HandoffValidationRule(field="version", regex=r"^v?\d+\.\d+\.\d+$"),
            ],
        )
        doc = {"version": "v1.2.3"}
        result = validate_handoff_doc(doc, contract, "dev", "reviewer")
        assert result["passed"] is True

    def test_rule_regex_mismatch(self):
        contract = HandoffContract(
            id="semver",
            validation_rules=[
                HandoffValidationRule(field="version", regex=r"^v?\d+\.\d+\.\d+$"),
            ],
        )
        doc = {"version": "not-a-version"}
        result = validate_handoff_doc(doc, contract, "dev", "reviewer")
        assert result["passed"] is False

    def test_empty_doc_with_required_fields(self):
        contract = HandoffContract(
            id="strict",
            required_fields=["must_exist"],
        )
        result = validate_handoff_doc({}, contract, "dev", "reviewer")
        assert result["passed"] is False

    def test_multiple_failures_reported(self):
        contract = HandoffContract(
            id="hard",
            from_roles=["alpha"],
            allowed_next_roles=["beta"],
            required_fields=["x", "y"],
        )
        doc = {}
        result = validate_handoff_doc(doc, contract, "wrong", "wrong")
        assert result["passed"] is False
        assert len(result["checks"]) >= 4  # from_roles + allowed_next_roles + x + y

    def test_none_values_in_doc_treated_as_missing(self):
        contract = HandoffContract(
            id="check",
            required_fields=["title"],
        )
        doc = {"title": None}
        result = validate_handoff_doc(doc, contract, "dev", "reviewer")
        assert result["passed"] is False

    def test_empty_string_in_doc_treated_as_missing(self):
        contract = HandoffContract(
            id="check",
            required_fields=["title"],
        )
        doc = {"title": ""}
        result = validate_handoff_doc(doc, contract, "dev", "reviewer")
        assert result["passed"] is False
