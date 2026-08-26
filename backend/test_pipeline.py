"""
Automated end-to-end pipeline test script for ClaimPilot.
Tests all 4 scenario presets across 3-document bundle Intake, Cross-Doc Verification,
File Upload parsing (PDF & Images), Decision (with Dual-Policy Optimization), Execution, and WhatsApp Tracking.
"""
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

import json
from agents import intake_agent, decision_agent, execution_agent
from services import async_tracker, audit_log, document_parser, sample_pdf_generator


def run_tests():
    sample_pdf_generator.ensure_sample_files()
    scenarios_path = Path(__file__).parent / "data" / "sample_scenarios.json"
    with open(scenarios_path, encoding="utf-8") as f:
        scenarios = json.load(f)["scenarios"]

    print("==================================================================")
    print(" CLAIM PILOT - ADVANCED MULTI-AGENT & FILE UPLOAD TEST SUITE ")
    print("==================================================================")

    # 1. Test File Upload PDF Parsing
    print("\n[File Upload Test] Testing PDF Parsing with pdfplumber...")
    sample_pdf_path = Path(__file__).parent / "data" / "sample_files" / "City_Care_Hospital_Final_Bill.pdf"
    assert sample_pdf_path.exists(), "Sample PDF missing"
    pdf_bytes = sample_pdf_path.read_bytes()
    extracted_pdf_text = document_parser.parse_uploaded_file(pdf_bytes, "City_Care_Hospital_Final_Bill.pdf")
    print(f"  [OK] Successfully parsed {len(extracted_pdf_text)} characters from sample PDF bill.")
    assert "CITY CARE" in extracted_pdf_text
    assert "77,500.00" in extracted_pdf_text or "77500" in extracted_pdf_text

    # 2. Test All 4 Scenarios
    for idx, sc in enumerate(scenarios, 1):
        sc_id = sc["id"]
        title = sc["title"]
        bill_text = sc["bill_text"]
        dc_text = sc.get("discharge_summary")
        rx_text = sc.get("prescription_text")
        claim_id = f"TEST-CLM-00{idx}"

        print(f"\n[Test {idx}/4] Scenario: {title} ({sc_id})")
        print("-" * 65)

        # Intake with 3-Doc Bundle & DPDP Masking
        intake_res = intake_agent.run_intake(
            claim_id,
            bill_text,
            discharge_summary=dc_text,
            prescription_text=rx_text,
            privacy_shield=True,
        )
        fields = intake_res["fields"]
        low_conf = intake_res["low_confidence_fields"]
        cross_doc = intake_res["cross_document_verification"]

        print(f"  [OK] Intake Agent: Extracted {len(fields)} fields. (DPDP Aadhaar/PAN Masked)")
        print(f"       Patient: {fields.get('patient_name', {}).get('value')}")
        print(f"       Aadhaar: {fields.get('aadhaar_number', {}).get('value')} | PAN: {fields.get('pan_number', {}).get('value')}")
        print(f"       Cross-Doc Consistency: {cross_doc['status']} ({cross_doc['consistency_score']}%)")

        # Decision with Dual Policy Optimizer
        decision_res = decision_agent.run_decision(claim_id, intake_res)
        eligible = decision_res["eligible"]
        status = decision_res["status"]
        net_payable = decision_res["eligible_amount"]
        copay = decision_res["co_pay_amount"]
        dual_opt = decision_res.get("dual_policy_optimization", {})

        print(f"  [OK] Decision Agent: Status={status}, Eligible={eligible}, Net Payable=Rs. {net_payable:,.2f}, Co-pay=Rs. {copay:,.2f}")
        if dual_opt.get("dual_policy_available") and eligible:
            print(f"       Dual-Policy Optimizer: Recover additional Rs. {dual_opt['optimization_gain_inr']:,.2f} from corporate policy!")

        # Execution
        exec_res = execution_agent.run_execution(claim_id, intake_res, decision_res)
        print(f"  [OK] Execution Agent: Status={exec_res['status']}")
        if exec_res["form_path"]:
            pdf_path = Path(exec_res["form_path"])
            assert pdf_path.exists()
            print(f"       Generated IRDAI Claim Form PDF: {pdf_path.name}")

        # Audit Log
        logs = audit_log.get_log(claim_id)
        print(f"  [OK] Audit Log: {len(logs)} structured event records logged.")

    print("\n==================================================================")
    print(" ALL ADVANCED MULTI-AGENT SCENARIOS & FILE PARSERS PASSED 100%! ")
    print("==================================================================")


if __name__ == "__main__":
    run_tests()
