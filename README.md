# Hoplid DevOps Assessment — Starter

This is a starting point. It is not yet the complete assessment.

## Prerequisites
- Docker Desktop with Docker Compose
- Git
- Optional: Python 3.11+ for running tests locally

## Start
```bash
docker compose up --build -d
docker compose ps
```
Open http://localhost:8000/docs and check http://localhost:8000/health.

## Create an order (PowerShell-friendly)
```powershell
$body = '{"user_id":"user-101","vendor_id":"vendor-12","items":[{"item_id":"meal-7","quantity":2}]}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/orders -Headers @{"Idempotency-Key"="demo-001"} -ContentType "application/json" -Body $body
```
Repeat the same request and key; it should return the same order. Reuse that key with a different body; it should return HTTP 409.

## Tests
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```
Ensure PostgreSQL is running before tests that access the API/database.

## Current status
- [x] FastAPI API and health endpoint
- [x] PostgreSQL order storage
- [x] Idempotency key and unique DB constraint
- [x] Docker Compose
- [x] Starter tests
- [ ] Kubernetes manifests, probes, resource requests/limits and scaling plan
- [ ] GitHub Actions workflow and security scanning
- [ ] Versioned migrations and expand/contract plan
- [ ] Load test and measured report
- [ ] Failure injection evidence, deployment verification and recovery demo
- [ ] Completed incident postmortem

## AI/tool disclosure
Before submission, accurately describe which AI tools you used, what you reviewed yourself, and which commands/tests you ran. Do not claim unverified results.
