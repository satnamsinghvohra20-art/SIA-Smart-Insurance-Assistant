"""
NABH HOSPITAL ACCREDITATION REGISTRY VERIFIER
--------------------------------------------
Validates hospital quality standards against National Accreditation Board for Hospitals &
Healthcare Providers (NABH - Quality Council of India) registry to ensure tariff compliance.
"""
from typing import Dict, Any, Optional

NABH_ACCREDITED_REGISTRY = {
    "APOLLO SPECIALITY HOSPITALS BANGALORE": {
        "nabh_id": "NABH-HSP-2021-0941",
        "accreditation_level": "FULL_NABH_ACCREDITED",
        "valid_until": "2027-12-31",
        "city": "Bangalore",
        "state": "Karnataka",
        "bed_capacity": 450,
        "quality_score": 98.4,
        "gipsa_ppn_network": True,
        "preferred_tpa_tariff": True
    },
    "FORTIS MEMORIAL RESEARCH INSTITUTE": {
        "nabh_id": "NABH-HSP-2020-0412",
        "accreditation_level": "FULL_NABH_ACCREDITED",
        "valid_until": "2026-09-30",
        "city": "Gurugram",
        "state": "Haryana",
        "bed_capacity": 300,
        "quality_score": 97.9,
        "gipsa_ppn_network": True,
        "preferred_tpa_tariff": True
    },
    "MAX SUPER SPECIALITY HOSPITAL SAKET": {
        "nabh_id": "NABH-HSP-2019-1120",
        "accreditation_level": "FULL_NABH_ACCREDITED",
        "valid_until": "2028-03-31",
        "city": "New Delhi",
        "state": "Delhi NCR",
        "bed_capacity": 500,
        "quality_score": 99.1,
        "gipsa_ppn_network": True,
        "preferred_tpa_tariff": True
    },
    "MANIPAL HOSPITAL OLD AIRPORT ROAD": {
        "nabh_id": "NABH-HSP-2022-0715",
        "accreditation_level": "FULL_NABH_ACCREDITED",
        "valid_until": "2027-06-30",
        "city": "Bangalore",
        "state": "Karnataka",
        "bed_capacity": 600,
        "quality_score": 98.8,
        "gipsa_ppn_network": True,
        "preferred_tpa_tariff": True
    },
    "NARAYANA INSTITUTE OF CARDIAC SCIENCES": {
        "nabh_id": "NABH-HSP-2021-0308",
        "accreditation_level": "FULL_NABH_ACCREDITED",
        "valid_until": "2026-11-30",
        "city": "Bangalore",
        "state": "Karnataka",
        "bed_capacity": 500,
        "quality_score": 99.5,
        "gipsa_ppn_network": True,
        "preferred_tpa_tariff": True
    },
    "CITY CARE HOSPITAL & RESEARCH CENTRE": {
        "nabh_id": "NABH-EL-2023-1490",
        "accreditation_level": "ENTRY_LEVEL_CERTIFIED",
        "valid_until": "2025-08-31",
        "city": "Bangalore",
        "state": "Karnataka",
        "bed_capacity": 80,
        "quality_score": 88.2,
        "gipsa_ppn_network": False,
        "preferred_tpa_tariff": False
    }
}


def verify_hospital_nabh(hospital_name: str) -> Dict[str, Any]:
    """
    Looks up hospital accreditation status by name or fuzzy matching.
    """
    clean_name = hospital_name.upper().strip()
    
    # Exact Match
    if clean_name in NABH_ACCREDITED_REGISTRY:
        info = NABH_ACCREDITED_REGISTRY[clean_name]
        return {
            "status": "VERIFIED_ACCREDITED",
            "hospital_name": hospital_name,
            **info
        }

    # Partial / Keyword Match
    for key, data in NABH_ACCREDITED_REGISTRY.items():
        if any(token in key for token in clean_name.split() if len(token) > 4):
            return {
                "status": "VERIFIED_ACCREDITED",
                "hospital_name": hospital_name,
                "matched_name": key,
                **data
            }

    # Fallback for unlisted nursing home / clinic
    return {
        "status": "NON_ACCREDITED_REGISTERED",
        "hospital_name": hospital_name,
        "nabh_id": "NOT_REGISTERED",
        "accreditation_level": "NON_ACCREDITED",
        "valid_until": None,
        "quality_score": 72.0,
        "gipsa_ppn_network": False,
        "preferred_tpa_tariff": False
    }
