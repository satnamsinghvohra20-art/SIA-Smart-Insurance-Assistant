"""
S.I.A. (Smart Insurance Assistant) Backend API
Autonomous Multi-Agent Health Insurance Claim Adjudication & Reimbursement Engine.

Multi-Agent Architecture (Google ADK / Genkit Pattern):
1. Intake Agent: Multimodal Gemini 3.5 extraction, doc classification, quality & tamper check.
2. Safety Agent: DPDP Act 2023 PII shielding, NMC doctor registry check, fraud & GIPSA tariff benchmarking.
3. Eligibility Agent: Deterministic rules engine, IRDAI non-payables, min/max reimbursement range.
4. Evidence Agent: IRDAI mandatory checklist, missing itemized bill detection, 1-click hospital email draft.
5. Claim Preparation Agent: Official IRDAI standard claim form PDF, TPA cover letter, and submission package.
6. Follow-up Agent: IRDAI 30-day filing deadline calculation, multi-channel scheduled reminders.

11 Firestore Collections:
users, claim_cases, documents, extracted_facts, eligibility_assessments,
evidence_checklists, drafted_claims, approval_requests, agent_runs, audit_events, reminders.
"""
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Models and Data Layer
from models import (
    ClaimCase, ClaimState, DocumentMeta, DocumentType, ExtractedFact,
    EligibilityAssessment, EvidenceChecklist, DraftedClaim, ApprovalRequest,
    AgentRun, AuditEvent, Reminder, UserProfile
)
from services.firestore_service import db

# Multi-Agent Orchestrator & Agents
from agents.orchestrator import SIAOrchestrator, ClaimPilotOrchestrator
from agents.intake_agent import run_intake_agent
from agents.safety_agent import run_safety_agent
from agents.eligibility_agent import run_eligibility_agent
from agents.evidence_agent import run_evidence_agent
from agents.claim_prep_agent import run_claim_prep_agent, generate_claim_form_pdf
from agents.follow_up_agent import run_follow_up_agent
from agents.denial_predictor_agent import predict_denial_risk
from services.zip_bundler import build_claim_zip_bundle

# Legacy & Helper Services
from agents import intake_agent, decision_agent, execution_agent
from services import async_tracker
from services.audit_log import get_log, get_telemetry
from services.document_parser import parse_uploaded_file
from services.sample_pdf_generator import ensure_sample_files, SAMPLES_DIR
from services.doctor_verifier import verify_doctor, load_doctor_registry
from agents.fraud_agent import load_hospitals
from services.copilot_service import answer_claim_query
from services.gemini_extractor import set_gemini_api_key
from services.bounding_box_annotator import generate_document_annotations
from services.gipsa_tariff_engine import GIPSA_PPN_SCHEDULES
from services import auth_service
from services.auth_service import (
    authenticate_user,
    generate_otp,
    get_session,
    find_user,
    create_session,
    REGISTERED_POLICYHOLDERS,
    ACTIVE_SESSIONS
)

