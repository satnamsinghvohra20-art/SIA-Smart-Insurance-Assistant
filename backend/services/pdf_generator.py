from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

GENERATED_DIR = Path(__file__).parent.parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

def generate_claim_pdf(claim_id: str, claim_data: dict) -> str:
    pdf_path = GENERATED_DIR / f"claim_form_{claim_id}.pdf"
    
    # Setup canvas
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    
    # Margin settings
    margin = 54 # 0.75 inch
    content_width = width - (2 * margin)
    
    # Title Header
    c.setFillColor(colors.HexColor("#0D1B2A"))
    c.rect(0, height - 80, width, 80, stroke=0, fill=1)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, height - 40, "S.I.A. INSURANCE ADJUDICATION PACKAGE")
    
    c.setFont("Helvetica", 10)
    c.drawString(margin, height - 58, f"IRDAI Standard Claim Submission — Form Part A & B | ID: {claim_id}")
    
    # Horizontal separator
    y = height - 100
    
    # Helper to draw sections
    def draw_section_header(title_text, curr_y):
        c.setFillColor(colors.HexColor("#1B263B"))
        c.rect(margin, curr_y - 20, content_width, 20, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin + 10, curr_y - 14, title_text)
        return curr_y - 35
        
    def draw_row(labels, values, curr_y):
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        # Left column
        c.drawString(margin + 10, curr_y, labels[0])
        c.setFont("Helvetica", 9)
        c.drawString(margin + 130, curr_y, str(values[0]))
        
        # Right column if present
        if len(labels) > 1:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(margin + 260, curr_y, labels[1])
            c.setFont("Helvetica", 9)
            c.drawString(margin + 380, curr_y, str(values[1]))
            
        return curr_y - 15

    # Section 1: Patient Profile & Policy Details (IRDAI Part A)
    y = draw_section_header("PART A: CLAIMANT & POLICY HOLDER DETAILS", y)
    profile = claim_data.get("patient_profile", {})
    y = draw_row(["Patient Name:", "ABHA ID:"], [profile.get("patient_name", "N/A"), profile.get("abha_id", "N/A")], y)
    y = draw_row(["Aadhaar ID:", "Policy Number:"], [profile.get("aadhaar_masked", "N/A"), profile.get("policy_number", "N/A")], y)
    y = draw_row(["Insurer Name:", "Adjudication Date:"], [profile.get("insurer_name", "N/A"), datetime.now().strftime("%Y-%m-%d")], y)
    
    y -= 10
    
    # Section 2: Clinical Summary (IRDAI Part B)
    y = draw_section_header("PART B: HOSPITALIZATION & CLINICAL SUMMARY", y)
    clinical = claim_data.get("clinical_summary", {})
    y = draw_row(["Hospital Name:", "Hospital GSTIN:"], [clinical.get("hospital_name", "N/A"), clinical.get("hospital_gstin", "N/A")], y)
    y = draw_row(["Treating Doctor:", "Doctor SMC Reg No:"], [clinical.get("treating_doctor", "N/A"), clinical.get("doctor_reg_no", "N/A")], y)
    
    doctor_status = "VERIFIED (NMC/SMC Registry)" if clinical.get("doctor_verified") else "UNVERIFIED"
    y = draw_row(["Doctor Reg Status:", "Admission Date:"], [doctor_status, clinical.get("admission_date", "N/A")], y)
    y = draw_row(["Discharge Date:", "Diagnosis (ICD-10):"], [clinical.get("discharge_date", "N/A"), f"{clinical.get('diagnosis', 'N/A')} ({clinical.get('icd10_code', 'N/A')})"], y)
    y = draw_row(["Procedure Performed:", "Statutory Filing Window:"], [clinical.get("procedure_performed", "N/A"), "30 Days (IRDAI Master Circular)"], y)

    y -= 10

    # Section 3: Financial Calculations & Adjudication Detail
    y = draw_section_header("PART C: FINANCIAL MATH & ELIGIBILITY DETAILS", y)
    financial = claim_data.get("financial_adjudication", {})
    
    y = draw_row(["Gross Claimed:", "Policy Sum Insured:"], [f"INR {financial.get('gross_claimed_amount', 0.0):,.2f}", f"INR {financial.get('policy_sum_insured', 0.0):,.2f}"], y)
    y = draw_row(["Non-Medical Deductions:", "Co-pay Percent Applied:"], [f"INR {financial.get('non_medical_deductions', 0.0):,.2f}", f"{financial.get('applicable_copay_percent', 0.0)}%"], y)
    y = draw_row(["Co-pay Deduction Amount:", "Net Approved Payout:"], [f"INR {financial.get('copay_deduction_amount', 0.0):,.2f}", f"INR {financial.get('net_approved_payout', 0.0):,.2f}"], y)
    y = draw_row(["Min Estimated Payout:", "GIPSA Tariff Benchmarking:"], [f"INR {financial.get('min_estimated_payout', 0.0):,.2f}", financial.get("gipsa_tariff_status", "N/A")], y)

    # Itemized Breakdown Table
    y -= 10
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#415A77"))
    c.rect(margin, y - 18, content_width, 18, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.drawString(margin + 10, y - 12, "Item Category")
    c.drawRightString(margin + 200, y - 12, "Billed (INR)")
    c.drawRightString(margin + 320, y - 12, "Payable (INR)")
    c.drawString(margin + 340, y - 12, "Reason / Remarks")
    
    y -= 18
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    
    for item in financial.get("itemized_breakdown", []):
        y -= 12
        c.drawString(margin + 10, y, item.get("category", "N/A"))
        c.drawRightString(margin + 200, y, f"{item.get('billed', 0.0):,.2f}")
        c.drawRightString(margin + 320, y, f"{item.get('payable', 0.0):,.2f}")
        c.drawString(margin + 340, y, item.get("deduction_reason", "none"))
        
        # Border under row
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)
        c.line(margin, y - 2, margin + content_width, y - 2)

    # Compliance & SLA details
    y -= 25
    y = draw_section_header("PART D: EVIDENCE STATUS & STATUTORY COMPLIANCE", y)
    evidence = claim_data.get("evidence_audit", {})
    statutory = claim_data.get("statutory_compliance", {})
    
    days_rem = statutory.get("days_remaining_to_file", 0)
    deadline_status = f"{days_rem} days remaining" if days_rem >= 0 else f"EXCEEDED BY {abs(days_rem)} DAYS (Appeal Needed)"
    y = draw_row(["Checklist Status:", "Filing Time Remaining:"], [evidence.get("checklist_status", "N/A"), deadline_status], y)
    y = draw_row(["Documents Verified:", "DPDP PII Protection Status:"], [", ".join(evidence.get("documents_verified", [])), "ACTIVE (Aadhaar/PAN Masked)"], y)

    # Signatures
    y -= 35
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    
    c.line(margin + 20, y, margin + 150, y)
    c.line(margin + 300, y, margin + 430, y)
    
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin + 45, y - 10, "Claimant Signature")
    c.drawString(margin + 310, y - 10, "Treating Doctor / Hospital Seal")
    
    # Save PDF
    c.showPage()
    c.save()
    return str(pdf_path)
