"""
FastAPI REST API Server for Oasis Icu Severity Score.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from .metrics import GLOBAL_METRICS
from .base import SecurityException
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Oasis Icu Severity Score API",
    description="Demonstration supervisor endpoints; not a validated clinical decision-support system.",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "oasis-icu-severity-score", "domain": "Clinical & Biomedical AI", "mode": "demonstration", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(GLOBAL_METRICS.export_prometheus_text(),
                             media_type="text/plain; version=0.0.4")


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException as exc:
        GLOBAL_METRICS.record_phi_block()
        raise HTTPException(status_code=422, detail="Possible identifying data") from exc
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException as exc:
        GLOBAL_METRICS.record_phi_block()
        raise HTTPException(status_code=422, detail="Possible identifying data") from exc


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
