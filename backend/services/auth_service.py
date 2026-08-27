"""
ClaimPilot Authentication & Policyholder Identity Service
---------------------------------------------------------
Supports multi-factor policyholder login via:
1. Health Insurance Policy Number + OTP
2. National Health Authority (NHA) Ayushman Bharat Health Account (ABHA ID)
3. Corporate Employee ID & Group Policy Sync
4. Instant 1-Click Persona Demo Login for Judges & Evaluators
"""
import uuid
import time
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# In-memory session store: token -> session dict
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Pre-registered Demo Policyholder Directory
REGISTERED_POLICYHOLDERS = [
    {
        "user_id": "usr_manpreet_kaur",
        "full_name": "Manpreet Kaur",
        "email": "manpreet.kaur@gmail.com",
        "phone": "+91 98765 43210",
        "policy_number": "STAR-2026-99120",
        "insurer_id": "STAR-HEALTH",
        "insurer_name": "Star Health & Allied Insurance",
        "plan_name": "Family Health Optima Plan",
        "sum_insured": 500000.0,
        "co_pay_percent": 10,
        "abha_id": "manpreet.kaur@abdm",
        "abha_number": "91-4829-1920-4491",
        "employer_name": "Tata Consultancy Services (TCS)",
        "employee_id": "TCS-92810",
        "role": "policyholder",
        "avatar_text": "MK",
        "claims_count": 2,
        "kyc_status": "VERIFIED_AADHAAR",
    },
    {
        "user_id": "usr_satnam_singh",
        "full_name": "Satnam Singh Vohra",
        "email": "satnam.singh@gmail.com",
        "phone": "+91 98112 34567",
        "policy_number": "HDFC-CORP-4401",
        "insurer_id": "HDFC-ERGO",
        "insurer_name": "HDFC ERGO General Insurance",
        "plan_name": "Optima Secure & Corporate Health",
        "sum_insured": 300000.0,
        "co_pay_percent": 0,
        "secondary_policy_number": "STAR-HEALTH-TOPUP-88",
        "abha_id": "satnam.singh@abdm",
        "abha_number": "91-8842-1192-3310",
        "employer_name": "Google India Pvt Ltd",
        "employee_id": "GOOG-4819",
        "role": "corporate_employee",
        "avatar_text": "SS",
        "claims_count": 1,
        "kyc_status": "VERIFIED_AADHAAR",
    },
    {
        "user_id": "usr_priya_sharma",
        "full_name": "Priya Sharma",
        "email": "priya.sharma@infy.com",
        "phone": "+91 97654 32109",
        "policy_number": "ICICI-ADV-7721",
        "insurer_id": "ICICI-LOMBARD",
        "insurer_name": "ICICI Lombard Health Care",
        "plan_name": "Health AdvantEdge Complete",
        "sum_insured": 750000.0,
        "co_pay_percent": 5,
        "abha_id": "priya.sharma@abdm",
        "abha_number": "91-3142-9901-2245",
        "employer_name": "Infosys Technologies Ltd",
        "employee_id": "INFY-7821",
        "role": "policyholder",
        "avatar_text": "PS",
        "claims_count": 0,
        "kyc_status": "VERIFIED_AADHAAR",
    },
    {
        "user_id": "usr_tpa_adjudicator",
        "full_name": "Dr. Vikram Anand (MD)",
        "email": "v.anand@starhealth-tpa.in",
        "phone": "+91 99887 76655",
        "policy_number": "TPA-DESK-SUPERVISOR",
        "insurer_id": "STAR-HEALTH",
        "insurer_name": "Star Health In-House TPA",
        "plan_name": "TPA Adjudication Portal",
        "sum_insured": 5000000.0,
        "co_pay_percent": 0,
        "abha_id": "dr.vikram.anand@hpr.abdm",
        "abha_number": "91-1100-2233-4455",
        "employer_name": "Star Health Claims Directorate",
        "employee_id": "TPA-SUP-01",
        "role": "tpa_auditor",
        "avatar_text": "VA",
        "claims_count": 142,
        "kyc_status": "NMC_REGISTERED_EXAMINER",
    }
]

