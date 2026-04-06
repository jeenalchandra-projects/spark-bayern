# =============================================================================
# main.py — SPARK-Bayern Consolidated Backend
# =============================================================================
# Single FastAPI application combining:
#   - API Gateway (routing, auth, GDPR audit)
#   - Quality Service (PDF scoring)
#   - RAG Service (Bayern BayBO legal analysis)
#   - Translation Service (DE/EN/TR/AR)
#
# STARTUP SEQUENCE:
# 1. Load BayBO law text into ChromaDB vector store (once, ~5 seconds)
# 2. Begin accepting requests
#
# All uploaded files are processed in-memory only. Nothing is written to disk.
# =============================================================================

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from auth import AuthRequired, verify_access_code
from audit import log_event, get_audit_log, get_log_summary
from quality import analyze_pdf
from rag import build_vector_store, analyze_application, REQUIRED_DOCUMENTS
from translations import TRANSLATIONS, translate_text

settings = get_settings()

# Global vector store — loaded once at startup, reused for all requests
_vector_store = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the BayBO vector store once when the service starts."""
    global _vector_store
    print("SPARK-Bayern backend starting...")
    print("Loading BayBO into vector store...")
    _vector_store = build_vector_store()
    log_event("service_started", result_summary="Backend online, BayBO loaded")
    print("Backend ready.")
    yield
    _vector_store = None
    log_event("service_stopped")


app = FastAPI(
    title="SPARK-Bayern Backend",
    description=(
        "Consolidated backend for SPARK-Bayern. "
        "Handles document upload, quality scoring, BayBO legal analysis, and translation. "
        "GDPR-compliant: no documents stored, all processing in-memory."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allows the frontend (different URL) to call this API
# In production, replace "*" with your exact Railway frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH CHECK
# =============================================================================
@app.get("/health")
async def health():
    """Used by Railway to verify the service is running."""
    return {
        "status": "ok",
        "service": "spark-bayern-backend",
        "vector_store_loaded": _vector_store is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gdpr": "No personal data stored. In-memory processing only.",
    }


# =============================================================================
# ACCESS VERIFICATION
# =============================================================================
@app.post("/verify-access")
async def verify_access(authenticated: bool = AuthRequired):
    """
    Frontend calls this first to check if the passphrase is correct.
    Returns 401 if wrong, 200 if correct.
    """
    log_event("access_verified")
    return {"authenticated": True, "message": "Zugang gewährt", "message_en": "Access granted"}


# =============================================================================
# MAIN ANALYSIS ENDPOINT
# =============================================================================
@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    language: str = Form(default="de"),
    authenticated: bool = AuthRequired,
):
    """
    Receives a PDF permit application and returns combined analysis results.

    WHAT HAPPENS STEP BY STEP:
    1. File bytes are read into memory (never written to disk)
    2. File is validated (size check, PDF magic bytes check)
    3. Event is logged (no personal data — only size and language)
    4. Quality analysis runs (pure Python, no AI, instant)
    5. RAG analysis runs (vector search + LLM via Requesty)
       Steps 4 and 5 run in PARALLEL for speed
    6. If language != "de": key text is translated via LLM
    7. Combined result is returned
    8. file_bytes variable goes out of scope → Python frees the memory
    """

    # Step 1: Read into memory
    file_bytes = await file.read()

    # Step 2: Validate
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail={
            "error": "Datei zu groß",
            "error_en": f"File too large. Max: {settings.max_upload_size_mb}MB",
            "max_mb": settings.max_upload_size_mb,
        })
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail={
            "error": "Nur PDF-Dateien werden akzeptiert",
            "error_en": "Only PDF files are accepted",
        })

    # Step 3: Audit log (no personal data)
    event_id = log_event(
        action="document_uploaded",
        file_size_bytes=len(file_bytes),
        language=language,
    )

    # Step 4 + 5: Quality and RAG in parallel
    # asyncio.gather runs both coroutines at the same time
    quality_task = asyncio.to_thread(analyze_pdf, file_bytes)
    rag_task = asyncio.to_thread(analyze_application, file_bytes, _vector_store, language)

    quality_report, rag_result = await asyncio.gather(quality_task, rag_task)

    log_event(
        action="analysis_completed",
        result_summary=f"Quality: {quality_report.score}/100, Status: {rag_result.get('overall_status', 'unknown')}",
    )

    # Step 6: Translate summary if non-German
    translated_summary = None
    if language != "de" and rag_result.get("summary"):
        translated_summary = await translate_text(rag_result["summary"], language)

    # Step 7: Build combined response
    result = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "quality": {
            "score": quality_report.score,
            "grade": quality_report.grade,
            "is_native_pdf": quality_report.is_native_pdf,
            "page_count": quality_report.page_count,
            "has_extractable_text": quality_report.has_extractable_text,
            "summary_de": quality_report.summary_de,
            "summary_en": quality_report.summary_en,
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message_de": i.message_de,
                    "message_en": i.message_en,
                    "points_deducted": i.points_deducted,
                    "details": i.details,
                }
                for i in quality_report.issues
            ],
        },
        "legal_analysis": rag_result,
        "language": language,
        **({"translated_summary": translated_summary} if translated_summary else {}),
        "ai_notice": {
            "de": "KI-Unterstützung – Die Endentscheidung liegt beim Sachbearbeiter.",
            "en": "AI assistance – The final decision rests with the case worker.",
        },
        "gdpr_notice": {
            "de": "Dieses Dokument wird nicht gespeichert. Alle Daten werden nach der Verarbeitung gelöscht.",
            "en": "This document is not stored. All data is deleted after processing.",
        },
    }

    # Step 8: file_bytes goes out of scope here — Python frees memory
    return result


# =============================================================================
# TRANSLATION ENDPOINTS
# =============================================================================
@app.get("/ui-translations/{language}")
async def get_ui_translations(language: str):
    """Returns all static UI translations for the given language."""
    lang = language if language in TRANSLATIONS else "de"
    t = TRANSLATIONS[lang]
    return {
        "language": lang,
        "rtl": t.get("rtl", False),
        "translations": t,
    }


@app.post("/translate")
async def translate(
    target_language: str = Form(...),
    text: str = Form(...),
    authenticated: bool = AuthRequired,
):
    """Translates dynamic text to the target language via LLM."""
    translated = await translate_text(text, target_language)
    return {
        "translated_text": translated,
        "language": target_language,
        "rtl": target_language == "ar",
    }


# =============================================================================
# LEGAL REFERENCE ENDPOINTS
# =============================================================================
@app.get("/required-documents")
async def required_documents():
    """Returns the required document list for Bayern Baugenehmigung."""
    return {
        "permit_type": "Baugenehmigung",
        "bundesland": "Bayern",
        "legal_basis": "Art. 68 BayBO",
        "documents": REQUIRED_DOCUMENTS,
    }


# =============================================================================
# GDPR AUDIT LOG
# =============================================================================
@app.get("/audit-log")
async def audit_log(authenticated: bool = AuthRequired):
    """Returns the session audit log. No personal data is ever included."""
    return {
        "summary": get_log_summary(),
        "entries": get_audit_log(),
        "note": "This log contains no personal data. Document content is never logged.",
    }


# =============================================================================
# RAILWAY ENTRYPOINT
# =============================================================================
# Railway sets the PORT environment variable automatically.
# We read it here so the service starts on the correct port.
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", settings.port))
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
