# =============================================================================
# query.py — RAG Query Engine
# =============================================================================
# WHAT THIS FILE DOES:
# Takes an uploaded permit application, extracts its text, finds the relevant
# BayBO law paragraphs, then asks the LLM to analyze the application against
# those specific laws. Returns structured findings.
#
# THE RAG FLOW IN DETAIL:
# 1. Extract text from the uploaded PDF
# 2. Build a search query from that text
# 3. Search ChromaDB for relevant BayBO paragraphs
# 4. Build a prompt: "Here are the relevant laws. Here is the application.
#    What is complete? What is missing? What needs attention?"
# 5. Send to LLM via Requesty → get structured response
# 6. Return findings
#
# WHY THIS IS BETTER THAN JUST ASKING THE LLM:
# Without RAG: LLM answers from training data (which may be outdated or wrong)
# With RAG: LLM answers based on the ACTUAL current BayBO text we provide
# This means every finding is grounded in a real law paragraph.
# =============================================================================

import io
import json
import pdfplumber
from openai import OpenAI
import chromadb
from config import get_settings
from ingest import search_relevant_law, REQUIRED_DOCUMENTS

settings = get_settings()


def _create_llm_client() -> OpenAI:
    """
    Creates an OpenAI-compatible client pointed at Requesty.

    Even though we're using Requesty and Mistral, we use the openai Python library
    because Requesty implements the exact same API format as OpenAI.
    We just change the base_url to point to Requesty instead of OpenAI.
    """
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        default_headers={
            "X-Title": settings.llm_app_title,
        }
    )


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts all readable text from a PDF.
    Returns empty string if text extraction fails (e.g., for scanned PDFs).
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)
            return "\n\n".join(all_text)
    except Exception:
        return ""


def _build_analysis_prompt(
    application_text: str,
    relevant_law_chunks: list[dict],
    language: str = "de",
) -> str:
    """
    Builds the prompt we send to the LLM.

    This is the most important part of RAG — the prompt design.
    We give the LLM:
    1. A clear role (senior Sachbearbeiter)
    2. The relevant law text (grounding)
    3. The application content
    4. A specific structured output format
    5. A reminder that the human makes the final decision

    IMPORTANT SAFETY PRINCIPLE:
    The prompt explicitly says the AI is assisting, not deciding.
    This satisfies EU AI Act Article 14 (human oversight).
    """
    law_text = "\n\n---\n\n".join([
        f"[{chunk['source']}]\n{chunk['text']}"
        for chunk in relevant_law_chunks
    ])

    if language == "de":
        lang_instruction = "Antworte ausschließlich auf Deutsch."
    elif language == "en":
        lang_instruction = "Reply exclusively in English."
    elif language == "tr":
        lang_instruction = "Yalnızca Türkçe yanıt verin."
    elif language == "ar":
        lang_instruction = "أجب باللغة العربية فقط."
    else:
        lang_instruction = "Reply in German (Deutsch)."

    prompt = f"""Du bist ein erfahrener Sachbearbeiter der Bauaufsichtsbehörde in Bayern.
Du prüfst Bauanträge auf Vollständigkeit und Plausibilität gemäß der Bayerischen Bauordnung (BayBO).

WICHTIG: Du unterstützt die Prüfung. Die endgültige Entscheidung trifft immer der zuständige Sachbearbeiter.
{lang_instruction}

---
RELEVANTE GESETZLICHE GRUNDLAGEN (BayBO):
{law_text}

---
INHALT DES EINGEREICHTEN ANTRAGS:
{application_text[:3000]}

---
AUFGABE:
Analysiere den Antrag anhand der oben genannten gesetzlichen Grundlagen.
Gib deine Antwort ausschließlich als JSON zurück (kein Text davor oder danach):

{{
  "overall_status": "vollständig" | "unvollständig" | "prüfungsbedürftig",
  "findings": [
    {{
      "type": "missing" | "issue" | "ok" | "info",
      "title": "Kurzer Titel des Befunds",
      "description": "Detaillierte Beschreibung",
      "legal_basis": "Relevanter BayBO-Artikel",
      "recommendation": "Empfohlene Maßnahme"
    }}
  ],
  "summary": "Gesamtzusammenfassung der Prüfung in 2-3 Sätzen",
  "next_steps": ["Schritt 1", "Schritt 2"]
}}"""

    return prompt


