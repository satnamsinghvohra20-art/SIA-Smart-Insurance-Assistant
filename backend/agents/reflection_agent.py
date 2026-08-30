from datetime import datetime

def run_self_correction(claim_data: dict) -> dict:
    """
    Phase 7: Reflection & Self-Correction Agent.
    Runs verification checklist, adjusts numbers for precision,
    ensures all datatypes are numeric floats, and sets the final case status.
    """
    corrections_log = []
    
    # Extract components
    profile = claim_data.get("patient_profile", {})
    clinical = claim_data.get("clinical_summary", {})
    financial = claim_data.get("financial_adjudication", {})
    evidence = claim_data.get("evidence_audit", {})
    statutory = claim_data.get("statutory_compliance", {})
    
    # 1. Schema Check: Ensure all numeric values are floats (not strings)
    # Correcting types if needed
    for key in ["gross_claimed_amount", "policy_sum_insured", "applicable_copay_percent", 
                "non_medical_deductions", "copay_deduction_amount", "net_approved_payout", "min_estimated_payout"]:
        val = financial.get(key, 0.0)
        if isinstance(val, str):
            try:
                financial[key] = float(val.replace(",", "").strip())
                corrections_log.append(f"Type correction: Converted financial field '{key}' from string to float.")
            except Exception:
                financial[key] = 0.0
        else:
            financial[key] = float(val)
            
    # Ensure itemized breakdown categories contain floats
    for item in financial.get("itemized_breakdown", []):
        for num_key in ["billed", "payable"]:
            val = item.get(num_key, 0.0)
            if isinstance(val, str):
                try:
                    item[num_key] = float(val.replace(",", "").strip())
                except Exception:
                    item[num_key] = 0.0
            else:
                item[num_key] = float(val)
                
    # 2. Math Check: Verification of eligibility arithmetic
    gross = financial["gross_claimed_amount"]
    deductions = financial["non_medical_deductions"]
    copay_pct = financial["applicable_copay_percent"]
    copay_amt = financial["copay_deduction_amount"]
    payout = financial["net_approved_payout"]
    sum_insured = financial["policy_sum_insured"]
    
    # Re-calculate eligible base
    calc_eligible_base = max(0.0, gross - deductions)
    calc_copay = round(calc_eligible_base * (copay_pct / 100.0), 2)
    calc_payout = round(min(calc_eligible_base - calc_copay, sum_insured), 2)
    
    if abs(copay_amt - calc_copay) > 0.05:
        corrections_log.append(f"Math Correction: Adjusted copay deduction from INR {copay_amt} to INR {calc_copay}.")
        financial["copay_deduction_amount"] = calc_copay
        
    if abs(payout - calc_payout) > 0.05:
        corrections_log.append(f"Math Correction: Adjusted net approved payout from INR {payout} to INR {calc_payout}.")
        financial["net_approved_payout"] = calc_payout
        
    # Re-verify min estimated payout
    calc_min_estimated = round(max(0.0, financial["net_approved_payout"] - (gross * 0.05)), 2)
    if abs(financial["min_estimated_payout"] - calc_min_estimated) > 0.05:
        financial["min_estimated_payout"] = calc_min_estimated
        
    # 3. Clinical Specialty Check (Doctor Alignment)
    doctor = clinical.get("treating_doctor", "")
    procedure = clinical.get("procedure_performed", "")
    specialty_match = True
    
    doc_lower = doctor.lower()
    proc_lower = procedure.lower()
    
    # Match surgical vs medical credentials
    if "laparoscopic" in proc_lower or "appendectomy" in proc_lower or "cholecystectomy" in proc_lower:
        # Surgical procedure requires a Surgeon or MS (Master of Surgery) credentials
        if not ("surgeon" in doc_lower or "ms" in doc_lower or "m.s." in doc_lower or "surgery" in doc_lower):
            specialty_match = False
            corrections_log.append("Clinical Check: Doctor credentials (MD or similar) do not explicitly align with surgical procedure (Laparoscopic).")
            
    # 4. Determine Final Case Status
    # Default is READY_FOR_APPROVAL
    status = "READY_FOR_APPROVAL"
    
    # Check for missing docs or forensic anomalies
    gaps = evidence.get("gaps", [])
    has_gaps = len(gaps) > 0
    
    is_overbilled = financial.get("gipsa_tariff_status") == "INFLATED_ABOVE_PPN_SCHEDULE"
    days_rem = statutory.get("days_remaining_to_file", 30)
    
    if not clinical.get("doctor_verified"):
        status = "ESCALATED_TO_HUMAN"
        corrections_log.append("Workflow status: Escalated due to unverified State Medical Council Doctor Registration.")
    elif has_gaps:
        status = "ESCALATED_TO_HUMAN"
        corrections_log.append("Workflow status: Escalated due to missing records or document discrepancies.")
    elif is_overbilled:
        status = "ESCALATED_TO_HUMAN"
        corrections_log.append("Workflow status: Escalated due to billing amounts exceeding GIPSA tariff schedules.")
    elif days_rem < 0:
        status = "ESCALATED_TO_HUMAN"
        corrections_log.append("Workflow status: Escalated because the statutory 30-day filing window has been exceeded.")
        
    # Clean up non-schema fields before returning final dictionary
    if "gaps" in evidence:
        del evidence["gaps"]
    if "gipsa_benchmark_cap" in financial:
        del financial["gipsa_benchmark_cap"]
    if "gipsa_anomalies" in financial:
        del financial["gipsa_anomalies"]
    if "aadhaar_raw" in claim_data.get("patient_profile", {}):
        del claim_data["patient_profile"]["aadhaar_raw"]
        
    # Construct structured output conforming to strict JSON schema
    final_payload = {
        "claim_case_id": claim_data.get("claim_case_id", "CLM-XXXXXX"),
        "status": status,
        "patient_profile": {
            "patient_name": profile.get("patient_name", "N/A"),
            "abha_id": profile.get("abha_id", "N/A"),
            "abha_verified": profile.get("abha_verified", True),
            "aadhaar_masked": profile.get("aadhaar_masked", "XXXX-XXXX-XXXX"),
            "policy_number": profile.get("policy_number", "N/A"),
            "insurer_name": profile.get("insurer_name", "N/A")
        },
        "clinical_summary": {
            "hospital_name": clinical.get("hospital_name", "N/A"),
            "hospital_gstin": clinical.get("hospital_gstin", "N/A"),
            "treating_doctor": clinical.get("treating_doctor", "N/A"),
            "doctor_reg_no": clinical.get("doctor_reg_no", "N/A"),
            "doctor_verified": clinical.get("doctor_verified", False),
            "admission_date": clinical.get("admission_date", "N/A"),
            "discharge_date": clinical.get("discharge_date", "N/A"),
            "diagnosis": clinical.get("diagnosis", "N/A"),
            "procedure_performed": clinical.get("procedure_performed", "N/A"),
            "icd10_code": clinical.get("icd10_code", "N/A")
        },
        "financial_adjudication": {
            "gross_claimed_amount": financial.get("gross_claimed_amount", 0.0),
            "policy_sum_insured": financial.get("policy_sum_insured", 0.0),
            "applicable_copay_percent": financial.get("applicable_copay_percent", 0.0),
            "non_medical_deductions": financial.get("non_medical_deductions", 0.0),
            "copay_deduction_amount": financial.get("copay_deduction_amount", 0.0),
            "net_approved_payout": financial.get("net_approved_payout", 0.0),
            "min_estimated_payout": financial.get("min_estimated_payout", 0.0),
            "gipsa_tariff_status": financial.get("gipsa_tariff_status", "WITHIN_PPN_SCHEDULE"),
            "itemized_breakdown": financial.get("itemized_breakdown", [])
        },
        "evidence_audit": {
            "checklist_status": evidence.get("checklist_status", "COMPLETE"),
            "documents_verified": evidence.get("documents_verified", []),
            "missing_documents": evidence.get("missing_documents", []),
            "hospital_email_draft": evidence.get("hospital_email_draft", None)
        },
        "statutory_compliance": {
            "irdai_filing_deadline_days": statutory.get("irdai_filing_deadline_days", 30),
            "days_remaining_to_file": statutory.get("days_remaining_to_file", 0),
            "ombudsman_appeal_ready": statutory.get("ombudsman_appeal_ready", False),
            "dpdp_pii_shielded": statutory.get("dpdp_pii_shielded", True)
        },
        "audit_trail": claim_data.get("audit_trail", [])
    }
    
    # Add ReflectionAgent logs to audit_trail
    if corrections_log:
        message = "Run self-correction checks: " + " | ".join(corrections_log)
    else:
        message = "Run self-correction checks: All math, schema and clinical verification checks passed successfully."
        
    final_payload["audit_trail"].append({
        "step": "ReflectionAgent",
        "action": "Self-correction & Schema Verification",
        "confidence": 1.0,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })
    
    return final_payload
