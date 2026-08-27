# ClaimPilot: 3-Minute Live Demo Presentation Script

## Overview
**Problem:** Indian employees lose over ₹18,000 Crores annually in unclaimed or clerical rejected health insurance reimbursements due to complex policies, missing itemized billing breakdowns, and cumbersome paperwork.
**Solution:** ClaimPilot — an autonomous, multi-agent AI system built on Google Cloud (Gemini 3.5, Cloud Run, Firestore, Pub/Sub) that discovers, verifies, prepares, and tracks eligible medical claims with strict human-in-the-loop safety gates.

---

## 3-Minute Demo Timeline

### ⏱️ [0:00 - 0:45] Minute 1: The Problem & Ingestion (Intake + Safety Agents)
- **Speaker:** *"Welcome to ClaimPilot. Let's look at a common, high-impact scenario: an Indian corporate employee undergoing emergency surgery (appendectomy) at an in-network hospital."*
- **Action:** Click **⚡ 1-Click Demo Scenario 1 (₹42,000 Claim)** or drag-and-drop the 4 documents:
  1. Hospital Bill (₹42,000)
  2. Hospital Discharge Summary
  3. Employer Group Health Insurance Policy (₹50,000 annual limit)
  4. Employee Insurance Health Card
- **Behind the Scenes:**
  - **Intake Agent (Gemini 3.5)** classifies all 4 documents and extracts structured entities (patient name, hospital, dates, diagnosis, doctor registration MMC-2012-08-2910, gross bill ₹42,000) with page citations.
  - **Safety Agent** verifies the treating doctor against the National Medical Commission (NMC) registry, activates India's DPDP Act 2023 privacy shield (masking Aadhaar/PAN), benchmarks tariffs against GIPSA schedules, and verifies SHA-256 invoice uniqueness.
- **Visual Highlight:** Point out the live 6-agent progress rail turning green and the extracted facts grid showing 98% confidence and source citations.

---

### ⏱️ [0:45 - 1:45] Minute 2: Deterministic Reasoning & Evidence Discovery (Eligibility + Evidence Agents)
- **Speaker:** *"Unlike probabilistic chatbots that hallucinate financial figures, ClaimPilot uses a deterministic rules engine aligned with IRDAI guidelines."*
- **Visual Highlight:**
  - **Eligibility Assessment Card:** Show that the claim is marked **LIKELY ELIGIBLE**.
  - **Financial Math:** Gross Bill: ₹42,000 | IRDAI Non-Payable Consumables (Schedule 1: PPE, sanitization kit): -₹3,360 | Corporate Co-pay: 0% | **Estimated Approved Payout: ₹38,640**.
  - **Evidence Agent Audit:** The agent scans the hospital bill and detects that an **Itemized Pharmacy & OT Consumables Breakup** is missing.
- **Action:**
  - Click **✉️ Request from Hospital** in the Evidence Checklist.
  - Show the pre-composed, formal email draft to `billing@apollohospitals.demo`.
  - Click **🚀 Dispatch Email to Hospital** to trigger the event.
  - Show the append-only activity timeline updating in real time.

---

### ⏱️ [1:45 - 2:30] Minute 3: Human Review, Approval Gate, & IRDAI Claim Form PDF
- **Speaker:** *"ClaimPilot enforces a strict safety invariant: the system never submits a legally binding claim or signs paperwork without explicit human approval."*
- **Visual Highlight:**
  - Point to the **🛡️ Human Review & Approval Gate**.
  - Check the declaration box: *"I confirm that the extracted facts and medical receipts are accurate."*
  - Click **✍️ Approve & Submit Claim**.
  - Show the claim state transition from `READY_FOR_REVIEW` to `SUBMITTED_MANUALLY`.
- **Action:**
  - Click **⬇️ Download PDF** to preview the generated official IRDAI Standard Reimbursement Form (Part A & B) with cover letter.
  - Show the **Scheduled Reminders** card displaying the 30-day IRDAI filing countdown and 15-day TPA SLA benchmark.

---

### ⏱️ [2:30 - 3:00] Wrap-up: Extensibility & Google Cloud Architecture
- **Speaker:** *"ClaimPilot is architected on Google Cloud using serverless Cloud Run microservices, 11 Firestore collections, Pub/Sub asynchronous queues, and Gemini 3.5. While starting with Indian health insurance, its multi-agent architecture is ready for government benefits, flight delays, warranty claims, and tax refunds."*
- **Visual Highlight:** Open **📊 TPA Analytics** modal to show the enterprise ROI: ₹3.48 Cr recovered, average adjudication time reduced from 45 mins to 2.4 mins, and 98%+ pass rate.

---

## Key Safety Controls to Emphasize
1. **No Hallucinated Math:** Financial figures use deterministic arithmetic.
2. **Explicit Human Gate:** Mandatory digital signoff required before external dispatch.
3. **DPDP 2023 Compliance:** Automatic PII masking.
4. **Fraud & Forensic Defense:** NMC doctor registry check & SHA-256 duplicate invoice check.
5. **Observability:** Complete append-only audit trail for every agent run and tool call.
