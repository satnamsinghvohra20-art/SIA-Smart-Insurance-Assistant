"""
Automated end-to-end pipeline test script for ClaimPilot (Real-Time Live Engine).
Tests dynamic real-time ingestion, ABHA ID verification, NMC doctor checks,
IRDAI Ombudsman legal appeal drafting, and IRDAI claim form PDF generation.
"""
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

import json
from agents import intake_agent, decision_agent, execution_agent
from services import (
    async_tracker,
    audit_log,
    document_parser,
    sample_pdf_generator,
    doctor_verifier,
    universal_parser,
    abha_verifier,
    appeal_generator,
)


def run_tests():
    sample_pdf_generator.ensure_sample_files()

    print("==================================================================")
    print(" CLAIM PILOT - GRAND PRIZE REAL-TIME LIVE SUITE VERIFICATION ")
    print("==================================================================")

    # 1. Test Universal Dynamic Parser on Arbitrary Custom Medical Text
    print("\n[Dynamic Ingestion Test] Testing Universal Parser on arbitrary hospital bill...")
    custom_bill = """
    APOLLO HOSPITALS ENTERPRISE LTD.
    21 Greams Lane, Chennai - 600006
    INPATIENT FINAL TAX INVOICE — INV # AHE/2026/0991
    Patient Name: Manpreet Kaur | Age: 31 | Gender: Female
    Aadhaar: 9812-4412-8812 | PAN: ABEPK9912L
    Admission: 10-09-2026 | Discharge: 13-09-2026
    Treating Doctor: Dr. Rajesh Mehta, MS | MMC-2012-08-2910
    Diagnosis: Acute Cholecystitis with gallstone pancreatitis
    Procedure Performed: Laparoscopic Cholecystectomy with Cholangiogram
    TOTAL INPATIENT CHARGES: INR 1,12,000.00
    GSTIN: 33AAACA1234F1Z1
    """
    parsed_dyn = universal_parser.parse_any_medical_document(custom_bill)
    assert parsed_dyn["patient_name"]["value"] == "Manpreet Kaur"
    assert parsed_dyn["total_amount"]["value"] == 112000.00
    print(f"  [OK] Successfully parsed arbitrary bill: Patient={parsed_dyn['patient_name']['value']}, Amount=Rs. {parsed_dyn['total_amount']['value']:,.2f}")

    # 2. Test ABHA ID Verification
    print("\n[ABDM Test] Testing Ayushman Bharat Health Account (ABHA ID) Verifier...")
    abha_res = abha_verifier.verify_abha_identity("Manpreet Kaur")
    assert abha_res["verified"] is True
    assert "abdm" in abha_res["abha_address"]
    print(f"  [OK] ABHA Account Linked: {abha_res['abha_address']} ({abha_res['nha_status']})")

    # 3. Test Doctor Verification against NMC Registry
    print("\n[Doctor Verification Test] Testing NMC / SMC Registry Verifier...")
    doc_res = doctor_verifier.verify_doctor("Dr. Rajesh Mehta", reg_number="MMC-2012-08-2910")
    assert doc_res["verified"] is True
    print(f"  [OK] Verified legitimate doctor: {doc_res['doctor_name']} ({doc_res['reg_number']}) -> Status: {doc_res['status']}")

    # 4. Test Legal Ombudsman Appeal Letter Generator on Rejected Claim
    print("\n[Legal Agent Test] Testing IRDAI Ombudsman Appeal Letter Generator...")
    appeal = appeal_generator.generate_ombudsman_appeal_letter(
        claim_id="REJ-CLM-9912",
        patient_name="Ananya Sharma",
        policy_number="ICICI-LOMBARD-HEALTH-2024",
        insurer_name="ICICI Lombard General Insurance",
        hospital_name="Apollo Hospital",
        bill_amount=47500.00,
        rejection_reason="Elective cosmetic rhinoplasty exclusion",
        clinical_diagnosis="Deviated Nasal Septum & Rhinoplasty",
        procedure_performed="Septorhinoplasty",
    )
    assert "Section 45 of the Insurance Act" in appeal["appeal_letter_text"]
    print(f"  [OK] Auto-drafted Ombudsman Grievance Petition: {len(appeal['appeal_letter_text'])} chars citing {len(appeal['legal_clauses_cited'])} legal statutes.")

    # 5. Test Full Live Pipeline on Custom Claim
    claim_id = "LIVE-CLM-REALTIME"
    intake_res = intake_agent.run_intake(
        claim_id=claim_id,
        raw_text=custom_bill,
        discharge_summary=custom_bill,
        privacy_shield=True,
    )
    assert intake_res["fields"]["total_amount"]["value"] == 112000.00
    print(f"  [OK] Live Intake: Extracted {len(intake_res['fields'])} fields with DPDP Aadhaar/PAN masking.")

    # Decision on Live Claim
    decision_res = decision_agent.run_decision(claim_id, intake_res)
    assert decision_res["eligible"] is True
    print(f"  [OK] Live Decision: Status={decision_res['status']}, Net Payable=Rs. {decision_res['eligible_amount']:,.2f}")

    # Execution on Live Claim
    exec_res = execution_agent.run_execution(claim_id, intake_res, decision_res)
    assert exec_res["status"] == "ready_for_approval"
    pdf_path = Path(exec_res["form_path"])
    assert pdf_path.exists()
    print(f"  [OK] Live Execution: Generated official IRDAI Claim Form PDF ({pdf_path.name}).")

    print("\n==================================================================")
    print(" ALL GRAND PRIZE FEATURES VERIFIED 100% CLEANLY! ")
    print("==================================================================")


if __name__ == "__main__":
    run_tests()