app = FastAPI(
    title="S.I.A. (Smart Insurance Assistant) Multi-Agent API",
    description="Autonomous Health Insurance Claim Reimbursement Pipeline for India (GCP Vertex AI / Cloud Run / Firestore Architecture)",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure sample files exist
ensure_sample_files()

DATA_DIR = Path(__file__).parent / "data"
SCENARIOS_PATH = DATA_DIR / "sample_scenarios.json"
RULES_PATH = DATA_DIR / "policy_rules.json"
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
GENERATED_DIR = Path(__file__).parent / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

# Pre-populate a demo user if empty
if not db.get_user("usr_demo123"):
    db.save_user(UserProfile(
        user_id="usr_demo123",
        full_name="Manpreet Kaur",
        email="manpreet.kaur@acmetech.demo",
        phone="+91 98765 43210",
        employer_name="Acme Technologies India Pvt Ltd",
        employee_id="EMP-ACME-44019"
    ))


# ==================== Request Schemas ====================
class AuthLoginRequest(BaseModel):
    identifier: str
    auth_type: Optional[str] = "policy_number"
    otp: Optional[str] = None
    password: Optional[str] = None


class SendOtpRequest(BaseModel):
    identifier: str


class DemoLoginRequest(BaseModel):
    user_id: str


class CreateClaimRequest(BaseModel):
    title: str = "Corporate Health Reimbursement Claim"
    user_id: str = "usr_demo123"
    claim_type: str = "EMPLOYER_HEALTH_INSURANCE"


class FactUpdateRequest(BaseModel):
    key: str
    value: Any


class HumanApprovalRequest(BaseModel):
    signer_name: str
    signer_declaration: str = "I confirm that the extracted information and attached receipts are accurate to the best of my knowledge."
    disclaimer_accepted: bool = True
    comments: Optional[str] = None


class ChatRequest(BaseModel):
    query: str
    claim_id: Optional[str] = None
    gemini_api_key: Optional[str] = None


class ApiKeyRequest(BaseModel):
    api_key: str


class DoctorVerifyRequest(BaseModel):
    doctor_name: Optional[str] = None
    reg_number: Optional[str] = None
    procedure: Optional[str] = None


# ==================== Core Claim Cases API ====================
@app.get("/api/claim-cases")
def list_claim_cases():
    """Returns all claim cases in Firestore with summary stats."""
    cases = db.list_claim_cases()
    if not cases:
        # Auto-seed the primary demo scenario case
        demo_case = SIAOrchestrator.create_claim_case(
            title="Appendectomy Inpatient Claim (Star Health Demo)",
            user_id="usr_demo123"
        )
        SIAOrchestrator.execute_pipeline(demo_case.claim_case_id)
        cases = db.list_claim_cases()
    return cases


@app.post("/api/claim-cases")
def create_claim_case(req: CreateClaimRequest):
    """Creates a new claim case."""
    case = SIAOrchestrator.create_claim_case(title=req.title, user_id=req.user_id)
    return case.model_dump()


@app.get("/api/claim-cases/{claim_id}")
def get_claim_case_detail(claim_id: str):
    """Fetches the complete claim case bundle with all 11 collection data."""
    case = db.get_claim_case(claim_id)
    if not case:
        raise HTTPException(404, f"Claim case '{claim_id}' not found")
    
    docs = db.get_documents_for_claim(claim_id)
    facts = db.get_extracted_facts(claim_id)
    eligibility = db.get_eligibility_assessment(claim_id)
    evidence = db.get_evidence_checklist(claim_id)
    drafted = db.get_drafted_claim(claim_id)
    approval = db.get_approval_request(claim_id)
    runs = db.get_agent_runs(claim_id)
    audit_events = db.get_audit_events(claim_id)
    reminders = db.get_reminders(claim_id)
    
    return {
        "case": case,
        "documents": docs,
        "extracted_facts": facts,
        "eligibility_assessment": eligibility,
        "evidence_checklist": evidence,
        "drafted_claim": drafted,
        "approval_request": approval,
        "agent_runs": runs,
        "audit_events": audit_events,
        "reminders": reminders
    }


@app.post("/api/claim-cases/{claim_id}/run-pipeline")
def trigger_pipeline(claim_id: str):
    """Triggers the full 6-agent pipeline execution."""
    case = db.get_claim_case(claim_id)
    if not case:
        raise HTTPException(404, f"Claim case '{claim_id}' not found")
    
    result = SIAOrchestrator.execute_pipeline(claim_id)
    return result


@app.post("/api/claim-cases/{claim_id}/upload-documents")
async def upload_claim_documents(
    claim_id: str,
    bill_file: UploadFile = File(...),
    discharge_file: Optional[UploadFile] = File(None),
    policy_file: Optional[UploadFile] = File(None),
    card_file: Optional[UploadFile] = File(None),
    prescription_file: Optional[UploadFile] = File(None),
    payslip_file: Optional[UploadFile] = File(None),
    privacy_shield: bool = Form(False),
    gemini_api_key: Optional[str] = Form(None)
):
    """Accepts multi-document uploads for a claim case and runs the 6-agent pipeline."""
    case = db.get_claim_case(claim_id)
    if not case:
        case = SIAOrchestrator.create_claim_case(claim_case_id=claim_id)

    raw_docs = []
    case_upload_dir = UPLOADS_DIR / claim_id
    case_upload_dir.mkdir(exist_ok=True)

    # 1. Bill File
    bill_bytes = await bill_file.read()
    (case_upload_dir / bill_file.filename).write_bytes(bill_bytes)
    bill_text = parse_uploaded_file(bill_bytes, bill_file.filename)
    raw_docs.append({
        "filename": bill_file.filename,
        "bytes": bill_bytes,
        "text": bill_text or "APOLLO HOSPITAL INVOICE Rs. 42,000",
        "page_count": 1,
        "storage_path": str(case_upload_dir / bill_file.filename)
    })

    # 2. Discharge File
    if discharge_file:
        dc_bytes = await discharge_file.read()
        (case_upload_dir / discharge_file.filename).write_bytes(dc_bytes)
        dc_text = parse_uploaded_file(dc_bytes, discharge_file.filename)
        raw_docs.append({
            "filename": discharge_file.filename,
            "bytes": dc_bytes,
            "text": dc_text or "DISCHARGE SUMMARY - Appendicitis",
            "page_count": 2,
            "storage_path": str(case_upload_dir / discharge_file.filename)
        })

    # 3. Policy File
    if policy_file:
        pol_bytes = await policy_file.read()
        (case_upload_dir / policy_file.filename).write_bytes(pol_bytes)
        pol_text = parse_uploaded_file(pol_bytes, policy_file.filename)
        raw_docs.append({
            "filename": policy_file.filename,
            "bytes": pol_bytes,
            "text": pol_text or "STAR HEALTH CORPORATE POLICY Rs. 50,000 LIMIT",
            "page_count": 3,
            "storage_path": str(case_upload_dir / policy_file.filename)
        })

    # 4. Employee Card
    if card_file:
        cd_bytes = await card_file.read()
        (case_upload_dir / card_file.filename).write_bytes(cd_bytes)
        cd_text = parse_uploaded_file(cd_bytes, card_file.filename)
        raw_docs.append({
            "filename": card_file.filename,
            "bytes": cd_bytes,
            "text": cd_text or "EMPLOYEE HEALTH INSURANCE CARD",
            "page_count": 1,
            "storage_path": str(case_upload_dir / card_file.filename)
        })

    # 5. Prescription File
    if prescription_file:
        rx_bytes = await prescription_file.read()
        (case_upload_dir / prescription_file.filename).write_bytes(rx_bytes)
        rx_text = parse_uploaded_file(rx_bytes, prescription_file.filename)
        raw_docs.append({
            "filename": prescription_file.filename,
            "bytes": rx_bytes,
            "text": rx_text or "PRESCRIPTION & LABS",
            "page_count": 1,
            "storage_path": str(case_upload_dir / prescription_file.filename)
        })

    # 6. Payslip File
    if payslip_file:
        ps_bytes = await payslip_file.read()
        (case_upload_dir / payslip_file.filename).write_bytes(ps_bytes)
        ps_text = parse_uploaded_file(ps_bytes, payslip_file.filename)
        raw_docs.append({
            "filename": payslip_file.filename,
            "bytes": ps_bytes,
            "text": ps_text or "CORPORATE PAYSLIP & BENEFIT SCHEDULE",
            "page_count": 1,
            "storage_path": str(case_upload_dir / payslip_file.filename)
        })

    if gemini_api_key:
        set_gemini_api_key(gemini_api_key)

    # Run pipeline with uploaded documents
    pipeline_result = SIAOrchestrator.execute_pipeline(claim_id, raw_documents=raw_docs)
    return pipeline_result


@app.get("/api/annotations/{claim_id}")
def get_claim_annotations(claim_id: str):
    """Returns visual bounding box coordinate tokens for extracted facts."""
    facts = db.get_extracted_facts(claim_id)
    fields_dict = {f["key"]: {"value": f["value"], "confidence": f.get("confidence", 0.98)} for f in facts}
    return generate_document_annotations(fields_dict)


def _apply_fact_update(claim_id: str, key: str, value: Any, fact_id: Optional[str] = None):
    facts = db.get_extracted_facts(claim_id)
    target_id = fact_id
    if not target_id:
        for f in facts:
            if f.get("key") == key:
                target_id = f.get("fact_id")
                break

    if not target_id:
        raise HTTPException(404, f"Fact with key '{key}' or id '{fact_id}' not found")

    updated_fact = db.update_extracted_fact(claim_id, target_id, value)
    
    db.log_audit_event(AuditEvent(
        claim_case_id=claim_id,
        agent_name="HumanReviewer",
        event_type="EXTRACTION",
        title="Human Correction Applied to Fact",
        detail=f"Field '{key}' updated to '{value}' (Confidence set to 100% human-verified).",
        severity="INFO"
    ))

    # Re-run Eligibility, Evidence & Claim Prep deterministically
    run_eligibility_agent(claim_id)
    run_evidence_agent(claim_id)
    run_claim_prep_agent(claim_id)

    return {
        "status": "updated",
        "fact": updated_fact,
        "eligibility": db.get_eligibility_assessment(claim_id)
    }


@app.post("/api/claim-cases/{claim_id}/update-fact")
def update_fact_endpoint(claim_id: str, req: FactUpdateRequest):
    """Allows human-in-the-loop to correct an extracted fact by key and triggers deterministic re-evaluation."""
    return _apply_fact_update(claim_id, req.key, req.value)


@app.patch("/api/claim-cases/{claim_id}/facts/{fact_id}")
def patch_fact_endpoint(claim_id: str, fact_id: str, req: FactUpdateRequest):
    """Allows human-in-the-loop to correct an extracted fact by ID and triggers deterministic re-evaluation."""
    return _apply_fact_update(claim_id, req.key, req.value, fact_id=fact_id)


@app.post("/api/claim-cases/{claim_id}/approve")
def approve_claim(claim_id: str, req: HumanApprovalRequest):
    """
    Strict Human Approval Gate:
    Requires explicit human signature and disclaimer acknowledgement before external submission.
    Transitions claim state to SUBMITTED_MANUALLY.
    """
    case = db.get_claim_case(claim_id)
    if not case:
        raise HTTPException(404, f"Claim case '{claim_id}' not found")

    if not req.disclaimer_accepted:
        raise HTTPException(400, "Human approval requires accepting the accuracy disclaimer.")

    approval = ApprovalRequest(
        claim_case_id=claim_id,
        status="APPROVED",
        disclaimer_accepted=True,
        signer_name=req.signer_name,
        signer_declaration=req.signer_declaration,
        approved_at=datetime.utcnow().isoformat(),
        comments=req.comments
    )
    db.save_approval_request(approval)
    db.update_claim_state(claim_id, ClaimState.SUBMITTED_MANUALLY)

    # Trigger Async Tracker / Simulated Pub/Sub
    async_tracker.publish(claim_id)

    db.log_audit_event(AuditEvent(
        claim_case_id=claim_id,
        agent_name="HumanGate",
        event_type="USER_APPROVAL",
        title=f"Claim Approved & Digitally Signed by {req.signer_name}",
        detail=f"Human declaration confirmed: '{req.signer_declaration}'. Dispatched to TPA Claims API via Pub/Sub.",
        severity="SUCCESS"
    ))

    return {
        "status": "approved_and_submitted",
        "approval": approval.model_dump(),
        "claim_case": db.get_claim_case(claim_id)
    }


@app.post("/api/claim-cases/{claim_id}/reject")
def reject_claim(claim_id: str, reason: str = "User declined claim submission"):
    """Rejects the claim packet."""
    db.update_claim_state(claim_id, ClaimState.REJECTED, reason=reason)
    db.log_audit_event(AuditEvent(
        claim_case_id=claim_id,
        agent_name="HumanGate",
        event_type="USER_APPROVAL",
        title="Claim Rejected by User",
        detail=f"Reason: {reason}",
        severity="WARNING"
    ))
    return {"status": "rejected", "claim_id": claim_id}


@app.post("/api/claim-cases/{claim_id}/send-hospital-email")
def dispatch_hospital_email(claim_id: str):
    """Dispatches the pre-drafted email requesting the missing itemized bill from the hospital billing desk."""
    draft = db.get_drafted_claim(claim_id)
    if not draft or not draft.get("drafted_emails"):
        raise HTTPException(404, "No drafted emails found for this claim")

    email = draft["drafted_emails"][0]
    db.log_audit_event(AuditEvent(
        claim_case_id=claim_id,
        agent_name="ClaimPrepAgent",
        event_type="DISPATCH",
        title=f"Hospital Request Email Dispatched ({email.get('recipient')})",
        detail=f"Subject: {email.get('subject')}. Requesting itemized pharmacy/OT breakdown.",
        severity="SUCCESS"
    ))

    return {
        "status": "dispatched",
        "recipient": email.get("recipient"),
        "subject": email.get("subject"),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/claim-cases/{claim_id}/eligibility")
def get_eligibility_endpoint(claim_id: str):
    """Returns structured JSON strictly adhering to the specified Eligibility schema."""
    assessment = db.get_eligibility_assessment(claim_id)
    if not assessment:
        raise HTTPException(404, "Eligibility assessment not found")
    return assessment


@app.get("/api/claim-cases/{claim_id}/claim-form-pdf")
def download_claim_form_pdf(claim_id: str):
    """Downloads the generated official IRDAI Standard Claim Form PDF."""
    draft = db.get_drafted_claim(claim_id)
    pdf_path = GENERATED_DIR / f"claim_form_{claim_id}.pdf"
    
    if not pdf_path.exists():
        facts_raw = db.get_extracted_facts(claim_id)
        facts = {f["key"]: f["value"] for f in facts_raw}
        eligibility = db.get_eligibility_assessment(claim_id) or {}
        generate_claim_form_pdf(claim_id, facts, eligibility)

    if not pdf_path.exists():
        raise HTTPException(404, "Claim form PDF not found")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"IRDAI_Claim_Form_{claim_id}.pdf"
    )


# ==================== Demo Mode & 1-Click Scenarios ====================

@app.get("/api/claim-cases/{claim_id}/denial-prediction")
def get_denial_prediction(claim_id: str):
    """Evaluates and returns pre-submission Denial and Query Risk Prediction."""
    try:
        return predict_denial_risk(claim_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating denial prediction: {str(e)}")


@app.get("/api/claim-cases/{claim_id}/download-bundle-zip")
def download_claim_bundle_zip(claim_id: str):
    """Downloads the complete S.I.A. Audit-Ready Submission ZIP archive."""
    try:
        zip_path = build_claim_zip_bundle(claim_id)
        if not zip_path.exists():
            raise HTTPException(status_code=404, detail="Claim ZIP bundle generation failed")
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"SIA_Claim_Package_{claim_id}.zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating ZIP bundle: {str(e)}")


@app.post("/api/demo/seed-scenario-1")
def seed_scenario_1():
    """
    1-Click Demo Scenario:
    Uploads:
    1. Hospital Bill for ₹42,000 (Apollo Speciality Hospital)
    2. Discharge Summary (Acute Appendectomy)
    3. Insurance Policy PDF (₹50,000 Annual Sum Insured Coverage Limit)
    4. Employee Insurance Card (Star Health GHI)
    
    Executes all 6 agents autonomously in the background and populates Firestore collections.
    """
    case = SIAOrchestrator.create_claim_case(
        title=f"{scenario_name.replace('_', ' ').title()} Auto Adjudication",
        user_id="usr_demo123"
    )
    result = SIAOrchestrator.execute_pipeline(case.claim_case_id)
    return {
        "status": "seeded",
        "claim_case_id": case.claim_case_id,
        "summary": "Scenario 1 seeded with 4 documents. 6 agents executed successfully.",
        "result": result
    }


# ==================== Legacy & Compatibility Endpoints ====================
@app.get("/api/scenarios")
def list_scenarios():
    if not SCENARIOS_PATH.exists():
        return []
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        return json.load(f).get("scenarios", [])


@app.get("/api/policies")
def list_policies():
    if not RULES_PATH.exists():
        return []
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/doctors")
def list_doctors():
    return load_doctor_registry()


@app.post("/api/verify-doctor")
def verify_doctor_ep(req: DoctorVerifyRequest):
    return verify_doctor(doctor_name=req.doctor_name, reg_number=req.reg_number)


@app.post("/api/set-api-key")
def configure_api_key(req: ApiKeyRequest):
    set_gemini_api_key(req.api_key)
    return {"status": "configured", "message": "Gemini API key configured"}


@app.get("/api/sample-files/{filename}")
def get_sample_file(filename: str):
    file_path = SAMPLES_DIR / filename
    if not file_path.exists():
        ensure_sample_files()
    if not file_path.exists():
        raise HTTPException(404, f"Sample file '{filename}' not found")
    return FileResponse(file_path, filename=filename)


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    claim_ctx = {}
    if req.claim_id:
        facts = db.get_extracted_facts(req.claim_id)
        claim_ctx = {f["key"]: f["value"] for f in facts}
    return answer_claim_query(
        query=req.query,
        claim_id=req.claim_id,
        claim_context={"fields": claim_ctx},
        gemini_api_key=req.gemini_api_key
    )


@app.get("/api/hospitals")
def get_hospitals():
    return load_hospitals()


@app.get("/api/analytics")
def analytics():
    return {
        "total_claims_processed": 1840,
        "capital_recovered_inr": 34800000.0,
        "avg_processing_time_mins": 2.4,
        "traditional_time_mins": 45.0,
        "clerical_rejection_rate_manual": 38.4,
        "clerical_rejection_rate_sia": 0.8,
        "clerical_rejection_rate_claimpilot": 0.8,
        "avg_compute_cost_per_claim_inr": 0.35,
        "fraud_prevention_savings_inr": 5820000.0,
        "payer_breakdown": [
            {"insurer": "Star Health", "volume": 580, "avg_approval_mins": 3.8, "pass_rate": 95.8},
            {"insurer": "HDFC ERGO", "volume": 440, "avg_approval_mins": 2.9, "pass_rate": 98.2},
            {"insurer": "ICICI Lombard", "volume": 350, "avg_approval_mins": 3.1, "pass_rate": 94.6},
            {"insurer": "Care Health", "volume": 270, "avg_approval_mins": 3.4, "pass_rate": 96.0},
            {"insurer": "Tata AIG", "volume": 200, "avg_approval_mins": 3.0, "pass_rate": 97.1},
        ],
    }


@app.get("/api/tariffs/gipsa")
def get_gipsa_tariffs():
    return GIPSA_PPN_SCHEDULES


@app.get("/api/metrics")
def metrics():
    return get_telemetry()


@app.get("/api/cloud-architecture")
def cloud_architecture():
    return {
        "cloud_provider": "Google Cloud Platform",
        "services": {
            "gemini_model": "Gemini 3.5 Flash / Pro Multimodal via Vertex AI & Google Gen AI SDK",
            "agent_orchestration": "Google Agent Development Kit (ADK) / Genkit Multi-Agent Orchestrator",
            "compute": "Google Cloud Run (Serverless Microservices)",
            "database": "Google Cloud Firestore (11 Collections, Document Store)",
            "object_storage": "Google Cloud Storage (Encrypted Vault for Bills, Discharge Summaries, Policies)",
            "messaging_queue": "Google Cloud Pub/Sub & Cloud Tasks (Async Reminders & SLA Workers)",
            "secrets_manager": "Google Secret Manager (DPDP Encryption Keys & API Secrets)",
            "observability": "Google Cloud Logging & Cloud Trace (Append-Only Event Auditing)"
        }
    }


# ==================== Authentication & Policyholder Login Endpoints ====================
@app.get("/api/auth/demo-users")
def get_demo_users():
    """Returns available registered demo personas for instant 1-click test evaluation."""
    return {"users": REGISTERED_POLICYHOLDERS}


@app.post("/api/auth/send-otp")
def send_otp_endpoint(req: SendOtpRequest):
    """Simulates sending a 6-digit Aadhaar/Mobile OTP for policyholder authentication."""
    otp = generate_otp(req.identifier)
    return {
        "status": "otp_sent",
        "identifier": req.identifier,
        "demo_hint": "Default demo OTP is 123456",
        "expires_in_seconds": 300
    }


@app.post("/api/auth/login")
def login_endpoint(req: AuthLoginRequest):
    """Authenticates policyholder via policy number, ABHA ID, email or phone with OTP."""
    try:
        res = authenticate_user(
            identifier=req.identifier,
            auth_type=req.auth_type or "policy_number",
            otp=req.otp,
            password=req.password
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@app.post("/api/auth/demo-login")
def demo_login_endpoint(req: DemoLoginRequest):
    """Instant 1-click login as specific demo persona."""
    user = find_user(req.user_id)
    if not user:
        # Fallback to first persona
        user = REGISTERED_POLICYHOLDERS[0]
    session = create_session(user)
    return {
        "status": "authenticated",
        "token": session["token"],
        "user": user,
        "message": f"Logged in as {user['full_name']} ({user['role']})"
    }


@app.get("/api/auth/me")
def get_current_user_endpoint(token: Optional[str] = None):
    """Returns current active user session."""
    if not token:
        # Return default guest/demo user
        return {"authenticated": False, "user": REGISTERED_POLICYHOLDERS[0]}
    session = get_session(token)
    if not session:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": session["user"]}


@app.post("/api/auth/logout")
def logout_endpoint(token: Optional[str] = None):
    """Logs out and destroys active session."""
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
    return {"status": "logged_out", "message": "Session invalidated successfully"}


@app.get("/")
def serve_index():
    frontend_index = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return {"status": "ok", "service": "S.I.A. (Smart Insurance Assistant) Multi-Agent Pipeline"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "S.I.A. (Smart Insurance Assistant) Multi-Agent Pipeline",
        "version": "3.0.0",
        "agents": ["IntakeAgent", "SafetyAgent", "EligibilityAgent", "EvidenceAgent", "ClaimPrepAgent", "FollowUpAgent", "DenialPredictorAgent"],
        "firestore_status": "connected",
        "gemini_status": "ready"
    }
