# S.I.A. (Smart Insurance Assistant) — Multi-Agent Architecture & Specification

> **An autonomous 6-agent cognitive pipeline built on Google Cloud (Vertex AI, Cloud Run, Firestore, and Pub/Sub) designed to discover, verify, calculate, assemble, and track health insurance reimbursements under IRDAI and DPDP Act 2023 regulations.**

---

## ??? System Architecture Overview

```
                                  +------------------------------+
                                  ¦      UNSTRUCTURED INPUTS     ¦
                                  ¦ (PDF Bills, Summaries, Rx)   ¦
                                  +------------------------------+
                                                 ¦
                                                 ?
+-------------------------------------------------------------------------------------------------+
¦                                     S.I.A. 6-AGENT PIPELINE                                     ¦
¦                                                                                                 ¦
¦  1. INTAKE AGENT         2. SAFETY AGENT           3. ELIGIBILITY AGENT                         ¦
¦  +--------------------+  +----------------------+  +----------------------------------------+   ¦
¦  ¦ Gemini 3.5 Vision  ¦  ¦ DPDP 2023 Masking    ¦  ¦ 100% Deterministic Arithmetic Engine   ¦   ¦
¦  ¦ Doc Classification ¦  ¦ NMC Doctor Registry  ¦  ¦ IRDAI Non-Payables (Schedule 1)        ¦   ¦
¦  ¦ 14 Extracted Facts ¦  ¦ GIPSA Tariff Caps    ¦  ¦ Dual-Policy Split Optimizer            ¦   ¦
¦  ¦ Confidence Scoring ¦  ¦ SHA-256 Invoice Auth ¦  ¦ Minimum / Maximum Estimated Payout     ¦   ¦
¦  +--------------------+  +----------------------+  +----------------------------------------+   ¦
¦            ¦                        ¦                                  ¦                        ¦
¦            +------------------------+----------------------------------+                        ¦
¦                                     ?                                                           ¦
¦  4. EVIDENCE AGENT       5. CLAIM PREP AGENT       6. FOLLOW-UP AGENT                           ¦
¦  +--------------------+  +----------------------+  +----------------------------------------+   ¦
¦  ¦ Mandatory Checklists¦ ¦ IRDAI Form Part A/B  ¦  ¦ 30-Day Statutory Filing Countdown      ¦   ¦
¦  ¦ Missing Bill Audit ¦  ¦ TPA Cover Letter     ¦  ¦ 15-Day TPA Settlement SLA Benchmark    ¦   ¦
¦  ¦ 1-Click Email Draft¦  ¦ Explicit Human Gate  ¦  ¦ Multi-Channel Reminders (WhatsApp/SMS) ¦   ¦
¦  +--------------------+  +----------------------+  +----------------------------------------+   ¦
+-------------------------------------------------------------------------------------------------+
                                                 ¦
                                                 ?
                                  +------------------------------+
                                  ¦     DISPATCHED TO TPA        ¦
                                  ¦ (Pub/Sub Event + Cloud Run)  ¦
                                  +------------------------------+
```

---

## ?? Detailed Agent Responsibilities

### 1. Intake Agent (`backend/agents/intake_agent.py`)
* **Role:** Multimodal ingestion, OCR extraction, and document categorization.
* **Core Technology:** Google Gemini 3.5 Flash Multimodal Vision API + `pdfplumber` structured table parser.
* **Extracted Schema (14 Key Fields):**
  - `patient_name`, `admission_date`, `discharge_date`, `hospital_name`, `hospital_gstin`, `treating_doctor`, `doctor_reg_no`, `diagnosis`, `icd10_code`, `procedure_performed`, `total_bill_amount`, `room_rent_per_day`, `policy_number`, `abha_id`.
* **Clinical Cross-Consistency:** Validates diagnosis match between hospital tax invoice and inpatient discharge summary (98%+ consistency score).

---

### 2. Safety & Anti-Fraud Agent (`backend/agents/safety_agent.py`)
* **Role:** Regulatory compliance, PII redaction, and forensic anti-fraud checks.
* **DPDP Act 2023 Shield:** Anonymizes national identifiers at ingestion time (Aadhaar `XXXX-XXXX-8812`, PAN `ARXXXX510N`).
* **NMC Doctor Verification:** Cross-checks medical practitioner registration numbers against the National Medical Commission (NMC) and State Medical Council (SMC) databases.
* **GIPSA Fair Price Benchmarking:** Compares hospital line items against General Insurance Public Sector Association (GIPSA) Preferred Provider Network (PPN) schedules.
* **Cryptographic Provenance:** Computes SHA-256 hashes of all ingested files to prevent duplicate invoice re-submission.

