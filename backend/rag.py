# =============================================================================
# rag.py — Bayern BayBO RAG Pipeline
# =============================================================================
# Merged from rag-service/ingest.py and rag-service/query.py.
# Loads BayBO law text into ChromaDB (in-memory), then answers questions
# about permit applications grounded in the actual law text.
# =============================================================================

import io
import os
import re
import json
import pdfplumber
import chromadb
from openai import OpenAI
from config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# BayBO fallback content (key articles, used when no PDF is available)
# ---------------------------------------------------------------------------
BAYBO_FALLBACK_CHUNKS = [
    {"id": "baybo_art_2", "source": "BayBO Art. 2 — Begriffe", "text": (
        "Art. 2 BayBO — Begriffe: Bauliche Anlagen sind mit dem Erdboden verbundene, "
        "aus Bauprodukten hergestellte Anlagen. Gebäude sind selbständig benutzbare, "
        "überdeckte bauliche Anlagen, die von Menschen betreten werden können. "
        "Gebäudeklasse 1: freistehende Gebäude bis 7 m Höhe, max. 2 Nutzungseinheiten. "
        "Gebäudeklasse 2: freistehende Gebäude bis 7 m. "
        "Gebäudeklasse 3: sonstige Gebäude bis 7 m. "
        "Gebäudeklasse 4: Gebäude bis 13 m. "
        "Gebäudeklasse 5: sonstige Gebäude einschließlich unterirdischer Gebäude."
    )},
    {"id": "baybo_art_6", "source": "BayBO Art. 6 — Abstandsflächen", "text": (
        "Art. 6 BayBO — Abstandsflächen: Vor den Außenwänden von Gebäuden sind Abstandsflächen freizuhalten. "
        "Die Abstandsfläche beträgt 1 H (H = Wandhöhe), mindestens 3 m. "
        "In Gewerbe- und Industriegebieten: 0,25 H, mindestens 3 m. "
        "Abstandsflächen müssen auf dem Grundstück selbst liegen. "
        "Grenzgaragen bis 3 m Wandhöhe sind zulässig."
    )},
    {"id": "baybo_art_11", "source": "BayBO Art. 11 — Erschließung", "text": (
        "Art. 11 BayBO — Erschließung: Bauliche Anlagen dürfen nur errichtet werden, wenn das Grundstück "
        "an einer befahrbaren öffentlichen Verkehrsfläche liegt oder eine gesicherte Zufahrt hat. "
        "Wasserversorgung und Abwasserbeseitigung müssen gesichert sein."
    )},
    {"id": "baybo_art_47", "source": "BayBO Art. 47 — Stellplätze", "text": (
        "Art. 47 BayBO — Stellplätze und Garagen: Bei Anlagen mit Zu- oder Abgangsverkehr "
        "sind notwendige Stellplätze herzustellen. "
        "Für Wohngebäude gilt: mindestens 1 Stellplatz pro Wohnung."
    )},
    {"id": "baybo_art_57", "source": "BayBO Art. 57 — Verfahrensfreie Bauvorhaben", "text": (
        "Art. 57 BayBO — Verfahrensfreie Bauvorhaben: Verfahrensfrei sind: "
        "Gebäude bis 75 m³ Brutto-Rauminhalt (außer Außenbereich). "
        "Garagen bis 50 m² Nutzfläche. "
        "Solarenergieanlagen an Gebäuden. "
        "Einfriedungen bis 2 m Höhe."
    )},
    {"id": "baybo_art_59", "source": "BayBO Art. 59 — Vereinfachtes Verfahren", "text": (
        "Art. 59 BayBO — Vereinfachtes Baugenehmigungsverfahren: "
        "Prüft die Übereinstimmung mit §§ 29-38 BauGB und örtlichen Bauvorschriften. "
        "Anwendbar auf Wohngebäude GK 1-3 und sonstige Gebäude GK 1-2."
    )},
    {"id": "baybo_art_60", "source": "BayBO Art. 60 — Baugenehmigungsverfahren", "text": (
        "Art. 60 BayBO — Baugenehmigungsverfahren: "
        "Bauvorhaben, die nicht verfahrensfrei sind und kein vereinfachtes Verfahren zulassen, "
        "bedürfen der Baugenehmigung. Der Bauantrag ist bei der Gemeinde einzureichen. "
        "Erforderlich: Bauzeichnungen, Baubeschreibung, Lageplan, Standsicherheitsnachweis, "
        "Wärmeschutznachweis, Schallschutznachweis, Nachweis der Barrierefreiheit."
    )},
    {"id": "baybo_art_68", "source": "BayBO Art. 68 — Erforderliche Unterlagen", "text": (
        "Art. 68 BayBO — Erforderliche Unterlagen: Dem Bauantrag sind beizufügen: "
        "1. Lageplan 1:1000 oder 1:500 mit Maßen zu den Grundstücksgrenzen. "
        "2. Bauzeichnungen (Grundrisse, Schnitte, Ansichten) 1:100. "
        "3. Baubeschreibung mit Nutzung, Konstruktion, Baustoffen. "
        "4. Berechnung Brutto-Rauminhalt (BRI) und Brutto-Grundfläche (BGF). "
        "5. Standsicherheitsnachweis. "
        "6. Wärmeschutznachweis nach GEG. "
        "7. Grundbuchauszug (nicht älter als 3 Monate). "
        "8. Zustimmungserklärung des Grundstückseigentümers."
    )},
]

