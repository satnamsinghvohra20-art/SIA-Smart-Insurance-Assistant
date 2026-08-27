"""
GIPSA / PPN STANDARDIZED PACKAGE RATE & TARIFF BENCHMARK ENGINE
--------------------------------------------------------------
Benchmarks inpatient hospital billing against GIPSA (General Insurance Public
Sector Association) and PPN (Preferred Provider Network) standardized package rates
for Tier-1, Tier-2, and Tier-3 Indian cities (IRDAI Master Circular 2024).
"""

# Standardized GIPSA PPN benchmark surgical tariffs (INR)
GIPSA_PPN_SCHEDULES = {
    "laparoscopic appendectomy": {
        "tier1_benchmark": 75000.0,
        "tier2_benchmark": 60000.0,
        "tier3_benchmark": 48000.0,
        "max_allowable_room_rent_pct": 1.0,
        "standard_stay_days": 3,
    },
    "laparoscopic cholecystectomy": {
        "tier1_benchmark": 110000.0,
        "tier2_benchmark": 88000.0,
        "tier3_benchmark": 70000.0,
        "max_allowable_room_rent_pct": 1.0,
        "standard_stay_days": 3,
    },
    "total knee replacement": {
        "tier1_benchmark": 210000.0,
        "tier2_benchmark": 175000.0,
        "tier3_benchmark": 140000.0,
        "max_allowable_room_rent_pct": 1.0,
        "standard_stay_days": 5,
    },
    "cataract surgery": {
        "tier1_benchmark": 38000.0,
        "tier2_benchmark": 30000.0,
        "tier3_benchmark": 24000.0,
        "max_allowable_room_rent_pct": 1.0,
        "standard_stay_days": 1,
    },
    "normal delivery": {
        "tier1_benchmark": 55000.0,
        "tier2_benchmark": 42000.0,
        "tier3_benchmark": 35000.0,
        "max_allowable_room_rent_pct": 1.0,
        "standard_stay_days": 3,
    },
}


def benchmark_hospital_tariff(procedure: str, billed_amount: float, city_tier: str = "Tier-1") -> dict:
    """Compares billed amount with GIPSA PPN tariff schedule."""
    proc_clean = (procedure or "laparoscopic appendectomy").lower()
    matched_schedule = None

    for k, v in GIPSA_PPN_SCHEDULES.items():
        if k in proc_clean or any(word in proc_clean for word in k.split() if len(word) > 4):
            matched_schedule = v
            break

    if not matched_schedule:
        matched_schedule = GIPSA_PPN_SCHEDULES["laparoscopic appendectomy"]

    benchmark_cap = matched_schedule.get("tier1_benchmark", 75000.0)
    if "tier2" in city_tier.lower() or "tier-2" in city_tier.lower():
        benchmark_cap = matched_schedule.get("tier2_benchmark", 60000.0)
    elif "tier3" in city_tier.lower() or "tier-3" in city_tier.lower():
        benchmark_cap = matched_schedule.get("tier3_benchmark", 48000.0)

    diff = billed_amount - benchmark_cap
    within_gipsa = billed_amount <= (benchmark_cap * 1.15)  # 15% reasonable variance buffer

    return {
        "procedure": procedure or "Laparoscopic Appendectomy",
        "city_tier": city_tier,
        "billed_amount": billed_amount,
        "gipsa_ppn_benchmark_rate": benchmark_cap,
        "variance_amount": round(diff, 2),
        "variance_pct": round((diff / benchmark_cap) * 100.0, 1),
        "is_within_fair_tariff": within_gipsa,
        "tariff_verdict": "FAIR_MARKET_TARIFF" if within_gipsa else "INFLATED_ABOVE_PPN_SCHEDULE",
        "admissibility_recommendation": f"Billed charges (₹{billed_amount:,.2f}) align with GIPSA PPN {city_tier} tariff schedule (Cap: ₹{benchmark_cap:,.2f})."
        if within_gipsa
        else f"Billed amount exceeds GIPSA PPN benchmark by ₹{diff:,.2f} ({round((diff / benchmark_cap) * 100.0, 1)}%). Subject to package tariff ceiling.",
    }
