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
    errors_found = 0

    def add(severity: str, code: str, message: str, path: str) -> None:
        nonlocal errors_found
        if severity == "error":
            errors_found += 1
        if len(issues) < _MAX_ISSUES:
            issues.append({
                "severity": severity,
                "code": code,
                "details": {"text": message},
                "expression": [path],
            })

    def validate_resource(obj: Any, path: str, depth: int = 0) -> bool:
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
        elif depth > 0 and contained:
            add("error", "structure", "Nested contained resources are not supported.", path + ".contained")
        else:
            seen = set()
            for i, item in enumerate(contained[:_MAX_ENTRIES]):
                child_path = f"{path}.contained[{i}]"
                if validate_resource(item, child_path, depth + 1) and isinstance(item, dict):
                    identifier = item.get("id")
                    if not identifier:
                        add("error", "required", "Contained resources need an id.", child_path + ".id")
                    elif isinstance(identifier, str):
                        if identifier in seen:
                            add("error", "duplicate", "Duplicate contained resource id.", child_path + ".id")
                        seen.add(identifier)
        return True

    if not validate_resource(resource, "resource"):
        return _result(issues, checked, errors_found)

    kind = resource["resourceType"]
    entries = []
    full_versions = set()
    internal_targets = set()
    if kind == "Bundle":
        if not isinstance(resource.get("type"), str) or resource["type"] not in _BUNDLE_TYPES:
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
                    version = ""
                    item_meta = entry.get("resource", {})
                    if isinstance(item_meta, dict) and isinstance(item_meta.get("meta"), dict):
                        v = item_meta["meta"].get("versionId")
                        version = v if isinstance(v, str) else ""
                    version_key = (url, version)
                    if version_key in full_versions and resource.get("type") != "history":
                        add("error", "duplicate", "Duplicate Bundle.entry.fullUrl and resource version.", path + ".fullUrl")
                    full_versions.add(version_key)
                    internal_targets.add(url)
                    if "/_history/" in url:
                        add("error", "invalid", "fullUrl cannot be version-specific.", path + ".fullUrl)
            item = entry.get("resource")
            if item is not None:
                if validate_resource(item, path + ".resource") and isinstance(item.get("id"), str):
                    internal_targets.add(item["resourceType"] + "/" + item["id"])
            bundle_type = resource.get("type")
            requires_request = bundle_type in ("batch", "transaction", "history")
            requires_response = bundle_type in ("batch-response", "transaction-response", "history")
            req = entry.get("request")
            response = entry.get("response")
            if requires_request:
                if not isinstance(req, dict) or not all(isinstance(req.get(x), str) and req[x] for x in ("method", "url")):
                    add("error", "required", "This Bundle type requires request.method and request.url.", path + ".request")
            elif req is not None:
                add("error", "structure", "request is not allowed for this Bundle type.", path + ".request")
            if requires_response and not isinstance(response, dict):
                add("error", "required", "This Bundle type requires entry.response.", path + ".response")
            elif not requires_response and response is not None:
                add("error", "structure", "response is not allowed for this Bundle type.", path + ".response")
            if entry.get("search") is not None and bundle_type != "searchset":
                add("error", "structure", "entry.search is only allowed in searchsets.", path + ".search")
            if item is None and req is None and response is None:
                add("error", "required", "Bundle entry needs a resource, request, or response.", path)
        if resource.get("total") is not None and resource.get("type") not in ("searchset", "history"):
            add("error", "structure", "Bundle.total is only permitted for search or history.", "resource.total")
        if resource.get("type") == "document":
            identifier = resource.get("identifier")
            if not isinstance(identifier, dict) or not identifier.get("system") or not identifier.get("value"):
                add("error", "required", "Document Bundle requires identifier.system and identifier.value.", "resource.identifier")
            if not resource.get("timestamp"):
                add("error", "required", "Document Bundle requires timestamp.", "resource.timestamp")
            if not entries:
                add("error", "required", "Document Bundle requires a first Composition entry.", "resource.entry")
        if resource.get("type") == "message" and not entries:
            add("error", "required", "Message Bundle requires a first MessageHeader entry.", "resource.entry")
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
        ids = {r["id"] for r in owner.get("contained", []) if isinstance(r, dict) and isinstance(r.get("id"), str)} if isinstance(owner.get("contained", []), list) else set()
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
                    if path == "resource" and kind == "Bundle" and key == "entry":
                        continue
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

    return _result(issues, checked, errors_found)


def _result(issues: list, checked: int, errors_found: int) -> dict:
    return {
        "valid": errors_found == 0,
        "resources_checked": checked,
        "issue_count": len(issues),
        "operationOutcome": {"resourceType": "OperationOutcome", "issue": issues or [{"severity": "information", "code": "informational", "details": {"text": "No issues detected by the limited checker."}}]},
    }


def parse_csv_boolean(value: Any) -> bool:
    """Strictly parse CSV booleans, rejecting ambiguous critical flags."""
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in ("true", "1", "yes", "y", "on"):
        return True
    if token in ("false", "0", "no", "n", "off", ""):
        return False
    raise ValueError("Expected a boolean value such as true/false or 1/0")
