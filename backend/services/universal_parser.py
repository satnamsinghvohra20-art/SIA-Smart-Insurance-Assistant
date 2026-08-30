"""
UNIVERSAL DYNAMIC DOCUMENT PARSER & LIVE EXTRACTION ENGINE
-----------------------------------------------------------
Performs real-time multimodal entity extraction on ANY real-world hospital bill,
discharge summary, prescription, or lab report without hardcoded mocks.
Prioritizes live Google Gemini API extraction and falls back to dynamic regex extraction.
"""
import re
from datetime import datetime
from services.gemini_extractor import extract_with_gemini_live, is_gemini_configured


def parse_any_medical_document(text: str) -> dict:
    """Extracts structured clinical and financial fields dynamically from raw document text."""
    fields = {}

    def set_field(k, val, conf=0.92):
        fields[k] = {"value": val, "confidence": conf, "source": "live_extractor"}

    # 0. Try Live Gemini Extraction first if configured
    if is_gemini_configured():
        try:
            gemini_data = extract_with_gemini_live(text)
            if gemini_data and isinstance(gemini_data, dict):
                for k, v in gemini_data.items():
                    if v is not None and str(v).strip() and str(v).lower() != "null":
                        set_field(k, v, 0.98)
                        if k == "total_bill_amount":
                            set_field("total_amount", v, 0.98)
                        elif k == "total_amount":
                            set_field("total_bill_amount", v, 0.98)
                if len(fields) >= 4:
                    if "total_bill_amount" in fields and "total_amount" not in fields:
                        fields["total_amount"] = fields["total_bill_amount"]
                    if "total_amount" in fields and "total_bill_amount" not in fields:
                        fields["total_bill_amount"] = fields["total_amount"]
                    return fields
        except Exception:
            pass

    # 1. Hospital Name Extraction
    hosp_match = re.search(
        r"([A-Z0-9\s,\.\-&]{4,50}(?:HOSPITAL|HEALTHCARE|MEDICAL CENTRE|NURSING HOME|CLINIC|INSTITUTE|FOUNDATION|CARE|MEDICARE))",
        text,
        re.IGNORECASE,
    )
    if hosp_match:
        raw_hosp = hosp_match.group(1).strip().title()
        clean_hosp = raw_hosp.split("\n")[0].strip()
        set_field("hospital_name", clean_hosp, 0.95)
    else:
        lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 3]
        if lines:
            set_field("hospital_name", lines[0].title(), 0.80)
        else:
            set_field("hospital_name", None, 0.40)

    # 2. Patient Name Extraction
    pat_match = re.search(
        r"(?:Patient(?:\s+Name)?|Name\s+of\s+Patient|Pt\.?\s+Name|Claimant\s+Name|Name)[:\s]+(?:Mr\.?|Ms\.?|Mrs\.?|Master)?\s*([A-Za-z\s]{3,35})(?:\n|\s{2,}|Age|Gender|\||\(|\/|UHID|IPD)",
        text,
        re.IGNORECASE,
    )
    if pat_match:
        set_field("patient_name", pat_match.group(1).strip().title(), 0.96)
    else:
        sal_match = re.search(r"\b(?:Mr\.?|Mrs\.?|Ms\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", text)
        if sal_match:
            set_field("patient_name", sal_match.group(1).strip().title(), 0.88)
        else:
            set_field("patient_name", None, 0.40)

    # 3. Total Amount Extraction
    amt_patterns = [
        r"(?:TOTAL\s+(?:INPATIENT\s+)?(?:BILL\s+)?AMOUNT|NET\s+(?:PAYABLE|AMOUNT)|GRAND\s+TOTAL|FINAL\s+BILL\s+AMOUNT|TOTAL\s+CHARGES|AMOUNT\s+PAID|TOTAL)[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
        r"(?:Total|Payable|Billed)[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
        r"(?:Rs\.?|INR|₹)\s*([\d,]{3,10}(?:\.\d{2})?)",
    ]
    total_val = None
    for p in amt_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw_amt = m.group(1).replace(",", "").strip()
            try:
                parsed_val = float(raw_amt)
                if parsed_val > 100:
                    total_val = parsed_val
                    break
            except ValueError:
                continue

    if total_val:
        set_field("total_amount", total_val, 0.96)
        set_field("total_bill_amount", total_val, 0.96)
    else:
        set_field("total_amount", None, 0.40)
        set_field("total_bill_amount", None, 0.40)

    # 4. Aadhaar & PAN Extraction
    aadh_match = re.search(r"(?:Aadhaar(?:\s+No)?|UIDAI)[:\s]+([\d\-\sX]{12,16})", text, re.IGNORECASE)
    if aadh_match:
        set_field("aadhaar_number", aadh_match.group(1).strip(), 0.98)
    else:
        gen_aadh = re.search(r"\b(\d{4}[-\s]\d{4}[-\s]\d{4})\b", text)
        if gen_aadh:
            set_field("aadhaar_number", gen_aadh.group(1).strip(), 0.90)
        else:
            set_field("aadhaar_number", None, 0.40)

    pan_match = re.search(r"\b([A-Z]{5}\d{4}[A-Z])\b", text)
    if pan_match:
        set_field("pan_number", pan_match.group(1).strip(), 0.98)
    else:
        set_field("pan_number", None, 0.40)

    # 5. Dates
    adm_match = re.search(
        r"(?:DOA|Date\s+of\s+Admission|Admission\s+Date)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        text,
        re.IGNORECASE,
    )
    if adm_match:
        set_field("admission_date", adm_match.group(1).strip(), 0.95)
    else:
        set_field("admission_date", None, 0.40)

    dis_match = re.search(
        r"(?:DOD|Date\s+of\s+Discharge|Discharge\s+Date)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        text,
        re.IGNORECASE,
    )
    if dis_match:
        set_field("discharge_date", dis_match.group(1).strip(), 0.95)
    else:
        set_field("discharge_date", None, 0.40)

    # 6. Diagnosis & Procedure
    diag_match = re.search(
        r"(?:Diagnosis|Final\s+Diagnosis|Clinical\s+Impression|Provisional\s+Diagnosis)[:\s]+([^\n\r\|]{4,80})",
        text,
        re.IGNORECASE,
    )
    if diag_match:
        set_field("diagnosis", diag_match.group(1).strip(), 0.92)
    else:
        set_field("diagnosis", None, 0.40)

    proc_match = re.search(
        r"(?:Procedure|Surgery|Operation\s+Done|Intervention)[:\s]+([^\n\r\|]{4,80})",
        text,
        re.IGNORECASE,
    )
    if proc_match:
        set_field("procedure_performed", proc_match.group(1).strip(), 0.92)
    else:
        set_field("procedure_performed", None, 0.40)

    # 7. Doctor & Reg No
    doc_match = re.search(
        r"(?:Doctor|Dr\.?|Consultant|Surgeon)[:\s]+([A-Za-z\s\.]{3,35})(?:,|\(|$|\n)",
        text,
        re.IGNORECASE,
    )
    if doc_match:
        doc_name = doc_match.group(1).strip()
        if not doc_name.lower().startswith("dr"):
            doc_name = "Dr. " + doc_name
        set_field("treating_doctor", doc_name, 0.93)
    else:
        set_field("treating_doctor", None, 0.40)

    reg_match = re.search(
        r"(?:Reg\.?\s*No|Registration\s*No|MMC|DMC|KMC|SMC)[:\s]+([A-Z0-9\-\/]{4,20})",
        text,
        re.IGNORECASE,
    )
    if reg_match:
        set_field("doctor_reg_no", reg_match.group(1).strip(), 0.95)
        set_field("treating_doctor_reg_no", reg_match.group(1).strip(), 0.95)
    else:
        set_field("doctor_reg_no", None, 0.40)
        set_field("treating_doctor_reg_no", None, 0.40)

    # 8. Policy Number
    pol_match = re.search(
        r"(?:Policy\s*(?:No|Number|\#)|Insurance\s*ID)[:\s]+([A-Z0-9\-\/]{6,25})",
        text,
        re.IGNORECASE,
    )
    if pol_match:
        set_field("policy_number", pol_match.group(1).strip(), 0.95)
    else:
        set_field("policy_number", None, 0.40)

    # Dual mapping guarantee
    if "total_bill_amount" in fields and "total_amount" not in fields:
        fields["total_amount"] = fields["total_bill_amount"]
    if "total_amount" in fields and "total_bill_amount" not in fields:
        fields["total_bill_amount"] = fields["total_amount"]

    return fields


class UniversalMedicalParser:
    def parse_text(self, text: str) -> dict:
        return parse_any_medical_document(text)

    def parse_document(self, text: str) -> dict:
        return parse_any_medical_document(text)

    def parse(self, text: str) -> dict:
        return parse_any_medical_document(text)

    @staticmethod
    def parse_static(text: str) -> dict:
        return parse_any_medical_document(text)
