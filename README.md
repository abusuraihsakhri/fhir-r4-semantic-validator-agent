# FHIR R4 Semantic Validator Agent

A local FHIR R4 JSON checker with a browser interface and Python CLI/API.
The repository also preserves its earlier **metric-based supervisor**, which is separate
from FHIR validation and is **not** a FHIR conformance engine.

## What it checks

- Valid-looking resourceType and FHIR resource id syntax
- Required base fields for Observation, DiagnosticReport, Encounter, and MedicationRequest
- Bundle type, entry structure, selected document/message and transaction constraints
- Duplicate Bundle entry fullUrl, contained ids, and local UUID references
- Missing relative references as **warnings** (they may resolve on another server)
- FHIR-format OperationOutcome diagnostics and a JSON report download

**Limits:** These are *partial* structural and reference checks, not exhaustive R4 validation.
This tool does **not** validate US Core 6.1, arbitrary StructureDefinition profiles,
FHIRPath invariants, cardinality throughout the specification, ValueSet bindings, LOINC,
SNOMED CT, RxNorm, or terminology-service expansions. A pass is **not proof of compliance**.
For conformance validation use the [HL7 FHIR Validator](https://github.com/hapifhir/org.hl7.fhir.core)
with the required R4 and implementation-guide packages.

## Browser use

Open `web/index.html`, paste JSON or load a .json file (up to 5 MiB), and select
**Validate locally**. Review findings, then download the OperationOutcome report.
This runs entirely in the browser with JavaScript; no Python runtime, account, server,
or external API is needed. The same static files can be hosted on GitHub Pages.
A Pages deployment workflow is included, but a live URL should only be advertised
after deployment and functional verification.

## Python installation

Requires Python 3.10+.

```bash
python -m pip install -e '.[api,test]'
python -m pytest -q
```

For minimal CLI installation: `python -m pip install -e .`.

## CLI

```bash
# JSON file must be inside the current working directory (max 5 MiB)
fhir-validator validate-fhir -i sample_fhir_bundle.json

# Legacy metric-based evaluation, retained for compatibility
fhir-validator audit --task-id TASK-001 --target KEY-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
fhir-validator batch -i sample.csv -o results.csv
fhir-validator verify-audit
```

The `validate-fhir` command prints JSON. Exit status is 0 when there are no
reported errors and 2 when structural errors were found. Its output uses
`operationOutcome.issue` with a `valid` boolean; warnings do not invalidate the result.

## REST API

```bash
fhir-validator serve --host 127.0.0.1 --port 8000
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/fhir/validate \
  -H 'Content-Type: application/json' \
  --data '{"resourceType":"Patient","id":"example"}'
```

The legacy `POST /api/audit`, `POST /api/chat`, `GET /metrics`, and
`GET /api/audit/logs` endpoints remain available. They perform metric-based
checks; they do **not** validate FHIR Bundles. Interactive API documentation is at
`http://127.0.0.1:8000/docs`.

## Privacy and security

Browser validation is local; no data is transmitted by the browser checker.
The Python server has **no authentication** and must not be exposed to untrusted
networks or fed identifiable patient data without additional access controls
and a deployment-specific privacy/security review. The legacy PHI-pattern guard
is a heuristic, **not** a guarantee of de-identification or HIPAA compliance.

The HMAC audit chain is in-memory; if `AUDIT_SECRET_KEY` is unset it uses
an ephemeral key. Neither the audit chain nor its key persist across restarts
automatically. Never place audit keys or patient data in public web assets.

## Technology and development

Python 3.10+, Pydantic 2, FastAPI/Uvicorn (optional API dependencies), pytest,
HTML/CSS/vanilla JavaScript. The static browser checker runs in current
evergreen Chrome, Firefox, Safari, and Edge with File API support.
GitHub Actions tests Python 3.10–3.13 and checks browser JavaScript syntax.

To run the container locally:

```bash
docker compose up --build
```

The Compose binding is loopback-only at `127.0.0.1:8000`.

## License

MIT — see [LICENSE](LICENSE).
