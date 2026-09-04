"""
Automated Pytest Test Suite for Fhir R4 Semantic Validator Agent.
Domain: Clinical & Biomedical AI
Standard: CAP / CLSI / ISO Standards
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, AuditTrail, validate_safe_path, PathTraversalException
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_phi_guard_edge_cases():
    # Empty string should pass
    PHIGuard.assert_no_phi("")

    # SSN pattern detection
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("SSN 123-45-6789 submitted")

    # Phone number detection
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Call patient at 555-123-4567")

    # Email detection
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Email: patient@example.com")

    # Redaction works
    redacted = PHIGuard.redact_phi("Patient MRN-1234567 has SSN 123-45-6789")
    assert "1234567" not in redacted
    assert "123-45-6789" not in redacted
    assert "[REDACTED_IDENTIFIER]" in redacted


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_audit_trail_signature_verification():
    """Verify that the audit trail detects tampered entries."""
    trail = AuditTrail(secret_key="test-key-for-verification")
    trail.log("test-actor", "test-tier", "TEST_EVENT", {"data": "value1"})
    trail.log("test-actor", "test-tier", "TEST_EVENT", {"data": "value2"})

    # Fresh trail should verify
    assert trail.verify_integrity() is True

    # Tamper with a payload hash — should fail verification
    trail.logs[0]["payload_hash"] = "tampered_hash_value"
    assert trail.verify_integrity() is False


def test_validate_safe_path():
    """Verify path traversal protection."""
    import os
    cwd = os.getcwd()

    # Safe path within cwd
    safe = validate_safe_path("sample.csv", allowed_base=cwd)
    assert safe.endswith("sample.csv")

    # Path traversal should raise
    with pytest.raises(PathTraversalException):
        validate_safe_path("../../etc/passwd", allowed_base=cwd)

    # Absolute path outside cwd should raise
    with pytest.raises(PathTraversalException):
        validate_safe_path("/etc/passwd", allowed_base=cwd)


def test_phi_via_supervisor_blocks_outbound():
    """Verify that supervisor rejects PHI-laden task IDs."""
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="Patient MRN-123456 critical",
        target_identifier="KEY-01",
        primary_metric=10.0,
    )
    with pytest.raises(SecurityException):
        supervisor.process_task(payload)
