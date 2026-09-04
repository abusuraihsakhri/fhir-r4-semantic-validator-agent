# FHIR R4 Semantic Validator Agent

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**FHIR R4 Semantic Validator Agent** is an advanced analytical and computational platform implementing US Core 6.1 & International FHIR R4 Bundle Profile Conformance. It provides a multi-agent evaluation engine that processes task payloads through specialized workers to produce consensus dossiers with cryptographic audit trails.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`Severity`** — dedicated module for severity evaluation and state verification.
- **`DomainKnowledgeRegistry`**: Enterprise domain rules, guideline matrices, and evidence benchmarks.
- **`AgentAlert`** — dedicated module for agent alert evaluation and state verification.
- **`ResourceStructureValidatorAgent`**: Specialized Sub-Agent 1 for primary metric & baseline quality auditing.
- **`TerminologyBindingAuditorAgent`**: Specialized Sub-Agent 2 for STAT kinetics & closed-loop escalation auditing.
- **`ReferentialIntegrityAgent`**: Specialized Sub-Agent 3 for biomarker & concordance triage.

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/fhir-r4-semantic-validator-agent.git
cd fhir-r4-semantic-validator-agent

# Install dependencies
pip install fastapi uvicorn pydantic pytest
```

### Environment Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` to set your `AUDIT_SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`).

---

## 💻 CLI Quickstart & Usage

### 1. Single Task Evaluation
```bash
python cli.py audit --task-id TASK-001 --target KEY-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 2. System Configuration Query
```bash
python cli.py chat "What is the system status?"
```

### 3. Batch CSV Processing
```bash
python cli.py batch -i sample.csv -o results.csv
```

### 4. Verify Audit Trail Integrity
```bash
python cli.py verify-audit
```

### 5. Launch REST API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### CLI Parameter Reference

| Command | Parameter | Description |
|:--------|:----------|:------------|
| `audit` | `--task-id` | Unique task / case identifier |
| `audit` | `--target` | Entity, patient key, or target identifier |
| `audit` | `--primary` | Primary measurement or score (float) |
| `audit` | `--secondary` | Secondary kinetic or confidence score (float) |
| `audit` | `--critical` | Emergency escalation flag |
| `audit` | `--status` | Status code or phenotype descriptor |
| `batch` | `-i, --input` | Input CSV file path |
| `batch` | `-o, --output` | Output CSV file path |
| `chat` | `query` | Natural language query (space-separated) |
| `serve` | `--host` | Server bind address |
| `serve` | `--port` | Server port |

### Input Data Schema (Batch CSV)

| Field | Description | Requirement |
|:------|:------------|:------------|
| `task_id` | Unique task identifier | Required |
| `target_identifier` | Entity or patient key | Required |
| `primary_metric` | Primary measurement | Required |
| `secondary_metric` | Secondary measurement | Optional |
| `is_critical_flag` | Emergency escalation flag | Optional |
| `status_descriptor` | Status code or phenotype | Optional |

---

## 🌐 REST API Endpoints

When the server is running (`python cli.py serve`), the following endpoints are available:

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/health` | Health and metadata check |
| `GET` | `/metrics` | Operational metrics |
| `POST` | `/api/audit` | Submit task payload for evaluation |
| `POST` | `/api/chat` | Air-gapped supervisory conversational assistant |
| `GET` | `/api/audit/logs` | Retrieve and verify HMAC audit trail |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition. Full signature verification on integrity checks.
* **Path Traversal Protection:** All batch file I/O is validated to prevent directory traversal attacks.
* **Secure Defaults:** Audit signing key is never hardcoded; ephemeral key generated if `AUDIT_SECRET_KEY` is not set.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

```bash
docker build -t fhir-r4-semantic-validator-agent .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=<your-secret-key> fhir-r4-semantic-validator-agent
```

Or using Docker Compose:

```bash
# Set your audit key in .env or environment
export AUDIT_SECRET_KEY=<your-secret-key>
docker-compose up --build
```

---

## 📁 Project Structure

```
fhir-r4-semantic-validator-agent/
├── agents/                         # Core agent modules (workers, supervisor, API)
│   ├── base.py                     # Security, PHI guard, HMAC audit trail
│   ├── models.py                   # Pydantic data models
│   ├── supervisor.py               # Master orchestrator
│   ├── workers.py                  # Specialized evaluation workers
│   ├── api.py                      # FastAPI REST endpoints
│   ├── metrics.py                  # Prometheus metrics exporter
│   ├── learning.py                 # Bayesian calibration engine
│   ├── llm_factory.py              # LLM provider factory
│   └── streamer.py                 # WebSocket telemetry broadcaster
├── fhir_r4_semantic_validator_agent/  # Alternative implementation package
├── tests/                          # Test suite
├── web/                            # Operations console (HTML)
├── cli.py                          # Main CLI entry point
├── fhir_validator_pro.py           # FHIR Validator Pro implementation
├── enrichment.py                   # Enrichment feature engines
├── simulator.py                    # High-throughput simulation
├── pyproject.toml                  # Project configuration
├── Dockerfile                      # Container build
├── docker-compose.yml              # Multi-service orchestration
└── .github/workflows/ci.yml        # CI/CD pipeline
```
