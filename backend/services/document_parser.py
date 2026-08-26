"""
DOCUMENT PARSER SERVICE
-----------------------
Extracts text and structured content from uploaded PDF bills, hospital invoice images,
and discharge summaries using pdfplumber and OCR simulation.
"""
import io
from pathlib import Path
import pdfplumber
from PIL import Image


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extracts raw text from a PDF file using pdfplumber."""
    extracted_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
    return "\n".join(extracted_text)


def extract_text_from_image_bytes(image_bytes: bytes, filename: str) -> str:
    """Simulates Vertex AI Gemini Multimodal OCR on an uploaded bill or summary image."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
    except Exception:
        width, height = (1200, 1600)

    # In production with Vertex AI Gemini:
    # response = gemini_client.models.generate_content(
    #     model="gemini-2.5-pro",
    #     contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), OCR_PROMPT]
    # )
    return f"[OCR PARSED IMAGE: {filename} ({width}x{height}px)]"


def parse_uploaded_file(file_bytes: bytes, filename: str) -> str:
    """Dispatches to the appropriate parser based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        text = extract_text_from_pdf_bytes(file_bytes)
        if not text.strip():
            # Scanned / Image-only PDF fallback
            text = f"[SCANNED PDF OCR: {filename}]"
        return text
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        return extract_text_from_image_bytes(file_bytes, filename)
    elif ext in [".txt", ".json", ".csv"]:
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        return file_bytes.decode("utf-8", errors="ignore")
