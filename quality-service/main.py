# =============================================================================
# main.py — Quality Service
# =============================================================================
# WHAT THIS FILE DOES:
# Runs a small FastAPI web service that accepts a PDF file and returns
# its quality score. Called by the API Gateway as part of the analysis pipeline.
# =============================================================================

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from scorer import analyze_pdf

app = FastAPI(
    title="SPARK-Bayern Quality Service",
    description="Analyzes PDF document quality without AI. Returns score, grade, and issues.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "quality-service"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Receives a PDF and returns a quality analysis.

    The file is read into memory, analyzed, and the result is returned.
    The file bytes are never written to disk.
    """
    # Read file into memory
    file_bytes = await file.read()

    # Validate it's a PDF
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="Only PDF files accepted")

    # Run the analysis (purely in-memory)
    report = analyze_pdf(file_bytes)

    # Convert the dataclass to a JSON-serializable dictionary
    return {
        "score": report.score,
        "grade": report.grade,
        "is_native_pdf": report.is_native_pdf,
        "page_count": report.page_count,
        "has_extractable_text": report.has_extractable_text,
        "summary_de": report.summary_de,
        "summary_en": report.summary_en,
        "issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "message_de": issue.message_de,
                "message_en": issue.message_en,
                "points_deducted": issue.points_deducted,
                "details": issue.details,
            }
            for issue in report.issues
        ],
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "gdpr_note": "File was analyzed in-memory. No data stored.",
    }
