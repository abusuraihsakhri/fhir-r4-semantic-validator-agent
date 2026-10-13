"""Conservative, dependency-free FHIR R4 JSON checks.

This is NOT full HL7 FHIR profile or terminology conformance validation.
For that use the official HL7 validator with appropriate IG packages.
"""
import re
from typing import Any

_ID = re.compile(r"^[A-Za-z0-9.\-]{1,64}$")
_TYPE = re.compile(r"^[A-Z][A-Za-z0-9]{0,254}$")
_REFERENCE = re.compile(r"^[A-Z][A-Za-z0-9]+/[A-Za-z0-9.\-]{1,64}$")
_BUNDLE_TYPES = {
    "document", "message", "transaction", "transaction-response",
    "batch", "batch-response", "history", "searchset", "collection",
}
_REQUIRED = {
    "Observation": ("status", "code"),
    "DiagnosticReport": ("status", "code"),
    "Encounter": ("status", "class"),
    "MedicationRequest": ("status", "intent", "subject"),
}
_MAX_ENTRIES = 2000
_MAX_NODES = 10000
_MAX_ISSUES = 200


def validate_fhir(resource: Any) -> dict:
    """Return an issue summary and FHIR R4 OperationOutcome; never echo input values."""
    issues = []
    checked = 0

    def add(severity: str, code: str, message: str, path: str) -> None:
        if len(issues) < _MAX_ISSUES:
            issues.append({
                "severity": severity,
                "code": code,
                "details": {"text": message},
                "expression": [path],
            })

    def validate_resource(obj: Any, path: str) -> bool:
        nonlocal checked
        if not isinstance(obj, dict):
            add("error", "structure", "Resource must be a JSON object.", path)
            return False
        kind = obj.get("resourceType")
        if not isinstance(kind, str) or not _TYPE.fullmatch(kind):
            add("error", "required", "A valid resourceType is required.", path + ".resourceType")
            return False
        checked += 1
        identifier = obj.get("id")
        if identifier is not None and (not isinstance(identifier, str) or not _ID.fullmatch(identifier)):
            add("error", "invalid", "Resource id must use 1–64 allowed characters.", path + ".id")
        for field in _REQUIRED.get(kind, ()):
            if field not in obj or obj[field] is None:
                add("error", "required", f"{kind}.{field} is required in base FHIR R4.", path + "." + field)
        if kind == "MedicationRequest" and not any(k in obj for k in ("medicationCodeableConcept", "medicationReference")):
            add("error", "required", "MedicationRequest.medication[x] is required.", path + ".medication[x]")
        contained = obj.get("contained", [])
        if not isinstance(contained, list):
            add("error", "structure", "contained must be an array.", path + ".contained")
        else:
            seen = set()
            for i, item in enumerate(contained[:_MAX_ENTRIES]):
                child_path = f"{path}.contained[{i}]"
                if validate_resource(item, child_path) and isinstance(item, dict):
                    identifier = item.get("id")
                    if not identifier:
                        add("error", "required", "Contained resources need an id.", child_path + ".id")
                    elif identifier in seen:
                        add("error", "duplicate", "Duplicate contained resource id.", child_path + ".id")
                    seen.add(identifier)
        return True

    if not validate_resource(resource, "resource"):
        return _result(issues, checked)

    kind = resource["resourceType"]
    entries = []
    full_urls = set()
    internal_targets = set()
    if kind == "Bundle":
        if resource.get("type") not in _BUNDLE_TYPES:
            add("error", "required", "Bundle.type must be a FHIR R4 bundle type.", "resource.type")
        entries = resource.get("entry", [])
        if not isinstance(entries, list):
            add("error", "structure", "Bundle.entry must be an array.", "resource.entry")
            entries = []
        if len(entries) > _MAX_ENTRIES:
            add("error", "too-costly", f"Bundles are limited to {_MAX_ENTRIES} entries.", "resource.entry")
            entries = entries[:_MAX_ENTRIES]
        for i, entry in enumerate(entries):
            path = f"resource.entry[{i}]"
            if not isinstance(entry, dict):
                add("error", "structure", "Bundle entry must be an object.", path)
                continue
            url = entry.get("fullUrl")
            if url is not None:
                if not isinstance(url, str) or not url.strip():
                    add("error", "invalid", "fullUrl must be a non-empty string.", path + ".fullUrl")
                else:
                    if url in full_urls and resource.get("type") != "history":
                        add("error", "duplicate", "Duplicate Bundle.entry.fullUrl.", path + ".fullUrl")
                    full_urls.add(url)
                    internal_targets.add(url)
            item = entry.get("resource")
            if item is not None:
                if validate_resource(item, path + ".resource") and isinstance(item.get("id"), str):
                    internal_targets.add(item["resourceType"] + "/" + item["id"])
            if resource.get("type") in {"batch", "transaction"}:
                req = entry.get("request")
                if not isinstance(req, dict) or not all(isinstance(req.get(x), str) and req[x] for x in ("method", "url")):
                    add("error", "required", "Batch and transaction entries need request.method and request.url.", path + ".request")
        if resource.get("type") == "document" and entries:
            first = entries[0]
            if not isinstance(first, dict) or not isinstance(first.get("resource"), dict) or first["resource"].get("resourceType") != "Composition":
                add("error", "structure", "A document Bundle must start with Composition.", "resource.entry[0].resource")
        if resource.get("type") == "message" and entries:
            first = entries[0]
            if not isinstance(first, dict) or not isinstance(first.get("resource"), dict) or first["resource"].get("resourceType") != "MessageHeader":
                add("error", "structure", "A message Bundle must start with MessageHeader.", "resource.entry[0].resource")

    # Check only internal/contained references; external absolute references
    # and relative references outside this Bundle can be resolved by a server.
    targets = [("resource", resource)]
    for i, entry in enumerate(entries):
        if isinstance(entry, dict) and isinstance(entry.get("resource"), dict):
            targets.append((f"resource.entry[{i}].resource", entry["resource"]))
    visited_nodes = 0
    for root_path, owner in targets:
        ids = {r.get("id") for r in owner.get("contained", []) if isinstance(r, dict)} if isinstance(owner.get("contained", []), list) else set()
        stack = [(root_path, owner)]
        while stack:
            path, node = stack.pop()
            visited_nodes += 1
            if visited_nodes > _MAX_NODES:
                add("error", "too-costly", "Maximum structure traversal limit reached.", path)
                stack.clear()
                break
            if isinstance(node, dict):
                for key, value in node.items():
                    child = path + "." + key
                    if key == "reference" and isinstance(value, str):
                        if value.startswith("#") and value[1:] not in ids:
                            add("error", "not-found", "Unresolved contained reference.", child)
                        elif value.startswith("urn:uuid:") and kind == "Bundle" and value not in internal_targets:
                            add("error", "not-found", "Unresolved in-bundle UUID reference.", child)
                        elif kind == "Bundle" and _REFERENCE.fullmatch(value) and value not in internal_targets:
                            add("warning", "not-found", "Relative reference not present in this Bundle; may resolve externally.", child)
                    elif isinstance(value, (dict, list)):
                        stack.append((child, value))
            elif isinstance(node, list):
                for i, child in enumerate(node):
                    if isinstance(child, (dict, list)):
                        stack.append((f"{path}[{i}]", child))

    return _result(issues, checked)


def _result(issues: list, checked: int) -> dict:
    return {
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "resources_checked": checked,
        "issue_count": len(issues),
        "operationOutcome": {"resourceType": "OperationOutcome", "issue": issues},
    }
