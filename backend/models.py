"""
ClaimPilot Data Models & Schemas
Defines all 11 collections, state enums, agent contracts, and the exact required EligibilityAssessment schema.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class ClaimState(str, Enum):
    DRAFT = "DRAFT"
    DOCUMENTS_UPLOADED = "DOCUMENTS_UPLOADED"
    PROCESSING = "PROCESSING"
    NEEDS_USER_INFO = "NEEDS_USER_INFO"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUBMITTED_MANUALLY = "SUBMITTED_MANUALLY"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"


class EligibilityStatus(str, Enum):
    LIKELY_ELIGIBLE = "likely_eligible"
    POSSIBLY_ELIGIBLE = "possibly_eligible"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    LIKELY_INELIGIBLE = "likely_ineligible"


class DocumentType(str, Enum):
    HOSPITAL_BILL = "hospital_bill"
    ITEMIZED_BILL = "itemized_bill"
    DISCHARGE_SUMMARY = "discharge_summary"
    POLICY_DOCUMENT = "policy_document"
    EMPLOYEE_CARD = "employee_card"
    PRESCRIPTION = "prescription"
    PAYSLIP = "payslip"
    INVESTIGATION_REPORT = "investigation_report"
    OTHER = "other"


# --- 1. Users ---
class UserProfile(BaseModel):
    user_id: str = Field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:8]}")
    full_name: str
    email: str
    phone: Optional[str] = None
    employer_name: Optional[str] = "Acme Corp India Pvt Ltd"
    employee_id: Optional[str] = "EMP-94812"
    abha_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# --- 2. Documents ---
class DocumentMeta(BaseModel):
    document_id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    claim_case_id: str
    filename: str
    doc_type: DocumentType
    file_size_bytes: int = 0
    page_count: int = 1
    sha256_hash: str = ""
    quality_score: float = 1.0  # 0.0 to 1.0 (clarity, lack of blur)
    tamper_detected: bool = False
    uploaded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    storage_path: Optional[str] = None


# --- 3. Extracted Facts ---
class SourceCitation(BaseModel):
    document_id: str
    document_name: Optional[str] = None
    source_page: int = 1
    confidence: float = 0.95
    bounding_box: Optional[Dict[str, float]] = None  # {x, y, width, height}
    snippet: Optional[str] = None


class ExtractedFact(BaseModel):
    fact_id: str = Field(default_factory=lambda: f"fact_{uuid.uuid4().hex[:8]}")
    claim_case_id: str
    key: str
    display_label: str
    value: Any
    original_value: Optional[Any] = None
    confidence: float = 0.95
    is_user_corrected: bool = False
    citation: Optional[SourceCitation] = None
    category: str = "general"  # patient, policy, hospital, billing, clinical


# --- 4. Supporting Evidence for Eligibility ---
class SupportingEvidenceItem(BaseModel):
    document_id: str
    fact: str
    source_page: int = 1
    confidence: float = 0.95


class EstimatedReimbursement(BaseModel):
    currency: str = "INR"
    minimum: float = 0.0
    maximum: float = 0.0
    basis: str = ""
    gross_claimed: float = 0.0
    non_medical_deductions: float = 0.0
    copay_amount: float = 0.0
    room_rent_penalty: float = 0.0


# --- 5. Eligibility Assessments ---
class EligibilityAssessment(BaseModel):
    claim_case_id: str
    eligibility_status: EligibilityStatus
    confidence: float = 0.95
    estimated_reimbursement: EstimatedReimbursement
    supporting_evidence: List[SupportingEvidenceItem] = []
    missing_information: List[str] = []
    risks_or_exclusions: List[str] = []
    next_best_action: str = "Review drafted claim packet and complete human approval."
    human_review_required: bool = True
    assessed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# --- 6. Evidence Checklists ---
class ChecklistItem(BaseModel):
    item_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    title: str
    category: str = "Mandatory IRDAI"
    status: str = "VERIFIED"  # VERIFIED, MISSING, ACTION_REQUIRED, OPTIONAL
    priority: str = "HIGH"  # HIGH, MEDIUM, LOW
    description: str
    action_type: Optional[str] = None  # REQUEST_FROM_HOSPITAL, UPLOAD_DOC, CONFIRM_WITH_HR
    action_payload: Optional[Dict[str, Any]] = None


class EvidenceChecklist(BaseModel):
    checklist_id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    claim_case_id: str
    overall_completeness: float = 0.85
    items: List[ChecklistItem] = []
    missing_count: int = 0
    verified_count: int = 0


# --- 7. Drafted Claims ---
class DraftedClaim(BaseModel):
    draft_id: str = Field(default_factory=lambda: f"drf_{uuid.uuid4().hex[:8]}")
    claim_case_id: str
    form_type: str = "IRDAI_STANDARD_REIMBURSEMENT_FORM"
    patient_name: str
    hospital_name: str
    policy_number: str
    gross_amount: float
    net_eligible_amount: float
    pdf_filename: Optional[str] = None
    pdf_url: Optional[str] = None
    cover_letter_text: Optional[str] = None
    drafted_emails: List[Dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# --- 8. Approval Requests ---
class ApprovalRequest(BaseModel):
    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:8]}")
    claim_case_id: str
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, MODIFIED
    disclaimer_accepted: bool = False
    signer_name: Optional[str] = None
    signer_declaration: str = "I confirm that the extracted information and attached receipts are accurate to the best of my knowledge."
    approved_at: Optional[str] = None
    comments: Optional[str] = None


# --- 9. Agent Runs ---
class AgentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    claim_case_id: str
    agent_name: str  # IntakeAgent, EligibilityAgent, EvidenceAgent, ClaimPrepAgent, FollowUpAgent, SafetyAgent
    status: str = "COMPLETED"  # RUNNING, COMPLETED, FAILED, ESCALATED
    latency_ms: float = 0.0
    tokens_consumed: int = 0
    confidence_score: float = 1.0
    summary_message: str = ""
    tool_calls: List[str] = []
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


# --- 10. Audit Events ---
class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    claim_case_id: str
    agent_name: str
    event_type: str  # CLASSIFICATION, EXTRACTION, ELIGIBILITY_CALC, EVIDENCE_CHECK, SAFETY_SCAN, USER_APPROVAL, DISPATCH
    title: str
    detail: str
    severity: str = "INFO"  # INFO, SUCCESS, WARNING, ALERT, CRITICAL
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# --- 11. Reminders ---
class Reminder(BaseModel):
    reminder_id: str = Field(default_factory=lambda: f"rem_{uuid.uuid4().hex[:8]}")
    claim_case_id: str
    title: str
    deadline_date: str
    days_remaining: int
    channel: str = "WHATSAPP_AND_EMAIL"  # EMAIL, SMS, WHATSAPP_AND_EMAIL, IN_APP
    status: str = "SCHEDULED"  # SCHEDULED, SENT, DISMISSED
    message_body: str


# --- Core Claim Case Entity ---
class ClaimCase(BaseModel):
    claim_case_id: str = Field(default_factory=lambda: f"CLM-{uuid.uuid4().hex[:6].upper()}")
    user_id: str = "usr_demo123"
    claim_type: str = "EMPLOYER_HEALTH_INSURANCE"  # Extensible to GOVT_BENEFIT, FLIGHT_DELAY, WARRANTY, TAX_REFUND
    state: ClaimState = ClaimState.DRAFT
    title: str = "Health Reimbursement Claim"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Financial Overview
    claimed_amount: float = 0.0
    estimated_reimbursable_min: float = 0.0
    estimated_reimbursable_max: float = 0.0
    eligibility_score: float = 0.0  # 0 to 100
    
    # Metadata
    patient_name: Optional[str] = None
    hospital_name: Optional[str] = None
    policy_number: Optional[str] = None
    insurer_name: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    filing_deadline: Optional[str] = None
    
    # Safety & Human Gate
    fraud_risk_level: str = "LOW"
    escalation_reason: Optional[str] = None
    human_approved: bool = False


# --- API Request Models ---
class FactUpdateRequest(BaseModel):
    key: str
    value: Any


class HumanApprovalRequest(BaseModel):
    signer_name: str
    signer_declaration: str = "I confirm that the extracted information and attached receipts are accurate to the best of my knowledge."
    disclaimer_accepted: bool = True
    comments: Optional[str] = None
