"""
ClaimPilot backend — FastAPI orchestration layer over the 3-agent pipeline:
Intake Agent → Decision Agent → Execution Agent.

Features:
- 4 realistic Indian insurance reimbursement scenario presets.
- Deterministic rules engine + Gemini 3.5 prompt abstraction.
- Live streaming tool execution audit logs.
- IRDAI Standard TPA Claim Form PDF generation.
- Idempotent async tracking simulation (Pub/Sub + Cloud Run).
- Telemetry & performance metrics.
"""
import sys
import json
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agents import intake_agent, decision_agent, execution_agent
from services import async_tracker
from services.audit_log import get_log, get_telemetry

app = FastAPI(
    title="ClaimPilot Multi-Agent API",
    description="Autonomous Health Insurance Claim Reimbursement Pipeline for India",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory claim store — maps to Firestore in production
CLAIMS = {}

DATA_DIR = Path(__file__).parent / "data"
SCENARIOS_PATH = DATA_DIR / "sample_scenarios.json"
RULES_PATH = DATA_DIR / "policy_rules.json"


class IntakeRequest(BaseModel):
    raw_text: str | None = None
    field_overrides: dict | None = None
    scenario_id: str | None = None


class DecisionRequest(BaseModel):
    policy_override: str | None = None


class ApproveRequest(BaseModel):
    claim_id: str


@app.get("/api/scenarios")
def list_scenarios():
    """Lists available realistic Indian demo scenarios."""
    if not SCENARIOS_PATH.exists():
        raise HTTPException(404, "Scenarios file not found")
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("scenarios", [])


@app.get("/api/scenario/{scenario_id}")
def get_scenario(scenario_id: str):
    """Retrieves a single scenario by ID."""
    if not SCENARIOS_PATH.exists():
        raise HTTPException(404, "Scenarios file not found")
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for sc in data.get("scenarios", []):
        if sc["id"] == scenario_id:
            return sc
    raise HTTPException(404, f"Scenario '{scenario_id}' not found")


@app.get("/api/policies")
def list_policies():
    """Returns policy rules database."""
    if not RULES_PATH.exists():
        raise HTTPException(404, "Policy rules not found")
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/intake")
def intake(req: IntakeRequest):
    """Intake Agent: extracts structured fields with confidence scores."""
    claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"

    # Resolve bill text
    raw_text = req.raw_text
    if not raw_text:
        if SCENARIOS_PATH.exists():
            with open(SCENARIOS_PATH, encoding="utf-8") as f:
                data = json.load(f)
                raw_text = data["scenarios"][0]["bill_text"]
        else:
            raw_text = "FINAL HOSPITAL BILL\nPatient Name: Satnam Singh\nTotal: 77500.00"

    intake_result = intake_agent.run_intake(
        claim_id=claim_id,
        raw_text=raw_text,
        field_overrides=req.field_overrides,
    )

    CLAIMS[claim_id] = {
        "claim_id": claim_id,
        "raw_text": raw_text,
        "intake": intake_result,
    }

    return {"claim_id": claim_id, "intake": intake_result}


@app.post("/api/intake/{claim_id}/update-fields")
def update_intake_fields(claim_id: str, overrides: dict):
    """Allows human-in-the-loop to update low-confidence fields before running decision."""
    if claim_id not in CLAIMS:
        raise HTTPException(404, "Claim not found")

    raw_text = CLAIMS[claim_id].get("raw_text", "")
    intake_result = intake_agent.run_intake(
        claim_id=claim_id,
        raw_text=raw_text,
        field_overrides=overrides,
    )
    CLAIMS[claim_id]["intake"] = intake_result

    # Clear subsequent steps if fields changed
    CLAIMS[claim_id].pop("decision", None)
    CLAIMS[claim_id].pop("execution", None)

    return {"claim_id": claim_id, "intake": intake_result}


@app.post("/api/decision/{claim_id}")
def decision(claim_id: str):
    """Decision Agent: evaluates policy rules, sub-limits, exclusions, and co-pay deterministically."""
    if claim_id not in CLAIMS or "intake" not in CLAIMS[claim_id]:
        raise HTTPException(404, "Run intake step first")

    decision_result = decision_agent.run_decision(claim_id, CLAIMS[claim_id]["intake"])
    CLAIMS[claim_id]["decision"] = decision_result

    return {"claim_id": claim_id, "decision": decision_result}


@app.post("/api/execute/{claim_id}")
def execute(claim_id: str):
    """Execution Agent: generates IRDAI claim form PDF and evidence checklist."""
    if claim_id not in CLAIMS or "decision" not in CLAIMS[claim_id]:
        raise HTTPException(404, "Run decision step first")

    execution_result = execution_agent.run_execution(
        claim_id=claim_id,
        intake_result=CLAIMS[claim_id]["intake"],
        decision=CLAIMS[claim_id]["decision"],
    )
    CLAIMS[claim_id]["execution"] = execution_result

    return {"claim_id": claim_id, "execution": execution_result}


@app.post("/api/approve")
def approve(req: ApproveRequest):
    """Human-in-the-loop Gate: triggers simulated Pub/Sub submission and async tracking."""
    claim_id = req.claim_id
    if claim_id not in CLAIMS or "execution" not in CLAIMS[claim_id]:
        raise HTTPException(404, "Run execution step first")

    result = execution_agent.submit_to_tpa(claim_id)
    async_tracker.publish(claim_id)

    return {"claim_id": claim_id, "submission": result}


@app.get("/api/tracking/{claim_id}")
def tracking(claim_id: str):
    """Fetches real-time status updates from the async tracking poller."""
    status = async_tracker.get_status(claim_id)
    if status is None:
        raise HTTPException(404, "Claim not yet submitted for tracking")
    return status


@app.get("/api/audit/{claim_id}")
def audit(claim_id: str):
    """Fetches the append-only audit event log and tool execution trace."""
    return get_log(claim_id)


@app.get("/api/claim-form/{claim_id}")
def claim_form(claim_id: str):
    """Downloads the generated IRDAI Standard Claim Form PDF."""
    execution = CLAIMS.get(claim_id, {}).get("execution")
    if not execution or not execution.get("form_path"):
        raise HTTPException(404, "Claim form not generated yet")
    return FileResponse(
        execution["form_path"],
        media_type="application/pdf",
        filename=f"IRDAI_ClaimForm_{claim_id}.pdf",
    )


@app.get("/api/metrics")
def metrics():
    """Returns agent performance telemetry, token consumption, and cost estimates."""
    return get_telemetry()


@app.get("/")
def serve_index():
    frontend_index = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return {"status": "ok", "service": "ClaimPilot Multi-Agent Pipeline"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "ClaimPilot Multi-Agent Pipeline", "version": "2.0.0"}

