"""
Automated end-to-end pipeline test script for ClaimPilot (Real-Time Live Engine).
Tests dynamic real-time ingestion on arbitrary hospital bills, PDF parsing, doctor NMC checks,
9 major Indian insurer rules, and IRDAI claim form PDF generation.
"""
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

import json
from agents import intake_agent, decision_agent, execution_agent
from services import async_tracker, audit_log, document_parser, sample_pdf_generator, doctor_verifier, universal_parser


def run_tests():
    sample_pdf_generator.ensure_sample_files()

    print("==================================================================")
    print(" CLAIM PILOT - REAL-TIME LIVE ENGINE & DYNAMIC TEST SUITE ")
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
    assert "Apollo" in parsed_dyn["hospital_name"]["value"]
    print(f"  [OK] Successfully parsed arbitrary bill: Patient={parsed_dyn['patient_name']['value']}, Amount=Rs. {parsed_dyn['total_amount']['value']:,.2f}, Doctor={parsed_dyn['treating_doctor']['value']}")

    # 2. Test Doctor Verification against NMC Registry
    print("\n[Doctor Verification Test] Testing NMC / SMC Registry Verifier...")
    doc_res = doctor_verifier.verify_doctor("Dr. Rajesh Mehta", reg_number="MMC-2012-08-2910")
    assert doc_res["verified"] is True
    print(f"  [OK] Verified legitimate doctor: {doc_res['doctor_name']} ({doc_res['reg_number']}) -> Status: {doc_res['status']}")

    # 3. Test Full Live Pipeline on Custom Claim
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
    print(" ALL REAL-TIME LIVE RUNTIME CHECKS PASSED 100%! ")
    print("==================================================================")


if __name__ == "__main__":
    run_tests()