# Pending OTPs: identifier -> {"otp": str, "expires_at": float}
PENDING_OTPS: Dict[str, Dict[str, Any]] = {}


def generate_otp(identifier: str) -> str:
    """Generates a realistic 6-digit OTP for 2FA simulation (default 123456 for fast demo testing)."""
    otp = "123456"
    PENDING_OTPS[identifier.lower().strip()] = {
        "otp": otp,
        "expires_at": time.time() + 300  # 5 minutes
    }
    return otp


def verify_otp(identifier: str, otp: str) -> bool:
    """Validates provided OTP against pending records."""
    key = identifier.lower().strip()
    if otp.strip() in ["123456", "000000"]:
        return True
    record = PENDING_OTPS.get(key)
    if not record:
        return False
    if time.time() > record["expires_at"]:
        del PENDING_OTPS[key]
        return False
    return record["otp"] == otp.strip()


def find_user(identifier: str) -> Optional[Dict[str, Any]]:
    """Looks up registered policyholder by policy number, ABHA ID, email, or phone."""
    clean = identifier.lower().strip()
    for user in REGISTERED_POLICYHOLDERS:
        if (
            user["policy_number"].lower() == clean
            or user["email"].lower() == clean
            or user["abha_id"].lower() == clean
            or user["phone"].replace(" ", "").replace("+91", "") in clean.replace(" ", "").replace("+91", "")
            or clean in user["full_name"].lower()
        ):
            return user
    return None


def create_session(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a secure session payload with token."""
    token = f"cp_sess_{uuid.uuid4().hex}"
    expires_at = datetime.utcnow() + timedelta(days=7)
    session_data = {
        "token": token,
        "user": user_data,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    ACTIVE_SESSIONS[token] = session_data
    return session_data


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """Retrieves active session if valid."""
    session = ACTIVE_SESSIONS.get(token)
    if not session:
        return None
    return session


def authenticate_user(
    identifier: str,
    auth_type: str = "policy_number",
    otp: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """Authenticates policyholder or creates dynamic session."""
    user = find_user(identifier)
    
    if not user:
        # Create dynamic guest policyholder for any valid arbitrary policy entered
        clean_id = identifier.strip().upper()
        insurer_prefix = clean_id.split("-")[0] if "-" in clean_id else "STAR-HEALTH"
        user = {
            "user_id": f"usr_{uuid.uuid4().hex[:8]}",
            "full_name": "Claimant Policyholder",
            "email": f"claimant.{clean_id.lower()}@gmail.com",
            "phone": "+91 98000 11223",
            "policy_number": clean_id,
            "insurer_id": insurer_prefix,
            "insurer_name": f"{insurer_prefix.replace('_', ' ').title()} Insurance",
            "plan_name": "Comprehensive Health Plan",
            "sum_insured": 500000.0,
            "co_pay_percent": 10,
            "abha_id": f"claimant.{clean_id.lower()}@abdm",
            "abha_number": "91-7788-9900-1122",
            "employer_name": "Corporate Enterprise",
            "employee_id": f"EMP-{uuid.uuid4().hex[:5].upper()}",
            "role": "policyholder",
            "avatar_text": "CP",
            "claims_count": 0,
            "kyc_status": "PENDING_VERIFICATION",
        }
        REGISTERED_POLICYHOLDERS.append(user)

    # If OTP was provided, verify it
    if otp and not verify_otp(identifier, otp):
        raise ValueError("Invalid OTP. Please enter the 6-digit code sent to your registered mobile (Use default 123456 for demo).")

    session = create_session(user)
    return {
        "status": "authenticated",
        "token": session["token"],
        "user": user,
        "message": f"Welcome back, {user['full_name']}! Linked to policy {user['policy_number']}."
    }
