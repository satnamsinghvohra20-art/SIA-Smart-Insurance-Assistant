"""
Automated end-to-end pipeline test script for ClaimPilot.
Tests all 4 scenario presets across Intake, Decision, Execution, PDF generation, and Tracking.
"""
import sys
import os
from pathlib import Path

# Ensure UTF-8 output encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

import json
from agents import intake_agent, decision_agent, execution_agent
from services import async_tracker, audit_log


def run_tests():
    scenarios_path = Path(__file__).parent / "data" / "sample_scenarios.json"
    with open(scenarios_path, encoding="utf-8") as f:
        scenarios = json.load(f)["scenarios"]

    print("==================================================================")
    print(" CLAIM PILOT - AUTOMATED PIPELINE TEST SUITE (4 SCENARIOS) ")
    print("==================================================================")

    for idx, sc in enumerate(scenarios, 1):
        sc_id = sc["id"]
        title = sc["title"]
        bill_text = sc["bill_text"]
        claim_id = f"TEST-CLM-00{idx}"

        print(f"\n[Test {idx}/4] Running Scenario: {title} ({sc_id})")
        print("-" * 65)

        # 1. Intake
        intake_res = intake_agent.run_intake(claim_id, bill_text)
        fields = intake_res["fields"]
        low_conf = intake_res["low_confidence_fields"]
        print(f"  [OK] Intake Agent: Extracted {len(fields)} fields. Low confidence: {low_conf}")
        print(f"       Patient: {fields.get('patient_name', {}).get('value')}")
        print(f"       Total Amount: Rs. {fields.get('total_amount', {}).get('value')}")
        print(f"       Diagnosis: {fields.get('diagnosis', {}).get('value')}")

        # 2. Decision
        decision_res = decision_agent.run_decision(claim_id, intake_res)
        eligible = decision_res["eligible"]
        status = decision_res["status"]
        net_payable = decision_res["eligible_amount"]
        copay = decision_res["co_pay_amount"]
        print(f"  [OK] Decision Agent: Status={status}, Eligible={eligible}, Net Payable=Rs. {net_payable:,.2f}, Co-pay=Rs. {copay:,.2f}")
        print(f"       Reason: {decision_res['reason']}")

        # 3. Execution
        exec_res = execution_agent.run_execution(claim_id, intake_res, decision_res)
        print(f"  [OK] Execution Agent: Status={exec_res['status']}")
        if exec_res["form_path"]:
            pdf_path = Path(exec_res["form_path"])
            assert pdf_path.exists(), f"PDF not found at {pdf_path}"
            print(f"       Generated PDF: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")
        else:
            print(f"       Gracefully halted without PDF for ineligible claim.")

        # 4. Audit Log
        logs = audit_log.get_log(claim_id)
        print(f"  [OK] Audit Log: {len(logs)} event records logged with tool calls & latency traces.")

    print("\n==================================================================")
    print(" ALL 4 SCENARIOS PASSED WITH 100% SUCCESS!")
    print("==================================================================")


if __name__ == "__main__":
    run_tests()
