"""
Firestore Data Access Layer for S.I.A. (Smart Insurance Assistant)
Implements all 11 required collections:
1. users
2. claim_cases
3. documents
4. extracted_facts
5. eligibility_assessments
6. evidence_checklists
7. drafted_claims
8. approval_requests
9. agent_runs
10. audit_events
11. reminders

Supports zero-config local file/memory storage and seamless Google Cloud Firestore client.
"""
import os
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import (
    ClaimCase, ClaimState, DocumentMeta, ExtractedFact,
    EligibilityAssessment, EvidenceChecklist, DraftedClaim,
    ApprovalRequest, AgentRun, AuditEvent, Reminder, UserProfile
)

STORE_DIR = Path(__file__).parent.parent / "data" / "store"
STORE_DIR.mkdir(parents=True, exist_ok=True)

class FirestoreService:
    def __init__(self):
        self._lock = threading.Lock()
        self.use_gcp_firestore = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and os.getenv("GCP_PROJECT_ID"))
        self._db = None
        
        if self.use_gcp_firestore:
            try:
                from google.cloud import firestore
                self._db = firestore.Client(project=os.getenv("GCP_PROJECT_ID"))
                print(f"[FirestoreService] Connected to live Google Cloud Firestore (Project: {os.getenv('GCP_PROJECT_ID')})")
            except Exception as e:
                print(f"[FirestoreService] Could not initialize GCP Firestore ({e}). Falling back to local storage.")
                self.use_gcp_firestore = False

        # In-memory storage buffers for all 11 collections
        self.users: Dict[str, Dict[str, Any]] = {}
        self.claim_cases: Dict[str, Dict[str, Any]] = {}
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.extracted_facts: Dict[str, List[Dict[str, Any]]] = {}  # keyed by claim_case_id
        self.eligibility_assessments: Dict[str, Dict[str, Any]] = {} # keyed by claim_case_id
        self.evidence_checklists: Dict[str, Dict[str, Any]] = {}     # keyed by claim_case_id
        self.drafted_claims: Dict[str, Dict[str, Any]] = {}          # keyed by claim_case_id
        self.approval_requests: Dict[str, Dict[str, Any]] = {}       # keyed by claim_case_id
        self.agent_runs: Dict[str, List[Dict[str, Any]]] = {}        # keyed by claim_case_id
        self.audit_events: Dict[str, List[Dict[str, Any]]] = {}      # keyed by claim_case_id
        self.reminders: Dict[str, List[Dict[str, Any]]] = {}         # keyed by claim_case_id

        self._load_local_state()

    def _load_local_state(self):
        state_file = STORE_DIR / "local_firestore_dump.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.users = data.get("users", {})
                    self.claim_cases = data.get("claim_cases", {})
                    self.documents = data.get("documents", {})
                    self.extracted_facts = data.get("extracted_facts", {})
                    self.eligibility_assessments = data.get("eligibility_assessments", {})
                    self.evidence_checklists = data.get("evidence_checklists", {})
                    self.drafted_claims = data.get("drafted_claims", {})
                    self.approval_requests = data.get("approval_requests", {})
                    self.agent_runs = data.get("agent_runs", {})
                    self.audit_events = data.get("audit_events", {})
                    self.reminders = data.get("reminders", {})
            except Exception as e:
                print(f"[FirestoreService] Warning reading local state: {e}")

    def _persist_local_state(self):
        state_file = STORE_DIR / "local_firestore_dump.json"
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "users": self.users,
                    "claim_cases": self.claim_cases,
                    "documents": self.documents,
                    "extracted_facts": self.extracted_facts,
                    "eligibility_assessments": self.eligibility_assessments,
                    "evidence_checklists": self.evidence_checklists,
                    "drafted_claims": self.drafted_claims,
                    "approval_requests": self.approval_requests,
                    "agent_runs": self.agent_runs,
                    "audit_events": self.audit_events,
                    "reminders": self.reminders
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"[FirestoreService] Warning saving local state: {e}")

    # ==================== 1. USERS ====================
    def save_user(self, user: UserProfile):
        with self._lock:
            data = user.model_dump()
            self.users[user.user_id] = data
            if self.use_gcp_firestore and self._db:
                self._db.collection("users").document(user.user_id).set(data)
            self._persist_local_state()
            return data

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.users.get(user_id)

    # ==================== 2. CLAIM CASES ====================
    def save_claim_case(self, case: ClaimCase):
        with self._lock:
            data = case.model_dump()
            data["updated_at"] = datetime.utcnow().isoformat()
            self.claim_cases[case.claim_case_id] = data
            if self.use_gcp_firestore and self._db:
                self._db.collection("claim_cases").document(case.claim_case_id).set(data)
            self._persist_local_state()
            return data

    def get_claim_case(self, claim_case_id: str) -> Optional[Dict[str, Any]]:
        return self.claim_cases.get(claim_case_id)

    def list_claim_cases(self) -> List[Dict[str, Any]]:
        return list(self.claim_cases.values())

    def update_claim_state(self, claim_case_id: str, new_state: ClaimState, reason: Optional[str] = None):
        with self._lock:
            if claim_case_id in self.claim_cases:
                self.claim_cases[claim_case_id]["state"] = new_state.value
                self.claim_cases[claim_case_id]["updated_at"] = datetime.utcnow().isoformat()
                if reason:
                    self.claim_cases[claim_case_id]["escalation_reason"] = reason
                if self.use_gcp_firestore and self._db:
                    self._db.collection("claim_cases").document(claim_case_id).update({
                        "state": new_state.value,
                        "updated_at": datetime.utcnow().isoformat()
                    })
                self._persist_local_state()

    # ==================== 3. DOCUMENTS ====================
    def add_document(self, doc: DocumentMeta):
        with self._lock:
            data = doc.model_dump()
            self.documents[doc.document_id] = data
            if self.use_gcp_firestore and self._db:
                self._db.collection("documents").document(doc.document_id).set(data)
            self._persist_local_state()
            return data

    def get_documents_for_claim(self, claim_case_id: str) -> List[Dict[str, Any]]:
        return [doc for doc in self.documents.values() if doc.get("claim_case_id") == claim_case_id]

    # ==================== 4. EXTRACTED FACTS ====================
    def save_extracted_facts(self, claim_case_id: str, facts: List[ExtractedFact]):
        with self._lock:
            fact_dicts = [f.model_dump() for f in facts]
            self.extracted_facts[claim_case_id] = fact_dicts
            if self.use_gcp_firestore and self._db:
                batch = self._db.batch()
                for fact in facts:
                    doc_ref = self._db.collection("extracted_facts").document(fact.fact_id)
                    batch.set(doc_ref, fact.model_dump())
                batch.commit()
            self._persist_local_state()

    def get_extracted_facts(self, claim_case_id: str) -> List[Dict[str, Any]]:
        return self.extracted_facts.get(claim_case_id, [])

    def update_extracted_fact(self, claim_case_id: str, fact_id: str, new_value: Any) -> Optional[Dict[str, Any]]:
        with self._lock:
            facts = self.extracted_facts.get(claim_case_id, [])
            for fact in facts:
                if fact.get("fact_id") == fact_id:
                    fact["original_value"] = fact.get("value")
                    fact["value"] = new_value
                    fact["is_user_corrected"] = True
                    fact["confidence"] = 1.0  # Explicit human validation
                    self._persist_local_state()
                    return fact
            return None

    # ==================== 5. ELIGIBILITY ASSESSMENTS ====================
    def save_eligibility_assessment(self, assessment: EligibilityAssessment):
        with self._lock:
            data = assessment.model_dump()
            self.eligibility_assessments[assessment.claim_case_id] = data
            if self.use_gcp_firestore and self._db:
                self._db.collection("eligibility_assessments").document(assessment.claim_case_id).set(data)
            self._persist_local_state()
            return data

    def get_eligibility_assessment(self, claim_case_id: str) -> Optional[Dict[str, Any]]:
        return self.eligibility_assessments.get(claim_case_id)

    # ==================== 6. EVIDENCE CHECKLISTS ====================
    def save_evidence_checklist(self, checklist: EvidenceChecklist):
        with self._lock:
            data = checklist.model_dump()
            self.evidence_checklists[checklist.claim_case_id] = data
            if self.use_gcp_firestore and self._db:
                self._db.collection("evidence_checklists").document(checklist.claim_case_id).set(data)
            self._persist_local_state()
            return data

    def get_evidence_checklist(self, claim_case_id: str) -> Optional[Dict[str, Any]]:
        return self.evidence_checklists.get(claim_case_id)

    # ==================== 7. DRAFTED CLAIMS ====================
    def save_drafted_claim(self, draft: DraftedClaim):
        with self._lock:
            data = draft.model_dump()
            self.drafted_claims[draft.claim_case_id] = data
            if self.use_gcp_firestore and self._db:
                self._db.collection("drafted_claims").document(draft.claim_case_id).set(data)
            self._persist_local_state()
            return data

    def get_drafted_claim(self, claim_case_id: str) -> Optional[Dict[str, Any]]:
        return self.drafted_claims.get(claim_case_id)

    # ==================== 8. APPROVAL REQUESTS ====================
    def save_approval_request(self, request: ApprovalRequest):
        with self._lock:
            data = request.model_dump()
            self.approval_requests[request.claim_case_id] = data
            if self.use_gcp_firestore and self._db:
                self._db.collection("approval_requests").document(request.claim_case_id).set(data)
            self._persist_local_state()
            return data

    def get_approval_request(self, claim_case_id: str) -> Optional[Dict[str, Any]]:
        return self.approval_requests.get(claim_case_id)

    # ==================== 9. AGENT RUNS ====================
    def record_agent_run(self, run: AgentRun):
        with self._lock:
            data = run.model_dump()
            runs = self.agent_runs.setdefault(run.claim_case_id, [])
            runs.append(data)
            if self.use_gcp_firestore and self._db:
                self._db.collection("agent_runs").document(run.run_id).set(data)
            self._persist_local_state()
            return data

    def get_agent_runs(self, claim_case_id: str) -> List[Dict[str, Any]]:
        return self.agent_runs.get(claim_case_id, [])

    # ==================== 10. AUDIT EVENTS ====================
    def log_audit_event(self, event: AuditEvent):
        with self._lock:
            data = event.model_dump()
            events = self.audit_events.setdefault(event.claim_case_id, [])
            events.append(data)
            if self.use_gcp_firestore and self._db:
                self._db.collection("audit_events").document(event.event_id).set(data)
            self._persist_local_state()
            return data

    def get_audit_events(self, claim_case_id: str) -> List[Dict[str, Any]]:
        return self.audit_events.get(claim_case_id, [])

    # ==================== 11. REMINDERS ====================
    def save_reminder(self, reminder: Reminder):
        with self._lock:
            data = reminder.model_dump()
            rems = self.reminders.setdefault(reminder.claim_case_id, [])
            rems.append(data)
            if self.use_gcp_firestore and self._db:
                self._db.collection("reminders").document(reminder.reminder_id).set(data)
            self._persist_local_state()
            return data

    def get_reminders(self, claim_case_id: str) -> List[Dict[str, Any]]:
        return self.reminders.get(claim_case_id, [])


# Global singleton database service
db = FirestoreService()
