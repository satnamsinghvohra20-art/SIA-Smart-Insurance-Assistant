# S.I.A. (Smart Insurance Assistant) — Autonomous Multi-Agent Health Reimbursement Platform

> **Production-style Multi-Agent AI system that helps Indian employees discover, verify, prepare, and track eligible medical insurance reimbursements with strict human-in-the-loop safety controls.**

[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI%20%7C%20Cloud%20Run%20%7C%20Firestore-4285F4?style=flat&logo=googlecloud)](https://cloud.google.com)
[![Gemini 3.5](https://img.shields.io/badge/Gemini%203.5-Multimodal%20Extraction-8E75B2?style=flat&logo=google)](https://ai.google.dev)
[![Architecture](https://img.shields.io/badge/Multi--Agent-ADK%20%2F%20Genkit%20Pattern-10B981?style=flat)](https://cloud.google.com)
[![License](https://img.shields.io/badge/Compliance-DPDP%20Act%202023%20%7C%20IRDAI%20Standard-2563EB?style=flat)](https://www.irdai.gov.in)

---

## 🎯 The Core Problem

Indian corporate employees lose over **₹18,000 Crores annually** in unclaimed or clerical rejected health insurance reimbursements due to:
1. **Opaque Policy Clauses & Exclusions:** Employees don't know what is covered, sub-limits, or non-payable items.
2. **Missing Itemized Documents:** Hospitals frequently omit unit-price itemized pharmacy / OT consumable schedules, causing TPAs to repudiate or delay claims.
3. **Clerical Turnaround Delays:** Manual claim filling takes 45+ minutes per claim and is prone to errors.
4. **Filing Deadlines:** 30-day post-discharge deadlines are frequently missed without active tracking.

**S.I.A. (Smart Insurance Assistant)** converts complicated medical documents into an actionable, verified, human-approved reimbursement package in under 3 minutes.

---

## 🏗️ Google Cloud Architecture & Multi-Agent Design

```
+---------------------------------------------------------------------------------------------------+
|                        S.I.A. (Smart Insurance Assistant) Enterprise Web UI                       |
|    (Eligibility Gauge, 6-Agent Rail, Editable Facts, Missing Itemized Action, IRDAI PDF Viewer)  |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v  (REST API / Cloud Run)
+---------------------------------------------------------------------------------------------------+
|                        Autonomous 6-Agent Pipeline (Google ADK / Genkit Pattern)                   |
|                                                                                                   |
|  1. Intake Agent      -> Gemini 3.5 Multimodal Extraction, Doc Classification & Tamper Analysis   |
|  2. Safety Agent      -> DPDP Act 2023 PII Masking, NMC Doctor Check, Anti-Fraud & GIPSA Tariffs  |
|  3. Eligibility Agent -> Deterministic Rules, IRDAI Non-Payables, Min/Max Reimbursement Math     |
|  4. Evidence Agent    -> IRDAI Mandatory Checklist, Missing Itemized Bill Detection & Email Draft  |
|  5. Claim Prep Agent  -> IRDAI Form (Part A/B) PDF Renderer, TPA Cover Letter & Evidence Bundle   |
|  6. Follow-up Agent   -> 30-Day IRDAI Deadline Monitor, Multi-Channel Reminders & Status Tracking |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                               Google Cloud Managed Infrastructure                                 |
|                                                                                                   |
|  * Vertex AI / Gemini API: Multimodal document OCR, vision extraction & AI Copilot reasoning      |
|  * Google Cloud Run: Serverless FastAPI container microservices                                   |
|  * Google Cloud Firestore: 11 Collections for state, facts, checklists, approvals & audit events |
|  * Google Cloud Storage: Encrypted vault for hospital bills, discharge summaries & policy PDFs    |
|  * Google Cloud Pub/Sub & Cloud Tasks: Asynchronous background worker queue & SLA reminders       |
|  * Google Secret Manager: DPDP encryption keys & provider credentials                             |
|  * Google Cloud Logging: Append-only immutable audit trail and telemetry                          |
+---------------------------------------------------------------------------------------------------+
```

---

## 📦 Data Model (11 Firestore Collections)

S.I.A. implements all 11 required collections:

1. **`users`**: User profile, employee ID, corporate group name, contact details.
2. **`claim_cases`**: Primary case entity with state, claimed amount, estimated reimbursement, and deadlines.
3. **`documents`**: Document metadata, SHA-256 hash, visual quality score, and storage paths.
4. **`extracted_facts`**: Structured key-value fields with confidence scores, source page numbers, and bounding boxes.
5. **`eligibility_assessments`**: Deterministic financial calculation with min/max range, basis, and exclusions.
6. **`evidence_checklists`**: Prioritized IRDAI evidence items, verification status, and actionable payload triggers.
7. **`drafted_claims`**: IRDAI claim form PDF path, insurer cover letter, and ready-to-dispatch emails.
8. **`approval_requests`**: Human digital signature, declaration statement, and approval timestamp.
9. **`agent_runs`**: Execution trace per agent (latency in ms, tokens consumed, tool calls, summary).
10. **`audit_events`**: Append-only audit trail logging every classification, calculation, and user action.
11. **`reminders`**: Multi-channel scheduled reminders (WhatsApp, Email, In-App) for 30-day filing deadline.

### Claim Case State Machine (11 States)
```
[DRAFT] -> [DOCUMENTS_UPLOADED] -> [PROCESSING]
                                         |
                                         +--> [ESCALATED_TO_HUMAN] (if risk > threshold)
                                         |
                                         +--> [NEEDS_USER_INFO] (if low confidence)
                                         |
                                         +--> [READY_FOR_REVIEW] -> [AWAITING_APPROVAL]
                                                                          |
                                                                          v
[RESOLVED] <-- [FOLLOW_UP_REQUIRED] <-- [SUBMITTED_MANUALLY] <------------+
     |                                         |
     v                                         v
 [REJECTED]                                [REJECTED]
```

---

## ⚖️ Exact Eligibility Assessment JSON Output

The Eligibility Agent strictly returns deterministic, structured JSON matching IRDAI guidelines:

```json
{
  "claim_case_id": "CLM-6D84B6",
  "eligibility_status": "likely_eligible",
  "confidence": 0.96,
  "estimated_reimbursement": {
    "currency": "INR",
    "minimum": 36540.00,
    "maximum": 38640.00,
    "basis": "Claim is within policy sum insured limit (₹50,000). Procedure 'Acute Appendicitis' is covered under Active Inpatient Care. Estimated non-medical consumable deductions (IRDAI Schedule 1 items like gloves, registration, kit) are ₹3,360. 0% co-pay applicable under employer corporate coverage.",
    "gross_claimed": 42000.00,
    "non_medical_deductions": 3360.00,
    "copay_amount": 0.00,
    "room_rent_penalty": 0.00
  },
  "supporting_evidence": [
    {
      "document_id": "doc_bill",
      "fact": "Hospital Final Bill totals Rs. 42,000.00 billed to patient Manpreet Kaur.",
      "source_page": 1,
      "confidence": 0.98
    },
    {
      "document_id": "doc_discharge",
      "fact": "Discharge summary confirms diagnosis 'Acute Appendicitis' with 48h active hospitalization.",
      "source_page": 1,
      "confidence": 0.97
    },
    {
      "document_id": "doc_policy",
      "fact": "Active Employer Health Policy #STAR-GHI-2024-9941 verified with corporate sum insured ceiling.",
      "source_page": 1,
      "confidence": 0.95
    }
  ],
  "missing_information": [
    "Itemized hospital billing breakup (pharmacy & OT consumable schedule) is required for full payout."
  ],
  "risks_or_exclusions": [
    "IRDAI Non-Payable items (gloves, sanitizer, admin charges) are excluded from reimbursement.",
    "Submission must be completed within 30 days of hospital discharge date."
  ],
  "next_best_action": "Obtain itemized pharmacy breakup from hospital, review drafted claim form, and provide final human signoff.",
  "human_review_required": true
}
```

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.10+
- Modern Web Browser (Chrome / Edge / Firefox)

### 2. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Run the Backend API
```bash
uvicorn main:app --reload --port 8000
```

### 4. Open the Web Dashboard
Open `frontend/index.html` directly in your browser or navigate to `http://localhost:8000` (FastAPI serves static frontend automatically).

### 5. Run Full Automated Test Suite
```bash
python backend/test_full_suite.py
```

---

## ☁️ Google Cloud Deployment Guide

### Deploying to Cloud Run & Firestore

```bash
# 1. Set Google Cloud Project & Region
gcloud config set project YOUR_GCP_PROJECT_ID
export REGION="asia-south1"

# 2. Enable Required Google Cloud APIs
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com

# 3. Create Firestore Database in Native Mode
gcloud firestore databases create --location=$REGION --type=firestore-native

# 4. Build and Deploy Backend to Cloud Run
gcloud run deploy sia-api \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID,GEMINI_API_KEY=YOUR_API_KEY"
```

---

## 🛡️ Trust & Safety Invariants

1. **Explicit Human Approval Gate:** S.I.A. will **never** submit a claim, sign a document, or email external parties without explicit human signoff and declaration acceptance.
2. **Deterministic Arithmetic:** Financial deductions follow deterministic IRDAI schedules and policy math — no LLM hallucinated sums.
3. **DPDP Act 2023 Shield:** Sensitive identifiers (Aadhaar, PAN, phone numbers) are masked at ingestion.
4. **NMC Doctor Verification:** Treating doctors are cross-checked against the National Medical Commission (NMC) registry.
5. **Full Observability:** Every agent run, latency measurement, confidence score, and tool call is recorded in an immutable append-only Firestore audit trail.

---

## 📄 License & Compliance
Built in compliance with IRDAI Health Insurance Regulations (2024) and Digital Personal Data Protection (DPDP) Act 2023.
