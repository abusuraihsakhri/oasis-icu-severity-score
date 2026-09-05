# OASIS ICU Severity Score

> **Domain:** Clinical Decision Support & Biomedical Computing

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

Oxford Acute Severity of Illness Score (OASIS) - Non-laboratory severity-of-illness score for ICU admissions using vital signs and pre-ICU stay.

Zero-dependency Python implementation with single and batch evaluation.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Key Features

- **Single Case Evaluation**: Calculate OASIS score for individual patients
- **Batch Processing**: Process CSV files with multiple patient records
- **PHI Protection**: Outbound guard preventing protected health information leakage
- **HMAC-SHA256 Audit Trail**: Tamper-evident cryptographic logging
- **FastAPI REST API**: OpenAPI 3.1 compliant REST endpoints
- **Prometheus Metrics**: Operational telemetry export
- **Multi-Worker Assessment**: Consensus-based evaluation with specialized workers

---

## Installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/oasis-icu-severity-score.git
cd oasis-icu-severity-score

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set required environment variable
export AUDIT_SECRET_KEY="your-secure-audit-key-min-16-chars"
```

### Docker Deployment

```bash
# Set your audit key
export AUDIT_SECRET_KEY="your-secure-production-audit-key"

# Build and run
docker-compose up --build
```

---

## Usage

### Single Case Evaluation

```bash
# With explicit parameters
python oasis_score.py single --v1 14.5 --v2 4.2 --v3 1.8

# Interactive defaults
python oasis_score.py single
```

### Batch CSV Processing

```bash
python oasis_score.py batch -i sample.csv -o results.csv
```

### Agent Supervisor CLI

```bash
# Run single audit task
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch processing
python cli.py batch -i input.csv -o output.csv

# Verify audit trail integrity
python cli.py verify-audit

# Start REST API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and service metadata |
| `/metrics` | GET | Prometheus operational metrics |
| `/api/audit` | POST | Submit task for multi-worker evaluation |
| `/api/chat` | POST | Supervisory conversational assistant |
| `/api/audit/logs` | GET | Retrieve and verify HMAC audit trail |

---

## Input Data Schema

### CSV Format for Batch Processing

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier | Required |
| `v1` | Primary parameter (e.g., heart rate) | Required |
| `v2` | Secondary parameter (e.g., blood pressure) | Required |
| `v3` | Tertiary parameter (e.g., temperature) | Required |

See `sample.csv` for example data.

---

## Security

### Required Configuration

The `AUDIT_SECRET_KEY` environment variable **must** be set. Generate a secure key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Security Features

- **Zero-PHI Outbound Guard**: AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **HMAC-SHA256 Audit Trail**: Cryptographically chained, tamper-evident logs
- **Path Traversal Protection**: Validated CSV input/output paths
- **Input Sanitization**: Type validation and bounds checking on all inputs

---

## Testing

```bash
# Set test environment variable
export AUDIT_SECRET_KEY="test-secret-key-for-testing-1234567890"

# Run full test suite
pytest -v

# Run specific test modules
pytest tests/test_security_and_validation.py -v
pytest tests/test_enrichment.py -v
pytest tests/test_oasis_icu_severity_score.py -v

# Run simulation benchmark
python simulator.py --tasks 1000
```

---

## Project Structure

```
oasis-icu-severity-score/
├── agents/                    # Multi-agent supervisor framework
│   ├── api.py                 # FastAPI REST endpoints
│   ├── base.py                # Security, PHI guard, HMAC audit trail
│   ├── learning.py            # Bayesian calibration engine
│   ├── llm_factory.py         # LLM provider abstraction
│   ├── metrics.py             # Prometheus metrics collector
│   ├── models.py              # Pydantic data models
│   ├── streamer.py            # WebSocket telemetry broadcaster
│   ├── supervisor.py          # Master orchestrator
│   └── workers.py             # Specialized domain workers
├── tests/                     # Test suite
│   ├── test_enrichment.py     # Enrichment engine tests
│   ├── test_oasis_icu_severity_score.py  # Core functionality tests
│   └── test_security_and_validation.py   # Security & validation tests
├── web/                       # Static web assets
├── cli.py                     # Command-line interface
├── oasis_score.py             # Core OASIS calculation
├── enrichment.py              # Enrichment feature engines
├── simulator.py               # High-throughput simulation
├── openapi_spec.json          # OpenAPI 3.1 specification
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container build
├── docker-compose.yml         # Container orchestration
└── sample.csv                 # Example input data
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.
