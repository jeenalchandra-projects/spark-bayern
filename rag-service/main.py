# =============================================================================
# main.py — RAG Service
# =============================================================================
# Loads the BayBO vector store on startup, then handles analysis requests.
# =============================================================================

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from ingest import build_vector_store
from query import analyze_application

# This will hold our vector store after startup
vector_store = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs the BayBO ingestion pipeline ONCE when the service starts.
    After this, the vector store is in memory and ready for queries.
    """
    global vector_store
    print("Loading BayBO into vector store...")
    vector_store = build_vector_store()
    print("RAG service ready.")
    yield
    # Cleanup: vector store is released from memory when service stops
    vector_store = None


app = FastAPI(
    title="SPARK-Bayern RAG Service",
    description="Legal analysis of permit applications against Bayern Bauordnung (BayBO) using RAG.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "rag-service",
        "vector_store_loaded": vector_store is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    language: str = Form(default="de"),
):
    """
    Receives a PDF permit application and returns a legal analysis
    grounded in actual BayBO law paragraphs.
    """
    if vector_store is None:
        raise HTTPException(
            status_code=503,
            detail="Vector store not initialized. Service may still be starting up."
        )

    file_bytes = await file.read()

    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="Only PDF files accepted")

    result = analyze_application(file_bytes, vector_store, language)
    return result


@app.get("/required-documents")
async def get_required_documents():
    """
    Returns the list of required documents for a Bayern Baugenehmigung.
    This is useful for the frontend to display a checklist.
    """
    from ingest import REQUIRED_DOCUMENTS
    return {
        "permit_type": "Baugenehmigung",
        "bundesland": "Bayern",
        "legal_basis": "Art. 68 BayBO",
        "documents": REQUIRED_DOCUMENTS,
    }