REQUIRED_DOCUMENTS = [
    {"id": "lageplan", "name_de": "Lageplan", "name_en": "Site plan",
     "description_de": "Lageplan 1:1000 oder 1:500 mit Grundstücksgrenzen",
     "description_en": "Site plan 1:1000 or 1:500 with plot boundaries",
     "legal_basis": "Art. 68 Abs. 1 Nr. 1 BayBO", "mandatory": True},
    {"id": "bauzeichnungen", "name_de": "Bauzeichnungen", "name_en": "Architectural drawings",
     "description_de": "Grundrisse, Schnitte und Ansichten im Maßstab 1:100",
     "description_en": "Floor plans, sections and elevations at scale 1:100",
     "legal_basis": "Art. 68 Abs. 1 Nr. 2 BayBO", "mandatory": True},
    {"id": "baubeschreibung", "name_de": "Baubeschreibung", "name_en": "Building description",
     "description_de": "Beschreibung des Vorhabens mit Nutzung, Konstruktion, Baustoffen",
     "description_en": "Description of project including use, construction and materials",
     "legal_basis": "Art. 68 Abs. 1 Nr. 3 BayBO", "mandatory": True},
    {"id": "flaechenberechnung", "name_de": "Flächenberechnung", "name_en": "Area calculation",
     "description_de": "Berechnung BRI und BGF",
     "description_en": "Calculation of gross volume (BRI) and gross floor area (BGF)",
     "legal_basis": "Art. 68 Abs. 1 Nr. 4 BayBO", "mandatory": True},
    {"id": "standsicherheit", "name_de": "Standsicherheitsnachweis", "name_en": "Structural stability certificate",
     "description_de": "Statischer Nachweis durch Prüfsachverständigen",
     "description_en": "Static proof of structural stability by certified expert",
     "legal_basis": "Art. 68 Abs. 1 Nr. 5 BayBO", "mandatory": True},
    {"id": "waermeschutz", "name_de": "Wärmeschutznachweis", "name_en": "Thermal insulation certificate",
     "description_de": "Nachweis nach GEG (Gebäudeenergiegesetz)",
     "description_en": "Certificate per Building Energy Act (GEG)",
     "legal_basis": "Art. 68 BayBO i.V.m. GEG", "mandatory": True},
    {"id": "grundbuch", "name_de": "Grundbuchauszug", "name_en": "Land register extract",
     "description_de": "Aktueller Grundbuchauszug (max. 3 Monate alt)",
     "description_en": "Current land register extract (max. 3 months old)",
     "legal_basis": "Art. 68 Abs. 2 BayBO", "mandatory": True},
    {"id": "bauantrag", "name_de": "Bauantragsformular", "name_en": "Application form",
     "description_de": "Ausgefülltes amtliches Bauantragsformular",
     "description_en": "Completed official building permit application form",
     "legal_basis": "Art. 64 BayBO", "mandatory": True},
]


def build_vector_store() -> chromadb.Collection:
    """
    Loads BayBO content into an in-memory ChromaDB collection.
    Called once at service startup. Returns the collection ready for queries.
    """
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(
        name="baybo",
        metadata={"hnsw:space": "cosine"},
    )

    chunks = BAYBO_FALLBACK_CHUNKS

    # Try loading from PDF if available
    if os.path.exists(settings.baybo_pdf_path):
        try:
            pdf_chunks = _load_pdf_chunks(settings.baybo_pdf_path)
            if pdf_chunks:
                chunks = pdf_chunks
                print(f"Loaded {len(chunks)} chunks from BayBO PDF")
        except Exception as e:
            print(f"PDF load failed, using fallback: {e}")
    else:
        print(f"Using built-in BayBO articles ({len(chunks)} chunks)")

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"]} for c in chunks],
    )
    return collection


def _load_pdf_chunks(pdf_path: str) -> list[dict]:
    chunks = []
    chunk_id = 0
    with pdfplumber.open(pdf_path) as pdf:
        current_article = ""
        current_text = ""
        for page in pdf.pages:
            for line in (page.extract_text() or "").split("\n"):
                if re.match(r"^Art\.\s+\d+|^Artikel\s+\d+", line.strip()):
                    if current_text.strip():
                        for sub in _split_text(current_text.strip()):
                            chunks.append({"id": f"baybo_{chunk_id}", "text": sub, "source": current_article})
                            chunk_id += 1
                    current_article = line.strip()
                    current_text = line + "\n"
                else:
                    current_text += line + "\n"
        if current_text.strip():
            for sub in _split_text(current_text.strip()):
                chunks.append({"id": f"baybo_{chunk_id}", "text": sub, "source": current_article})
    return chunks


