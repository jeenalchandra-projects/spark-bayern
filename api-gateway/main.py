# =============================================================================
# main.py — API Gateway: the central entry point for all requests
# =============================================================================
# WHAT THIS FILE DOES:
# This is the "front door" of the entire backend system.
# Every request from the browser comes here first. This file:
#   1. Checks the passphrase (via auth.py)
#   2. Records the action in the audit log (via audit.py)
#   3. Receives the uploaded PDF
#   4. Calls the quality service, RAG service, and translation service
#   5. Combines all results into one response
#   6. Deletes the file from memory
#   7. Returns the combined result to the browser
#
# IMPORTANT — THE FILE IS NEVER SAVED:
# Python reads the uploaded file into a variable (bytes in RAM).
# We pass those bytes to the analysis services.
# After we have the results, the variable goes out of scope and Python
# automatically frees the memory. No disk write ever occurs.
# =============================================================================

import httpx                               # For calling other services
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Allows the browser to call this API
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from config import get_settings
from auth import AuthRequired
from audit import log_event, get_audit_log, get_log_summary

settings = get_settings()


# =============================================================================
# APP STARTUP AND SHUTDOWN
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code here runs once when the server starts (before the "yield")
    and once when it shuts down (after the "yield").
    We use this to create and close the HTTP client efficiently.
    """
    # Create a shared HTTP client — reusing one client is more efficient
    # than creating a new one for every request
    app.state.http_client = httpx.AsyncClient(
        timeout=60.0  # Wait up to 60 seconds for other services to respond
    )
    log_event("service_started", result_summary="API Gateway online")
    yield  # Server runs here
    # Cleanup on shutdown
    await app.state.http_client.aclose()
    log_event("service_stopped", result_summary="API Gateway shutting down")


# =============================================================================
# CREATE THE FASTAPI APPLICATION
# =============================================================================
app = FastAPI(
    title="SPARK-Bayern API Gateway",
    description=(
        "Central gateway for the SPARK-Bayern permit processing extension. "
        "Handles document upload, quality scoring, legal RAG analysis, and translation. "
        "GDPR-compliant: no documents stored, all processing in-memory."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# CORS MIDDLEWARE
# =============================================================================
# CORS = Cross-Origin Resource Sharing
# WHAT THIS IS: Browsers block JavaScript from calling APIs on different domains
# by default. Our React frontend runs on one URL, the API on another.
# CORS middleware tells the browser "yes, this API allows requests from the frontend".
# WHY IMPORTANT FOR SECURITY: In production, replace "*" with the exact frontend URL.
# For the hackathon demo, allowing all origins ("*") is acceptable.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # In production: ["https://spark-bayern.up.railway.app"]
    allow_credentials=True,
    allow_methods=["*"],        # Allow GET, POST, etc.
    allow_headers=["*"],        # Allow all headers including our X-Access-Code
)


# =============================================================================
# HELPER FUNCTION: Call another service
# =============================================================================
async def call_service(
    endpoint_url: str,
    file_bytes: bytes,
    filename: str,
    extra_data: dict | None = None,
) -> dict:
    """
    Sends a file to one of our backend services and returns its response.

    Args:
        endpoint_url: Full URL of the service endpoint (e.g., http://quality-service:8001/analyze)
        file_bytes: The raw bytes of the PDF file
        filename: Original filename (used for logging only, not stored)
        extra_data: Any additional form fields to send alongside the file

    Returns:
        The JSON response from the service as a Python dictionary.
        If the service is unreachable, returns an error dict instead of crashing.
    """
    try:
        # We send the file as "multipart/form-data" — the same format a browser
        # uses when submitting a form with a file attachment.
        files = {"file": (filename, file_bytes, "application/pdf")}
        data = extra_data or {}

        response = await app.state.http_client.post(
            endpoint_url,
            files=files,
            data=data,
        )
        response.raise_for_status()  # Raises an exception if status code >= 400
        return response.json()

    except httpx.ConnectError:
        # Service is not running — return a graceful error instead of crashing
        return {
            "error": "service_unavailable",
            "message": f"Service at {endpoint_url} is not reachable. "
                       "Make sure all Docker containers are running.",
        }
    except httpx.TimeoutException:
        return {
            "error": "service_timeout",
            "message": f"Service at {endpoint_url} took too long to respond.",
        }
    except Exception as e:
        return {
            "error": "service_error",
            "message": str(e),
        }


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Railway and Docker use this to verify the service is running.
    Returns 200 OK if everything is fine.
    """
    return {
        "status": "ok",
        "service": "api-gateway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gdpr_note": "No personal data stored. In-memory processing only.",
    }


@app.post("/verify-access")
async def verify_access(authenticated: bool = AuthRequired):
    """
    Endpoint the frontend calls first to check if the passphrase is correct.
    The actual check happens in the AuthRequired dependency (auth.py).
    If we get here, the passphrase was correct.

    FLOW:
    1. Browser sends POST /verify-access with X-Access-Code header
    2. AuthRequired checks the code
    3. If wrong: returns 401 immediately
    4. If correct: we return success here
    """
    log_event("access_verified")
    return {
        "authenticated": True,
        "message": "Zugang gewährt",  # German: Access granted
        "message_en": "Access granted",
    }


@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(..., description="PDF document to analyze"),
    language: str = "de",
    authenticated: bool = AuthRequired,
):
    """
    Main endpoint: receives a PDF, runs all analyses, returns combined results.

    This is the most important endpoint. Here is exactly what happens:

    STEP 1: Read the file into memory (bytes)
    STEP 2: Validate it (size check, PDF check)
    STEP 3: Log the event (no personal data)
    STEP 4: Send to Quality Service → get quality score
    STEP 5: Send to RAG Service → get legal analysis against BayBO
    STEP 6: Combine results into one response
    STEP 7: If language != "de", send result text to Translation Service
    STEP 8: Return everything to the browser
    STEP 9: File bytes are no longer referenced → Python frees the memory

    Args:
        file: The uploaded PDF file
        language: Language code for response text (de/en/tr/ar)
        authenticated: Injected by AuthRequired — ensures passphrase was correct
    """

    # ------------------------------------------------------------------
    # STEP 1: Read file into memory
    # ------------------------------------------------------------------
    # file.read() loads the entire file as bytes into a variable.
    # This variable lives only in RAM — no disk involvement.
    file_bytes = await file.read()

    # ------------------------------------------------------------------
    # STEP 2: Validate the file
    # ------------------------------------------------------------------
    # Check file size
    max_bytes = settings.max_upload_size_mb * 1024 * 1024  # Convert MB to bytes
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,  # 413 = Payload Too Large
            detail={
                "error": "Datei zu groß",  # German: File too large
                "error_en": f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
                "max_size_mb": settings.max_upload_size_mb,
                "received_size_mb": round(len(file_bytes) / (1024 * 1024), 2),
            }
        )

    # Check that it's actually a PDF (PDFs start with the bytes "%PDF")
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=415,  # 415 = Unsupported Media Type
            detail={
                "error": "Nur PDF-Dateien werden akzeptiert",  # Only PDF files accepted
                "error_en": "Only PDF files are accepted.",
            }
        )

    # ------------------------------------------------------------------
    # STEP 3: Log the upload event (no personal data logged)
    # ------------------------------------------------------------------
    event_id = log_event(
        action="document_uploaded",
        file_size_bytes=len(file_bytes),
        language=language,
        result_summary=f"File received: {len(file_bytes)} bytes",
    )

    # ------------------------------------------------------------------
    # STEP 4 & 5: Call quality and RAG services in parallel
    # ------------------------------------------------------------------
    # We use httpx to call both services at the same time (parallel),
    # which is faster than calling them one after the other (sequential).
    import asyncio

    quality_task = call_service(
        endpoint_url=f"{settings.quality_service_url}/analyze",
        file_bytes=file_bytes,
        filename=file.filename or "document.pdf",
    )

    rag_task = call_service(
        endpoint_url=f"{settings.rag_service_url}/analyze",
        file_bytes=file_bytes,
        filename=file.filename or "document.pdf",
        extra_data={"language": language},
    )

    # asyncio.gather runs both tasks at the same time and waits for both to finish
    quality_result, rag_result = await asyncio.gather(quality_task, rag_task)

    log_event(
        action="analysis_completed",
        result_summary=f"Quality: {quality_result.get('score', 'error')}, "
                       f"RAG: {len(rag_result.get('findings', []))} findings",
    )

    # ------------------------------------------------------------------
    # STEP 6: Build combined result
    # ------------------------------------------------------------------
    combined_result = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "quality": quality_result,
        "legal_analysis": rag_result,
        "language": language,
        # EU AI Act compliance notice — always present
        "ai_notice": {
            "de": "KI-Unterstützung – Die Endentscheidung liegt beim Sachbearbeiter.",
            "en": "AI assistance – The final decision rests with the case worker.",
        },
        "gdpr_notice": {
            "de": "Dieses Dokument wird nicht gespeichert. Alle Daten werden nach der Verarbeitung gelöscht.",
            "en": "This document is not stored. All data is deleted after processing.",
        },
    }

    # ------------------------------------------------------------------
    # STEP 7: Translate if language is not German
    # ------------------------------------------------------------------
    if language != "de":
        translation_result = await call_service(
            endpoint_url=f"{settings.translation_service_url}/translate",
            file_bytes=b"{}",  # Translation service gets JSON, not a PDF
            filename="result.json",
            extra_data={
                "target_language": language,
                "text": str(combined_result),  # Send the result for translation
            },
        )
        if "error" not in translation_result:
            combined_result["translated_summary"] = translation_result.get("translated_text", "")

        log_event(action="translation_completed", language=language)

    # ------------------------------------------------------------------
    # STEP 8: Return result
    # STEP 9: file_bytes goes out of scope here → Python frees memory
    # ------------------------------------------------------------------
    return combined_result


@app.get("/audit-log")
async def view_audit_log(authenticated: bool = AuthRequired):
    """
    Returns the current session's audit log.
    Only accessible with the correct passphrase.
    Useful for demonstrating GDPR compliance during the hackathon presentation.
    """
    return {
        "summary": get_log_summary(),
        "entries": get_audit_log(),
        "gdpr_note": "This log contains no personal data. Document content is never logged.",
    }


@app.get("/session-stats")
async def session_stats(authenticated: bool = AuthRequired):
    """Returns high-level statistics about the current demo session."""
    return get_log_summary()