---

### 3. Eligibility & Decision Agent (`backend/agents/eligibility_agent.py`)
* **Role:** Zero-hallucination, 100% deterministic rules-based underwriter math.
* **Why Deterministic?** Eliminates LLM financial hallucination risks. Code evaluates structured policy parameters against statutory IRDAI guidelines.
* **Core Adjudication Logic:**
  1. *Waiting Period Verification:* Checks active policy inception against general 30-day and 24-month Pre-Existing Disease (PED) rules.
  2. *Exclusion Filtering:* Evaluates aesthetic / cosmetic clauses (e.g., elective rhinoplasty).
  3. *IRDAI Non-Payables Deduction:* Automatically deducts non-medical consumables (gloves, PPE, administrative charges) per IRDAI Master Circular Schedule 1.
  4. *Co-Pay & Room Rent Sub-limit Computation:* Exact percentage arithmetic in INR.
  5. *Dual-Policy Split Optimizer:* Automatically routes residual co-pay balance to secondary corporate group insurance for 100% recovery.

---

### 4. Evidence Discovery Agent (`backend/agents/evidence_agent.py`)
* **Role:** Audit gap detection and hospital communication automation.
* **Mandatory IRDAI Checklist:** Validates required document bundle (Hospital Invoice, Itemized Bill, Discharge Summary, Doctor Prescription, Diagnostic Reports).
* **Missing Breakup Detection:** Identifies when hospitals provide lump-sum invoices missing pharmacy or surgical consumable itemizations.
* **1-Click Email Dispatch:** Generates formal, ready-to-send hospital billing emails with patient IP/Bill reference numbers.

---

### 5. Claim Preparation & Execution Agent (`backend/agents/claim_prep_agent.py`)
* **Role:** Document compilation and human-in-the-loop governance.
* **Artifact Generation:** Renders official **IRDAI Standard Mediclaim Reimbursement Claim Form (Part A & B)** in vector PDF format using ReportLab.
* **Explicit Human Gate Invariant:** S.I.A. **never** submits a claim or signs a document without explicit claimant digital authorization and legal declaration acceptance.
* **Digital Provenance Stamp:** Watermarks generated packages with SHA-256 verified signatures and timestamped approval logs.

---

### 6. Follow-up & SLA Agent (`backend/agents/follow_up_agent.py`)
* **Role:** Statutory timeline tracking and multi-channel claimant alerts.
* **IRDAI 30-Day Deadline Monitor:** Computes days remaining from hospital discharge to statutory filing expiration.
* **TPA 15-Day SLA Benchmark:** Tracks turnaround times against IRDAI Turnaround Time (TAT) mandates.
* **Scheduled Reminders:** Dispatches proactive alerts via simulated WhatsApp push notifications, Email, and In-App cards.

---

## ?? Conversational Copilot & Legal Dispute Agent
* **S.I.A. AI Copilot (`backend/services/copilot_service.py`):** Interactive conversational assistant powered by Google Gemini with live claim context.
* **Ombudsman Legal Appeal Generator (`backend/services/appeal_generator.py`):** Auto-drafts formal grievance petitions under **Section 45 of Insurance Act 1938** and **Rule 17 of Insurance Ombudsman Rules 2017** with mandatory 14-day resolution demand.

---

## ?? Firestore 11-Collection Ledger

| Collection | Schema Description |
|---|---|
| `users` | Policyholder profile, employee ID, corporate group info |
| `claim_cases` | Core claim state machine entity |
| `documents` | Ingested files, visual quality scores, SHA-256 hashes |
| `extracted_facts` | 14 structured clinical/financial facts with confidence |
| `eligibility_assessments` | Deterministic financial calculation with min/max range |
| `evidence_checklists` | Prioritized document requirements and gap status |
| `drafted_claims` | IRDAI Claim Form PDF path, cover letter, email drafts |
| `approval_requests` | Digital signature, legal declaration, approval timestamp |
| `agent_runs` | Per-agent execution trace (latency, tool calls, status) |
| `audit_events` | Append-only immutable regulatory audit trail |
| `reminders` | Multi-channel scheduled deadlines and SLA milestones |

---

## ??? Core Safety & Trust Invariants

1. **No Hallucinated Financial Calculations:** Financial arithmetic is 100% deterministic over structured policy rules.
2. **Explicit Human Gate:** Mandatory digital signoff required before external TPA dispatch.
3. **DPDP Act 2023 Compliance:** Automatic PII masking on sensitive identifiers.
4. **NMC Doctor Verification:** Doctor credential checks against national registries.
5. **Full Observability:** Immutable append-only audit trail for every agent run and tool call.
