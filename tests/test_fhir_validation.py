"""Regressions for conservative FHIR R4 checks and the existing API."""
import pytest

from fhir_validation import validate_fhir


def codes(result, severity=None):
    return [i["code"] for i in result["operationOutcome"]["issue"]
            if severity is None or i["severity"] == severity]


def test_patient_base_resource():
    result = validate_fhir({"resourceType": "Patient", "id": "patient-1"})
    assert result["valid"]
    assert result["resources_checked"] == 1
    assert result["operationOutcome"]["resourceType"] == "OperationOutcome"


@pytest.mark.parametrize("bad", [None, [], "Patient", {}, {"resourceType": 42},
                                  {"resourceType": "Patient", "id": "bad id"}])
def test_invalid_resource(bad):
    outcome = validate_fhir(bad)
    assert not outcome["valid"]
    assert "error" in [i["severity"] for i in outcome["operationOutcome"]["issue"]]


def test_malformed_bundle_type_and_contained_id():
    assert not validate_fhir({"resourceType": "Bundle", "type": []})["valid"]
    assert not validate_fhir({"resourceType": "Patient", "contained": [{"resourceType": "Patient", "id": []}]})["valid"]


def test_missing_required_observation_elements():
    outcome = validate_fhir({"resourceType": "Observation", "id": "o1"})
    assert not outcome["valid"]
    assert codes(outcome, "error").count("required") == 2


def test_resolved_bundle_references():
    bundle = {
        "resourceType": "Bundle", "type": "collection",
        "entry": [
            {"fullUrl": "urn:uuid:patient1", "resource": {"resourceType": "Patient", "id": "p1"}},
            {"fullUrl": "urn:uuid:obs1", "resource": {
                "resourceType": "Observation", "id": "o1", "status": "final",
                "code": {"text": "Synthetic example"}, "subject": {"reference": "Patient/p1"},
            }},
        ],
    }
    result = validate_fhir(bundle)
    assert result["valid"], result
    assert result["resources_checked"] == 3
    assert not codes(result, "error")
    assert not codes(result, "warning")


def test_unresolved_uuid_and_duplicate_fullurl():
    bundle = {
        "resourceType": "Bundle", "type": "collection",
        "entry": [
            {"fullUrl": "urn:uuid:a", "resource": {
                "resourceType": "Patient", "id": "one",
                "managingOrganization": {"reference": "urn:uuid:missing"},
            }},
            {"fullUrl": "urn:uuid:a", "resource": {"resourceType": "Patient", "id": "two"}},
        ],
    }
    result = validate_fhir(bundle)
    assert not result["valid"]
    assert "duplicate" in codes(result)
    assert "not-found" in codes(result)


def test_relative_external_reference_is_warning():
    outcome = validate_fhir({"resourceType": "Bundle", "type": "collection", "entry": [
        {"resource": {"resourceType": "Observation", "status": "final",
                      "code": {"text": "Example"}, "subject": {"reference": "Patient/external"}}},
    ]})
    assert outcome["valid"]
    assert codes(outcome, "warning") == ["not-found"]


def test_contained_reference():
    resource = {
        "resourceType": "Observation", "status": "final", "code": {"text": "example"},
        "contained": [{"resourceType": "Patient", "id": "subject"}],
        "subject": {"reference": "#subject"},
    }
    assert validate_fhir(resource)["valid"]
    resource["subject"]["reference"] = "#missing"
    assert not validate_fhir(resource)["valid"]


def test_bundle_structure_and_transaction_request():
    outcome = validate_fhir({"resourceType": "Bundle", "type": "transaction",
                             "entry": [{"resource": {"resourceType": "Patient"}}]})
    assert not outcome["valid"]
    assert "required" in codes(outcome)


def test_diagnostics_do_not_echo_patient_information():
    secret = "Patient Jane Smith"
    outcome = validate_fhir({"resourceType": "Patient", "id": secret})
    assert not outcome["valid"]
    assert secret not in str(outcome)


def test_api_fhir_validation():
    from fastapi.testclient import TestClient
    from agents.api import app
    client = TestClient(app)
    valid = client.post("/api/fhir/validate", json={"resourceType": "Patient", "id": "p1"})
    assert valid.status_code == 200
    assert valid.json()["valid"]
    invalid = client.post("/api/fhir/validate", json={"resourceType": "Observation"})
    assert invalid.status_code == 200
    assert not invalid.json()["valid"]