def analyze_application(
    file_bytes: bytes,
    collection: chromadb.Collection,
    language: str = "de",
) -> dict:
    """
    Main function: runs the full RAG analysis pipeline on an uploaded application.

    Args:
        file_bytes: The raw bytes of the uploaded PDF (in memory, never on disk)
        collection: The pre-loaded ChromaDB collection with BayBO content
        language: Target language for the response

    Returns:
        A dictionary with findings, status, and recommendations.
    """

    # ------------------------------------------------------------------
    # STEP 1: Extract text from the application PDF
    # ------------------------------------------------------------------
    application_text = _extract_text_from_pdf(file_bytes)

    if not application_text.strip():
        # No text could be extracted (scanned image without OCR)
        return {
            "overall_status": "prüfungsbedürftig",
            "findings": [{
                "type": "issue",
                "title": "Text nicht extrahierbar",
                "description": (
                    "Aus dem Dokument konnte kein Text extrahiert werden. "
                    "Das Dokument scheint ein Scan ohne Texterkennung (OCR) zu sein. "
                    "Eine automatische Prüfung ist nicht möglich."
                ),
                "legal_basis": "Art. 68 BayBO",
                "recommendation": "Bitte reichen Sie das Dokument als durchsuchbares PDF ein.",
            }],
            "summary": "Dokument konnte nicht automatisch geprüft werden.",
            "next_steps": ["Dokument als durchsuchbares PDF neu einreichen"],
            "rag_used": False,
            "law_chunks_consulted": 0,
        }

    # ------------------------------------------------------------------
    # STEP 2: Find relevant BayBO paragraphs using vector search
    # ------------------------------------------------------------------
    # We use the first 1000 characters as the search query
    # (enough to understand what kind of application this is)
    search_query = application_text[:1000]
    relevant_chunks = search_relevant_law(collection, search_query, top_k=settings.rag_top_k)

    # ------------------------------------------------------------------
    # STEP 3: Build prompt and call LLM
    # ------------------------------------------------------------------
    prompt = _build_analysis_prompt(application_text, relevant_chunks, language)

    client = _create_llm_client()

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein präziser juristischer Assistent für Bauantragsverfahren in Bayern. "
                        "Antworte immer mit validem JSON. Kein Text außerhalb des JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,    # Low temperature = more consistent, less creative
                                # We want factual analysis, not imaginative text
            max_tokens=2000,
        )

        raw_response = response.choices[0].message.content.strip()

        # ------------------------------------------------------------------
        # STEP 4: Parse the LLM response as JSON
        # ------------------------------------------------------------------
        # The LLM might include markdown code fences (```json ... ```)
        # so we strip those before parsing
        if raw_response.startswith("```"):
            raw_response = raw_response.split("```")[1]
            if raw_response.startswith("json"):
                raw_response = raw_response[4:]
            raw_response = raw_response.strip()

        analysis = json.loads(raw_response)

        # Add metadata to the result
        analysis["rag_used"] = True
        analysis["law_chunks_consulted"] = len(relevant_chunks)
        analysis["law_sources"] = [chunk["source"] for chunk in relevant_chunks]
        analysis["required_documents"] = REQUIRED_DOCUMENTS
        analysis["ai_model"] = settings.llm_model
        analysis["ai_notice"] = (
            "Diese Analyse wurde mit KI-Unterstützung erstellt. "
            "Die Endentscheidung liegt beim zuständigen Sachbearbeiter."
        )

        return analysis

    except json.JSONDecodeError as e:
        # If the LLM returns non-JSON (shouldn't happen with temperature=0.1 but possible)
        return {
            "overall_status": "prüfungsbedürftig",
            "findings": [{
                "type": "info",
                "title": "Analyse-Ergebnis (Textformat)",
                "description": raw_response[:1000],
                "legal_basis": "Automatische Prüfung",
                "recommendation": "Manuelle Prüfung empfohlen",
            }],
            "summary": "Die KI-Analyse konnte nicht strukturiert dargestellt werden.",
            "next_steps": ["Manuelle Prüfung durch Sachbearbeiter"],
            "rag_used": True,
            "law_chunks_consulted": len(relevant_chunks),
            "parse_error": str(e),
        }

    except Exception as e:
        return {
            "overall_status": "prüfungsbedürftig",
            "findings": [{
                "type": "issue",
                "title": "KI-Service nicht verfügbar",
                "description": f"Die KI-Analyse konnte nicht durchgeführt werden: {str(e)}",
                "legal_basis": "N/A",
                "recommendation": "Manuelle Prüfung erforderlich",
            }],
            "summary": "KI-Analyse nicht verfügbar. Manuelle Prüfung erforderlich.",
            "next_steps": ["Manuelle Prüfung durch Sachbearbeiter"],
            "rag_used": False,
            "law_chunks_consulted": 0,
            "error": str(e),
        }
