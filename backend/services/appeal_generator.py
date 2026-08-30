"""
IRDAI LEGAL DISPUTE & GRIEVANCE APPEAL LETTER GENERATOR
-------------------------------------------------------
When a claim is rejected (e.g. exclusion ambiguity, missed window, or disputed co-pay),
S.I.A.'s Legal Agent auto-drafts a formal appeal petition to the Insurance Ombudsman
and TPA Grievance Officer citing IRDAI Protection of Policyholders' Interests Regulations 2024.
"""
from datetime import datetime


def generate_ombudsman_appeal_letter(
    claim_id: str,
    patient_name: str,
    policy_number: str,
    insurer_name: str,
    hospital_name: str,
    bill_amount: float,
    rejection_reason: str,
    clinical_diagnosis: str,
    procedure_performed: str,
) -> dict:
    """Drafts a formal, legally grounded IRDAI grievance letter for claimant appeal."""
    today_str = datetime.now().strftime("%d-%m-%Y")

    appeal_text = f"""FORMAL RECONSIDERATION & GRIEVANCE APPEAL PETITION
Under IRDAI (Protection of Policyholders' Interests) Regulations, 2024
Ref: Disputed Inpatient Mediclaim Reimbursement | Claim Ref: {claim_id}

Date: {today_str}

To,
The Grievance Redressal Officer / Chief Medical Underwriter
{insurer_name}
Subject: Formal Appeal against Claim Rejection / Dispute for Policy #{policy_number} (Patient: {patient_name})

Dear Grievance Redressal Team,

I am writing to formally contest the repudiation / deduction of Inpatient Health Insurance Claim #{claim_id} for treatment undergone at {hospital_name} from {today_str} regarding {procedure_performed} for {clinical_diagnosis}, amounting to Rs. {bill_amount:,.2f}.

1. GROUNDS OF CONTESTATION:
The repudiation ground stated: "{rejection_reason}" is inconsistent with IRDAI Master Circular on Health Insurance (Ref: IRDAI/HLT/REG/CIR/2024).

2. CLINICAL NECESSITY & DOCTOR CERTIFICATION:
As documented in the Inpatient Discharge Summary by the treating surgical consultant, the hospitalization was medically essential and emergency-indicated, precluding any elective exclusion clauses under Section 45 of the Insurance Act, 1938.

3. PRAYER & RELIEF SOUGHT:
In accordance with IRDAI Turnaround Time (TAT) mandates:
  a) Immediate medical re-adjudication of the claim package.
  b) Direct NEFT disbursement of the admissible sum of Rs. {bill_amount:,.2f} to claimant account.
  c) Escalation to the Office of the Insurance Ombudsman (Rule 17 of Insurance Ombudsman Rules, 2017) upon failure of resolution within 14 calendar days.

Attached Documents:
  [1] Certified Hospital Tax Invoice & Itemized Breakup
  [2] Signed Clinical Discharge Summary & Operative Notes
  [3] Registered Medical Practitioner (NMC) Verification Certificate
  [4] IRDAI Standard Form Part A & B Declaration

Claimant: {patient_name}
Policy Number: {policy_number}
Claim Reference: {claim_id}
Generated via S.I.A. (Smart Insurance Assistant) Autonomous Legal Subagent
"""

    return {
        "claim_id": claim_id,
        "appeal_subject": f"IRDAI Grievance Appeal — Claim #{claim_id} ({patient_name})",
        "legal_clauses_cited": [
            "IRDAI (Protection of Policyholders' Interests) Regulations, 2024",
            "Section 45 of Insurance Act, 1938 (Non-repudiability)",
            "Rule 17 of Insurance Ombudsman Rules, 2017 (14-Day Mandatory TAT)",
        ],
        "appeal_letter_text": appeal_text.strip(),
        "generated_date": today_str,
    }
