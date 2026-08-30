"""
DENIAL & QUERY PREDICTOR AGENT
------------------------------
Predicts potential TPA claim queries, audit disputes, and repudiation risks before submission.
Calculates a Denial Probability Score (0-100%) and generates actionable 1-click prescriptive fixes.
"""
from typing import Dict, Any, List
from datetime import datetime
from services.audit_log import log_event
from services.firestore_service import db


def predict_denial_risk(claim_case_id: str) -> Dict[str, Any]:
    """
    Evaluates evidence checklist, extracted facts, eligibility math, and doctor credentials
    to predict potential TPA rejection triggers and output a proactive mitigation plan.
    """
    facts = db.get_extracted_facts(claim_case_id) or []
    facts_dict = {f["key"]: f.get("value") for f in facts} if isinstance(facts, list) else {}
    evidence = db.get_evidence_checklist(claim_case_id) or {}
    eligibility = db.get_eligibility_assessment(claim_case_id) or {}

    risk_factors: List[Dict[str, Any]] = []
    prescriptive_fixes: List[Dict[str, Any]] = []
    penalty_points = 0

    # 1. Check Missing Itemized Pharmacy / Consumables
    missing_items = [i for i in evidence.get("items", []) if i.get("status") == "MISSING"]
    if any("Itemized" in i.get("title", "") for i in missing_items):
        penalty_points += 35
        risk_factors.append({
            "code": "MISSING_ITEMIZED_BILL",
            "severity": "HIGH",
            "message": "Hospital tax invoice lacks itemized pharmacy and consumable unit-rate breakdown.",
            "impact": "+35% risk of TPA administrative query delay."
        })
        prescriptive_fixes.append({
            "action_id": "auto_email_hospital",
            "title": "Dispatch Pre-composed Email to Hospital Billing Desk",
            "description": "Auto-requests unit-price pharmacy summary from hospital billing.",
            "status": "READY"
        })

    # 2. Check Doctor Registry Status
    doctor_reg = facts_dict.get("treating_doctor_reg_no") or facts_dict.get("doctor_reg_no")
    if not doctor_reg or "TEMP" in str(doctor_reg):
        penalty_points += 25
        risk_factors.append({
            "code": "UNVERIFIED_DOCTOR_REG",
            "severity": "MEDIUM",
            "message": "Treating surgeon NMC/SMC registration credential requires official registry verification.",
            "impact": "+25% risk of pre-auth qualification dispute."
        })
        prescriptive_fixes.append({
            "action_id": "verify_nmc_registry",
            "title": "Fetch Live NMC & ABDM HPR Verification Seal",
            "description": "Attaches active State Medical Council certificate to claim bundle.",
            "status": "READY"
        })

    # 3. Check Policy Exclusions
    exclusions = eligibility.get("risks_or_exclusions", [])
    if exclusions:
        penalty_points += 40
        risk_factors.append({
            "code": "EXCLUSION_CLAUSE_DETECTED",
            "severity": "CRITICAL",
            "message": f"Procedure matches policy exclusion clause: {', '.join(exclusions)}.",
            "impact": "+40% risk of total claim repudiation."
        })
        prescriptive_fixes.append({
            "action_id": "draft_ombudsman_appeal",
            "title": "Pre-draft Ombudsman Appeal under Section 45",
            "description": "Generates emergency clinical necessity petition citing IRDAI Regulations 2024.",
            "status": "READY"
        })

    # 4. Check Filing Window Remaining
    reminders = db.get_reminders(claim_case_id) or []
    for rem in reminders:
        if rem.get("days_remaining", 30) < 5:
            penalty_points += 20
            risk_factors.append({
                "code": "FILING_WINDOW_EXPIRING",
                "severity": "HIGH",
                "message": f"Statutory 30-day IRDAI filing deadline expires in {rem.get('days_remaining')} days.",
                "impact": "+20% risk of time-bar rejection."
            })
            prescriptive_fixes.append({
                "action_id": "instant_tpa_dispatch",
                "title": "One-Click Emergency Priority TPA Dispatch",
                "description": "Dispatches complete package via Pub/Sub priority queue.",
                "status": "READY"
            })

    denial_probability = min(max(penalty_points, 1.2), 98.0)
    admissibility_health_score = round(100.0 - denial_probability, 1)

    if denial_probability < 15.0:
        overall_risk = "LOW_RISK"
        verdict = "Audit-Ready: High probability of first-pass zero-query settlement."
    elif denial_probability < 50.0:
        overall_risk = "MODERATE_RISK"
        verdict = "Action Recommended: Resolve missing itemized breakdown to prevent TPA delay."
    else:
        overall_risk = "HIGH_RISK"
        verdict = "Attention Required: Review exclusion clauses and attach doctor credentials before submission."

    result = {
        "claim_case_id": claim_case_id,
        "denial_probability_percent": round(denial_probability, 1),
        "admissibility_health_score": admissibility_health_score,
        "overall_risk_level": overall_risk,
        "verdict_summary": verdict,
        "risk_factors": risk_factors,
        "prescriptive_fixes": prescriptive_fixes,
        "evaluated_at": datetime.utcnow().isoformat() + "Z"
    }

    log_event(
        claim_case_id,
        "denial_predictor_agent",
        "denial_risk_evaluated",
        f"Denial Probability: {result['denial_probability_percent']}% | Health Score: {admissibility_health_score}/100 ({overall_risk})",
        tool_call="evaluate_tpa_query_triggers",
        payload={"denial_probability": result["denial_probability_percent"], "risk_count": len(risk_factors)}
    )

    return result
