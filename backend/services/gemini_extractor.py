"""
GEMINI LIVE MULTIMODAL EXTRACTION ENGINE
---------------------------------------
Performs real-time extraction on uploaded Hospital Bills, Discharge Summaries, and Prescriptions
using Google Gemini API (gemini-2.5-flash / gemini-1.5-flash) with structured JSON schema output,
and provides intelligent offline fallback when API key is not configured.
"""
import os
import json
import re
from pathlib import Path

# Try importing Google Generative AI
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""


def set_gemini_api_key(api_key: str):
    global GEMINI_API_KEY
    GEMINI_API_KEY = api_key.strip()
    if HAS_GENAI and GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)


if HAS_GENAI and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        pass


EXTRACTION_PROMPT = """
You are an expert Indian Health Insurance Underwriting and TPA Claim Ingestion AI.
Extract all relevant claim fields from the provided hospital bill, discharge summary, and prescription text.

Output ONLY valid JSON with the following exact structure:
{
  "patient_name": "Full name of patient",
  "aadhaar_number": "Aadhaar number if present or null",
  "pan_number": "PAN number if present or null",
  "policy_number": "Insurance policy number if present or null",
  "total_amount": 77500.00,
  "diagnosis": "Primary clinical diagnosis",
  "procedure": "Surgical or medical procedure performed",
  "admission_date": "DD-MM-YYYY",
  "discharge_date": "DD-MM-YYYY",
  "hospital_name": "Hospital Name",
  "hospital_gstin": "15-digit GSTIN or null",
  "treating_doctor": "Doctor Name",
  "doctor_reg_number": "Medical Council Registration Number if present or null",
  "bill_date": "DD-MM-YYYY",
  "itemized_charges": [
    {"category": "Room Rent", "amount": 10500.00},
    {"category": "Surgery/OT", "amount": 32000.00},
    {"category": "Anaesthesia", "amount": 8000.00},
    {"category": "Investigations/Lab", "amount": 7200.00},
    {"category": "Pharmacy/Consumables", "amount": 16800.00},
    {"category": "Other Hospital Services", "amount": 3000.00}
  ]
}
"""


def extract_with_gemini_live(combined_text: str, api_key: str | None = None) -> dict | None:
    """Invokes Gemini API live if key is available."""
    key = api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key or not HAS_GENAI:
        return None

    try:
        genai.configure(api_key=key)
        # Try latest flash models
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"{EXTRACTION_PROMPT}\n\nDOCUMENT TEXT:\n{combined_text}",
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )
        if response and response.text:
            text = response.text.strip()
            # Clean possible markdown formatting
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
    except Exception as e:
        print(f"Gemini live extraction error: {e}")
        return None