def _split_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            bp = text[end - 100:end].rfind(". ")
            if bp != -1:
                end = end - 100 + bp + 2
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if len(c) > 20]


def search_law(collection: chromadb.Collection, query: str) -> list[dict]:
    results = collection.query(query_texts=[query], n_results=min(settings.rag_top_k, collection.count()))
    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            chunks.append({"text": doc, "source": meta.get("source", "BayBO")})
    return chunks


def analyze_application(file_bytes: bytes, collection: chromadb.Collection, language: str = "de") -> dict:
    """
    Main RAG analysis: extracts text from PDF, finds relevant BayBO paragraphs,
    asks LLM to analyze the application against those specific laws.
    """
    # Extract text
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n\n".join(p.extract_text() or "" for p in pdf.pages).strip()
    except Exception:
        text = ""

    if not text:
        return {
            "overall_status": "prüfungsbedürftig",
            "findings": [{"type": "issue", "title": "Text nicht extrahierbar",
                "description": "Kein Text extrahierbar. Bitte als durchsuchbares PDF einreichen.",
                "legal_basis": "Art. 68 BayBO", "recommendation": "Dokument als natives PDF einreichen."}],
            "summary": "Automatische Prüfung nicht möglich.",
            "next_steps": ["Dokument als durchsuchbares PDF neu einreichen"],
            "rag_used": False, "law_chunks_consulted": 0,
        }

    # Find relevant law
    relevant = search_law(collection, text[:1000])

    law_text = "\n\n---\n\n".join(f"[{c['source']}]\n{c['text']}" for c in relevant)

    lang_map = {"en": "Reply in English.", "tr": "Yalnızca Türkçe yanıt verin.", "ar": "أجب باللغة العربية فقط."}
    lang_instruction = lang_map.get(language, "Antworte auf Deutsch.")

    prompt = f"""Du bist ein Sachbearbeiter der Bauaufsichtsbehörde Bayern.
{lang_instruction}
WICHTIG: Du unterstützt die Prüfung. Die Endentscheidung trifft der Sachbearbeiter.

RELEVANTE BayBO-GRUNDLAGEN:
{law_text}

ANTRAG (Auszug):
{text[:3000]}

Antworte NUR als JSON (kein Text außerhalb):
{{
  "overall_status": "vollständig" | "unvollständig" | "prüfungsbedürftig",
  "findings": [{{"type": "missing"|"issue"|"ok"|"info", "title": "...", "description": "...", "legal_basis": "...", "recommendation": "..."}}],
  "summary": "2-3 Sätze Gesamtzusammenfassung",
  "next_steps": ["Schritt 1", "Schritt 2"]
}}"""

    if not settings.llm_api_key:
        return {
            "overall_status": "prüfungsbedürftig",
            "findings": [{"type": "info", "title": "KI nicht konfiguriert",
                "description": "LLM_API_KEY nicht gesetzt. Qualitätsprüfung verfügbar.",
                "legal_basis": "N/A", "recommendation": "API-Schlüssel in Umgebungsvariablen setzen."}],
            "summary": "KI-Analyse nicht verfügbar. Manuelle Prüfung erforderlich.",
            "next_steps": ["API-Schlüssel konfigurieren"],
            "rag_used": False, "law_chunks_consulted": 0,
            "required_documents": REQUIRED_DOCUMENTS,
        }

    try:
        client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url,
                        default_headers={"X-Title": settings.llm_app_title})
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "Präziser juristischer Assistent für Bayern Baurecht. Antworte immer als valides JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)
        result["rag_used"] = True
        result["law_chunks_consulted"] = len(relevant)
        result["law_sources"] = [c["source"] for c in relevant]
        result["required_documents"] = REQUIRED_DOCUMENTS
        result["ai_model"] = settings.llm_model
        result["ai_notice"] = "KI-Unterstützung. Endentscheidung beim Sachbearbeiter."
        return result

    except json.JSONDecodeError:
        return {
            "overall_status": "prüfungsbedürftig",
            "findings": [{"type": "info", "title": "Analyse verfügbar (Textformat)",
                "description": raw[:1000] if 'raw' in dir() else "Fehler",
                "legal_basis": "Automatisch", "recommendation": "Manuelle Prüfung"}],
            "summary": "KI-Analyse konnte nicht strukturiert dargestellt werden.",
            "next_steps": ["Manuelle Prüfung"], "rag_used": True,
            "law_chunks_consulted": len(relevant), "required_documents": REQUIRED_DOCUMENTS,
        }
    except Exception as e:
        return {
            "overall_status": "prüfungsbedürftig",
            "findings": [{"type": "issue", "title": "KI-Service Fehler",
                "description": str(e), "legal_basis": "N/A", "recommendation": "Manuelle Prüfung"}],
            "summary": "KI nicht verfügbar.", "next_steps": ["Manuelle Prüfung"],
            "rag_used": False, "law_chunks_consulted": 0, "required_documents": REQUIRED_DOCUMENTS,
        }
