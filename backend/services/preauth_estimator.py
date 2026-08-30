"""
PRE-ADMISSION HOSPITAL COST & OUT-OF-POCKET ESTIMATOR
----------------------------------------------------
Calculates expected hospitalization expenses, GIPSA tariff caps,
room rent proportionate deduction penalties, and patient out-of-pocket exposure before admission.
"""
from typing import Dict, Any

PROCEDURE_TARIFF_BENCHMARKS = {
    "appendectomy": {
        "title": "Laparoscopic Appendectomy",
        "ppn_package_rate": 45000.0,
        "standard_hospital_rate": 60000.0,
        "consumable_estimate": 3500.0,
        "recommended_stay_days": 2
    },
    "cataract": {
        "title": "Phacoemulsification Cataract Surgery with Foldable IOL",
        "ppn_package_rate": 35000.0,
        "standard_hospital_rate": 48000.0,
        "consumable_estimate": 2000.0,
        "recommended_stay_days": 1
    },
    "knee_replacement": {
        "title": "Total Knee Replacement (Unilateral)",
        "ppn_package_rate": 185000.0,
        "standard_hospital_rate": 240000.0,
        "consumable_estimate": 15000.0,
        "recommended_stay_days": 4
    },
    "cholecystectomy": {
        "title": "Laparoscopic Cholecystectomy (Gallbladder Removal)",
        "ppn_package_rate": 55000.0,
        "standard_hospital_rate": 75000.0,
        "consumable_estimate": 4500.0,
        "recommended_stay_days": 2
    },
    "hernia": {
        "title": "Laparoscopic Inguinal Hernia Mesh Repair",
        "ppn_package_rate": 48000.0,
        "standard_hospital_rate": 65000.0,
        "consumable_estimate": 4000.0,
        "recommended_stay_days": 2
    },
    "dengue": {
        "title": "Dengue Inpatient Management & Platelet Transfusion",
        "ppn_package_rate": 28000.0,
        "standard_hospital_rate": 38000.0,
        "consumable_estimate": 2500.0,
        "recommended_stay_days": 3
    }
}

ROOM_RATES_BY_CATEGORY = {
    "general_ward": 1500.0,
    "twin_sharing": 3500.0,
    "single_private": 7500.0,
    "deluxe_suite": 15000.0
}


def estimate_preauth_costs(
    procedure_key: str,
    room_category: str,
    sum_insured: float = 500000.0,
    policy_room_rent_cap: float = 5000.0,
    co_pay_percent: float = 0.0,
    is_network_hospital: bool = True
) -> Dict[str, Any]:
    """
    Simulates pre-hospitalization cost adjudication and flags room rent proportionate deductions.
    """
    proc = PROCEDURE_TARIFF_BENCHMARKS.get(procedure_key.lower(), PROCEDURE_TARIFF_BENCHMARKS["appendectomy"])
    actual_room_rate = ROOM_RATES_BY_CATEGORY.get(room_category.lower(), 7500.0)
    stay_days = proc["recommended_stay_days"]

    # Calculate Room Rent Excess & Proportionate Deduction Ratio
    proportionate_ratio = 1.0
    room_rent_penalty = 0.0
    if actual_room_rate > policy_room_rent_cap:
        proportionate_ratio = round(policy_room_rent_cap / actual_room_rate, 3)
        # Proportionate deduction applies to associated medical charges (approx 65% of bill)
        associated_charges = proc["standard_hospital_rate"] * 0.65
        room_rent_penalty = round(associated_charges * (1.0 - proportionate_ratio), 2)

    gross_estimate = proc["standard_hospital_rate"] + (actual_room_rate * stay_days)
    consumables = proc["consumable_estimate"]
    
    # Net Admissible
    admissible_base = max(gross_estimate - consumables - room_rent_penalty, 0.0)
    copay_amount = round(admissible_base * (co_pay_percent / 100.0), 2)
    expected_insurance_payout = max(round(admissible_base - copay_amount, 2), 0.0)
    expected_patient_copay = round(gross_estimate - expected_insurance_payout, 2)

    tips = []
    if actual_room_rate > policy_room_rent_cap:
        tips.append(
            f"⚠️ Room Rent Alert: Choosing '{room_category.replace('_', ' ').title()}' (₹{actual_room_rate:,.0f}/day) exceeds policy cap (₹{policy_room_rent_cap:,.0f}/day). "
            f"This triggers an estimated ₹{room_rent_penalty:,.0f} proportionate deduction penalty on surgeon & nursing charges."
        )
        tips.append("💡 Recommendation: Opting for 'Twin Sharing' keeps your room within the cap and eliminates the proportionate deduction!")
    else:
        tips.append("✅ Room category is within your policy limit. Zero proportionate room penalty will be applied.")

    if not is_network_hospital:
        tips.append("⚠️ Non-Network Hospital: Reimbursement filing required post-discharge within 30 days under IRDAI guidelines.")

    return {
        "procedure": proc["title"],
        "room_category": room_category,
        "stay_days": stay_days,
        "gross_hospital_estimate": gross_estimate,
        "gipsa_ppn_benchmark_rate": proc["ppn_package_rate"],
        "non_payable_consumables": consumables,
        "proportionate_room_rent_penalty": room_rent_penalty,
        "co_pay_deduction": copay_amount,
        "expected_insurance_payout": expected_insurance_payout,
        "expected_patient_out_of_pocket": expected_patient_copay,
        "coverage_percentage": round((expected_insurance_payout / gross_estimate) * 100.0, 1),
        "guidance_tips": tips
    }
