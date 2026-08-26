"""
DOCTOR & MEDICAL PRACTITIONER VERIFICATION SERVICE
--------------------------------------------------
Verifies treating doctors against the National Medical Commission (NMC) of India,
State Medical Councils (MMC, DMC, KMC, etc.), and the Ayushman Bharat Healthcare
Professionals Registry (ABDM HPR).

WHY THIS MATTERS FOR HACKATHONS & INSURANCE:
  Fraudulent / fake medical bills with non-existent doctor registration numbers
  account for ~18% of fraudulent claims in India. ClaimPilot verifies every practitioner
  before claim approval.
"""
import json
import re
from pathlib import Path
from services.audit_log import log_event

REGISTRY_PATH = Path(__file__).parent.parent / "data" / "doctor_registry.json"


def load_doctor_registry() -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("practitioners", [])


def extract_doctor_reg_number(text: str) -> str | None:
    """Extracts medical council registration numbers using regex."""
    patterns = [
        r"(MMC[\s\-/]*\d{4}[\s\-/]*\d{2}[\s\-/]*\d{4})",
        r"(DMC[\s\-/]*R[\s\-/]*\d{4}[\s\-/]*\d{4})",
        r"(KMC[\s\-/]*\d{4}[\s\-/]*\d{2}[\s\-/]*\d{4})",
        r"(HNMC[\s\-/]*\d{4}[\s\-/]*\d{4})",
        r"Reg(?:istration)?\s*No:?\s*([A-Z0-9\-/]+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            clean = m.group(1).strip().replace(" ", "")
            return clean
    return None


def verify_doctor(
    doctor_name: str | None,
    reg_number: str | None = None,
    hospital_name: str | None = None,
    procedure_name: str | None = None,
    claim_id: str | None = None,
) -> dict:
    """Verifies a doctor against the National Medical Commission registry."""
    registry = load_doctor_registry()
    cleaned_name = (doctor_name or "").lower().replace(".", "").replace("dr", "").strip()

    matched_doc = None

    # 1. Match by registration number first if provided
    if reg_number:
        clean_reg = reg_number.upper().replace(" ", "").replace("-", "")
        for doc in registry:
            doc_reg = doc["reg_number"].upper().replace(" ", "").replace("-", "")
            if clean_reg == doc_reg or clean_reg in doc_reg:
                matched_doc = doc
                break

    # 2. Match by doctor name & aliases
    if not matched_doc and cleaned_name:
        for doc in registry:
            doc_name_clean = doc["doctor_name"].lower().replace(".", "").replace("dr", "").strip()
            if cleaned_name in doc_name_clean or doc_name_clean in cleaned_name:
                matched_doc = doc
                break
            for alias in doc.get("aliases", []):
                alias_clean = alias.lower().replace(".", "").replace("dr", "").strip()
                if cleaned_name in alias_clean or alias_clean in cleaned_name:
                    matched_doc = doc
                    break

    # If practitioner found in NMC registry
    if matched_doc:
        is_active = matched_doc.get("license_status") == "ACTIVE_VERIFIED" and matched_doc.get("good_standing", True)
        fraud_risk = "LOW" if is_active else "CRITICAL"

        # Check specialty alignment with procedure
        specialty = matched_doc.get("specialty", "")
        specialty_match = True
        if procedure_name:
            proc_lower = procedure_name.lower()
            if "rhinoplasty" in proc_lower and "plastic" not in specialty.lower() and "ent" not in specialty.lower():
                specialty_match = False
            elif "appendectomy" in proc_lower and "surgery" not in specialty.lower():
                specialty_match = False

        result = {
            "verified": is_active,
            "status": "NMC_VERIFIED" if is_active else "REVOKED_OR_FRAUDULENT",
            "doctor_name": matched_doc["doctor_name"],
            "reg_number": matched_doc["reg_number"],
            "medical_council": matched_doc["medical_council"],
            "nmc_uid": matched_doc["nmc_uid"],
            "hpr_id": matched_doc["hpr_id"],
            "qualifications": matched_doc["qualifications"],
            "specialty": specialty,
            "specialty_aligned": specialty_match,
            "associated_hospitals": matched_doc.get("associated_hospitals", []),
            "license_valid_upto": matched_doc.get("valid_upto"),
            "fraud_risk": fraud_risk,
            "verification_summary": (
                f"Active License confirmed with {matched_doc['medical_council']}. ABDM HPR Identity: {matched_doc['hpr_id']}."
                if is_active
                else f"CRITICAL: License status '{matched_doc.get('license_status')}' in NMC Registry. High fraud risk flagged."
            ),
        }
    else:
        # Doctor not in registry -> Unverified Practitioner
        result = {
            "verified": False,
            "status": "UNREGISTERED_PRACTITIONER",
            "doctor_name": doctor_name or "Unknown",
            "reg_number": reg_number or "NOT_FOUND",
            "medical_council": "Unverified Medical Council",
            "nmc_uid": "UNREGISTERED",
            "hpr_id": "NONE",
            "qualifications": ["Unverified"],
            "specialty": "Unspecified",
            "specialty_aligned": True,
            "associated_hospitals": [],
            "license_valid_upto": "UNKNOWN",
            "fraud_risk": "HIGH",
            "verification_summary": f"Doctor '{doctor_name}' (Reg: {reg_number or 'N/A'}) could not be verified in the National Medical Commission (NMC) Registry.",
        }

    if claim_id:
        log_event(
            claim_id,
            "intake_agent",
            "doctor_verified" if result["verified"] else "doctor_verification_failed",
            f"NMC Registry Verification: Doctor '{result['doctor_name']}' -> {result['status']} (Council: {result['medical_council']}, Reg: {result['reg_number']}).",
            tool_call="nmc_doctor_registry_verifier",
            payload=result,
        )

    return result
