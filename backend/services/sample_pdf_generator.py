"""
Script to pre-generate realistic sample PDF bills and discharge summaries for drag-and-drop testing.
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample_files"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def generate_sample_bill_pdf() -> str:
    path = SAMPLE_DIR / "City_Care_Hospital_Final_Bill.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    # Hospital Header
    c.setFillColor(colors.HexColor("#0D1B2A"))
    c.rect(0, height - 35 * mm, width, 35 * mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#4CC3B0"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(18 * mm, height - 15 * mm, "CITY CARE MULTISPECIALITY HOSPITAL")

    c.setFillColor(colors.HexColor("#E0E1DD"))
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, height - 22 * mm, "201, Linking Road, Bandra West, Mumbai - 400050 | GSTIN: 27ABCDE1234F1Z5")
    c.drawString(18 * mm, height - 28 * mm, "TAX INVOICE / FINAL INPATIENT REIMBURSEMENT BILL — BILL NO: CCH/2026/08/1147")

    y = height - 45 * mm

    def draw_heading(text):
        nonlocal y
        c.setFillColor(colors.HexColor("#1B263B"))
        c.rect(16 * mm, y - 2 * mm, width - 32 * mm, 6 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(19 * mm, y, text)
        y -= 8 * mm

    def draw_field(label1, val1, label2, val2):
        nonlocal y
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#415A77"))
        c.drawString(18 * mm, y, f"{label1}:")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#0D1B2A"))
        c.drawString(52 * mm, y, str(val1))

        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#415A77"))
        c.drawString(108 * mm, y, f"{label2}:")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#0D1B2A"))
        c.drawString(142 * mm, y, str(val2))
        y -= 6 * mm

    draw_heading("PATIENT & ADMISSION PARTICULARS")
    draw_field("Patient Name", "Satnam Singh", "Age / Gender", "27 Y / Male")
    draw_field("Aadhaar Number", "8492-4910-3321", "PAN Card", "ABCPS1290K")
    draw_field("Admission Date", "14-08-2026 (10:30 AM)", "Discharge Date", "17-08-2026 (02:00 PM)")
    draw_field("Treating Doctor", "Dr. Rajesh Mehta, MS", "Policy Number", "STAR-HEALTH-FAMILY-2024")
    draw_field("Clinical Diagnosis", "Acute Appendicitis (K35.80)", "Procedure", "Laparoscopic Appendectomy")
    y -= 3 * mm

    draw_heading("ITEMIZED CHARGES BREAKUP (INR)")

    items = [
        ("1. Room Rent & Nursing (3 nights @ Rs 3,500/night)", "10,500.00"),
        ("2. Laparoscopic Surgery OT & Surgeon Charges", "32,000.00"),
        ("3. Anaesthetist & Monitored Sedation Care", "8,000.00"),
        ("4. Laboratory Investigations (CBC, LFT, USG Abdomen)", "7,200.00"),
        ("5. Inpatient Pharmacy & Surgical Consumables", "16,800.00"),
        ("6. Post-op Dressing & Hospital Services", "3,000.00"),
    ]

    for item_name, item_amt in items:
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#1B263B"))
        c.drawString(18 * mm, y, item_name)
        c.drawRightString(width - 20 * mm, y, f"Rs. {item_amt}")
        y -= 5.5 * mm

    # Total Box
    y -= 2 * mm
    c.setStrokeColor(colors.HexColor("#4CC3B0"))
    c.setFillColor(colors.HexColor("#F0FDF4"))
    c.rect(16 * mm, y - 12 * mm, width - 32 * mm, 12 * mm, fill=1, stroke=1)

    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(colors.HexColor("#065F46"))
    c.drawString(20 * mm, y - 8 * mm, "TOTAL INPATIENT BILL AMOUNT: Rs. 77,500.00")
    c.drawRightString(width - 20 * mm, y - 8 * mm, "PAID IN FULL (PAID VIA UPI / NETBANKING)")

    y -= 20 * mm
    draw_heading("AUTHENTICATION & HOSPITAL DISPATCH")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(18 * mm, y, "Verified by: City Care Inpatient Billing Desk | Authorized Medical Superintendent Signature")
    y -= 12 * mm
    c.drawString(18 * mm, y, "Billing Officer: __________________________        Date: 18-08-2026")

    c.showPage()
    c.save()
    return str(path)


def generate_sample_discharge_pdf() -> str:
    path = SAMPLE_DIR / "City_Care_Discharge_Summary.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    # Header
    c.setFillColor(colors.HexColor("#0D1B2A"))
    c.rect(0, height - 32 * mm, width, 32 * mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#38BDF8"))
    c.setFont("Helvetica-Bold", 15)
    c.drawString(18 * mm, height - 14 * mm, "CITY CARE MULTISPECIALITY HOSPITAL — DISCHARGE SUMMARY")
    c.setFillColor(colors.HexColor("#E0E1DD"))
    c.setFont("Helvetica", 8.5)
    c.drawString(18 * mm, height - 21 * mm, "DEPARTMENT OF GENERAL & LAPAROSCOPIC SURGERY | IPD NO: IP-99201")

    y = height - 42 * mm

    def section(title, text_lines):
        nonlocal y
        c.setFillColor(colors.HexColor("#1B263B"))
        c.rect(16 * mm, y - 2 * mm, width - 32 * mm, 6 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(19 * mm, y, title)
        y -= 8 * mm

        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#0D1B2A"))
        for line in text_lines:
            c.drawString(18 * mm, y, line)
            y -= 5 * mm
        y -= 3 * mm

    section("PATIENT IDENTIFICATION", [
        "Patient: Satnam Singh | Age: 27 Years | Gender: Male | Admission: 14-08-2026 | Discharge: 17-08-2026",
        "Treating Consultant: Dr. Rajesh Mehta, MS (Gen Surg), FMAS | Policy No: STAR-HEALTH-FAMILY-2024"
    ])

    section("CLINICAL DIAGNOSIS & REASON FOR ADMISSION", [
        "Primary Diagnosis: Acute Appendicitis with appendicular phlegmon (ICD-10: K35.80)",
        "Chief Complaints: Severe right iliac fossa abdominal pain, nausea, low-grade fever for 24 hours.",
        "Clinical Examination: Marked tenderness and rebound guarding at McBurney's point. Rovsing's sign positive."
    ])

    section("OPERATIVE PROCEDURE & INTRA-OPERATIVE FINDINGS", [
        "Procedure Performed: Laparoscopic Appendectomy on 14-08-2026 under General Anaesthesia.",
        "Operative Findings: Acute retrocecal appendicitis with localized inflammatory exudate. Appendix ligated and removed.",
        "Histopathology: Specimen sent for HPE. No malignancy observed."
    ])

    section("POST-OPERATIVE COURSE & DISCHARGE ADVICE", [
        "Post-op Course: Afebrile, vitals stable, bowel sounds restored on Post-Op Day 1. Diet upgraded to normal.",
        "Discharge Medications: Tab Cefuroxime 500mg BD x 5 days, Tab Pantoprazole 40mg OD x 5 days, Tab Paracetamol SOS.",
        "Follow-up: Suture removal and dressing review at surgical OPD on 24-08-2026."
    ])

    c.showPage()
    c.save()
    return str(path)


def ensure_sample_files():
    bill_path = SAMPLE_DIR / "City_Care_Hospital_Final_Bill.pdf"
    if not bill_path.exists():
        generate_sample_bill_pdf()
    dc_path = SAMPLE_DIR / "City_Care_Discharge_Summary.pdf"
    if not dc_path.exists():
        generate_sample_discharge_pdf()


if __name__ == "__main__":
    b_path = generate_sample_bill_pdf()
    d_path = generate_sample_discharge_pdf()
    print(f"Generated sample PDFs:\n - {b_path}\n - {d_path}")
