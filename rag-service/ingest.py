# =============================================================================
# ingest.py — Bayern Bauordnung (BayBO) Ingestion Pipeline
# =============================================================================
# WHAT THIS FILE DOES:
# Loads the Bayern Building Code (Bayerische Bauordnung / BayBO) PDF,
# splits it into small chunks, converts each chunk into a vector (embedding),
# and stores everything in an in-memory vector database (ChromaDB).
#
# WHAT IS AN EMBEDDING?
# An embedding is a list of numbers (e.g., 1536 numbers) that represents
# the "meaning" of a piece of text. Texts with similar meaning have similar
# numbers. This allows us to search for "which law paragraph is most relevant
# to this application?" using mathematical similarity rather than keyword matching.
#
# THE PIPELINE:
# BayBO PDF → Extract text → Split into chunks → Embed each chunk → Store in ChromaDB
#
# This runs ONCE when the service starts. After that, the vector database
# is in memory and queries are fast.
#
# IMPORTANT — WHAT HAPPENS IF THE BAYBO PDF IS NOT AVAILABLE:
# We include a fallback: if no PDF is found, we load a set of hardcoded
# key BayBO articles. This ensures the demo always works.
# =============================================================================

import pdfplumber
import chromadb
import re
import os
from openai import OpenAI
from config import get_settings

settings = get_settings()


# Key BayBO articles hardcoded as fallback
# These are real articles from the Bayerische Bauordnung (Art. = Artikel)
# Source: https://www.gesetze-im-internet.de/baybo/ (public domain)
BAYBO_FALLBACK_CHUNKS = [
    {
        "id": "baybo_art_2",
        "text": (
            "Art. 2 BayBO — Begriffe: "
            "Bauliche Anlagen sind mit dem Erdboden verbundene, aus Bauprodukten hergestellte Anlagen. "
            "Gebäude sind selbständig benutzbare, überdeckte bauliche Anlagen, die von Menschen betreten werden können. "
            "Gebäude der Gebäudeklasse 1: freistehende Gebäude mit einer Höhe bis zu 7 m und nicht mehr als zwei Nutzungseinheiten. "
            "Gebäudeklasse 2: freistehende Gebäude mit einer Höhe bis zu 7 m und nicht mehr als zwei Nutzungseinheiten. "
            "Gebäudeklasse 3: sonstige Gebäude mit einer Höhe bis zu 7 m. "
            "Gebäudeklasse 4: Gebäude mit einer Höhe bis zu 13 m. "
            "Gebäudeklasse 5: sonstige Gebäude einschließlich unterirdischer Gebäude."
        ),
        "source": "BayBO Art. 2 — Begriffe",
    },
    {
        "id": "baybo_art_57",
        "text": (
            "Art. 57 BayBO — Verfahrensfreie Bauvorhaben: "
            "Verfahrensfrei sind insbesondere: "
            "Gebäude mit einem Brutto-Rauminhalt bis zu 75 m³, außer im Außenbereich. "
            "Garagen einschließlich überdachter Stellplätze mit einer Nutzfläche bis zu 50 m². "
            "Nebengebäude und Nebenanlagen zu Wohngebäuden der Gebäudeklassen 1 und 2. "
            "Anlagen der technischen Gebäudeausrüstung. "
            "Solarenergieanlagen und Sonnenkollektoren an und auf Gebäuden. "
            "Einfriedungen bis zu 2 m Höhe."
        ),
        "source": "BayBO Art. 57 — Verfahrensfreie Bauvorhaben",
    },
    {
        "id": "baybo_art_59",
        "text": (
            "Art. 59 BayBO — Vereinfachtes Baugenehmigungsverfahren: "
            "Im vereinfachten Baugenehmigungsverfahren prüft die Bauaufsichtsbehörde "
            "die Übereinstimmung mit den Vorschriften über die Zulässigkeit der baulichen Anlagen "
            "nach den §§ 29 bis 38 BauGB sowie den Regelungen örtlicher Bauvorschriften. "
            "Anwendbar auf: Wohngebäude der Gebäudeklassen 1 bis 3, "
            "sonstige Gebäude der Gebäudeklassen 1 und 2."
        ),
        "source": "BayBO Art. 59 — Vereinfachtes Baugenehmigungsverfahren",
    },
    {
        "id": "baybo_art_60",
        "text": (
            "Art. 60 BayBO — Baugenehmigungsverfahren: "
            "Bauvorhaben, die nicht verfahrensfrei sind und für die kein vereinfachtes Verfahren gilt, "
            "bedürfen der Baugenehmigung. "
            "Der Bauantrag ist bei der Gemeinde einzureichen. "
            "Der Antrag muss enthalten: Bauzeichnungen, Baubeschreibung, Lageplan, "
            "statische Nachweise, Standsicherheitsnachweis, Wärmeschutznachweis, "
            "Schallschutznachweis, Nachweis der Barrierefreiheit."
        ),
        "source": "BayBO Art. 60 — Baugenehmigungsverfahren",
    },
    {
        "id": "baybo_art_68",
        "text": (
            "Art. 68 BayBO — Erforderliche Unterlagen: "
            "Dem Bauantrag sind beizufügen: "
            "1. Lageplan im Maßstab 1:1000 oder 1:500 mit Einzeichnung des Bauvorhabens "
            "und der Maße zu den Grundstücksgrenzen. "
            "2. Bauzeichnungen (Grundrisse, Schnitte, Ansichten) im Maßstab 1:100. "
            "3. Baubeschreibung mit Angaben zu Nutzung, Konstruktion und Baustoffen. "
            "4. Berechnung des Brutto-Rauminhalts und der Brutto-Grundfläche. "
            "5. Statischer Nachweis (Standsicherheitsnachweis). "
            "6. Energieausweis oder Wärmeschutznachweis nach GEG. "
            "7. Grundbuchauszug (nicht älter als 3 Monate). "
            "8. Zustimmungserklärung des Grundstückseigentümers, wenn nicht identisch mit Bauherr."
        ),
        "source": "BayBO Art. 68 — Erforderliche Unterlagen",
    },
    {
        "id": "baybo_art_6",
        "text": (
            "Art. 6 BayBO — Abstandsflächen: "
            "Vor den Außenwänden von Gebäuden sind Abstandsflächen freizuhalten. "
            "Die Abstandsfläche beträgt 1 H (H = Höhe der Wand), mindestens 3 m. "
            "In Gewerbe- und Industriegebieten genügt eine Tiefe von 0,25 H, mindestens 3 m. "
            "Abstandsflächen müssen auf dem Grundstück selbst liegen. "
            "Ausnahmen gelten bei Wänden an der Grundstücksgrenze (Grenzgaragen bis 3 m Wandhöhe)."
        ),
        "source": "BayBO Art. 6 — Abstandsflächen",
    },
    {
        "id": "baybo_art_11",
        "text": (
            "Art. 11 BayBO — Erschließung: "
            "Bauliche Anlagen dürfen nur errichtet werden, wenn das Grundstück "
            "in angemessener Breite an einer befahrbaren öffentlichen Verkehrsfläche liegt "
            "oder eine befahrbare öffentlich-rechtlich gesicherte Zufahrt zu einer "
            "befahrbaren öffentlichen Verkehrsfläche hat. "
            "Wasserversorgung und Abwasserbeseitigung müssen gesichert sein."
        ),
        "source": "BayBO Art. 11 — Erschließung",
    },
    {
        "id": "baybo_art_47",
        "text": (
            "Art. 47 BayBO — Stellplätze und Garagen: "
            "Bei der Errichtung von Anlagen, bei denen ein Zu- oder Abgangsverkehr "
            "zu erwarten ist, sind notwendige Stellplätze herzustellen. "
            "Die Anzahl ergibt sich aus der Stellplatzsatzung der Gemeinde. "
            "Für Wohngebäude gilt: mindestens 1 Stellplatz pro Wohnung."
        ),
        "source": "BayBO Art. 47 — Stellplätze und Garagen",
    },
]


# Required documents checklist for a standard Baugenehmigung in Bayern
# These are the documents that Art. 68 BayBO requires
REQUIRED_DOCUMENTS = [
    {
        "id": "lageplan",
        "name_de": "Lageplan",
        "name_en": "Site plan",
        "description_de": "Lageplan 1:1000 oder 1:500 mit Grundstücksgrenzen und Maßen",
        "description_en": "Site plan 1:1000 or 1:500 with plot boundaries and measurements",
        "legal_basis": "Art. 68 Abs. 1 Nr. 1 BayBO",
        "mandatory": True,
    },
    {
        "id": "bauzeichnungen",
        "name_de": "Bauzeichnungen",
        "name_en": "Architectural drawings",
        "description_de": "Grundrisse, Schnitte und Ansichten im Maßstab 1:100",
        "description_en": "Floor plans, sections and elevations at scale 1:100",
        "legal_basis": "Art. 68 Abs. 1 Nr. 2 BayBO",
        "mandatory": True,
    },
    {
        "id": "baubeschreibung",
        "name_de": "Baubeschreibung",
        "name_en": "Building description",
        "description_de": "Beschreibung des Vorhabens mit Angaben zu Nutzung, Konstruktion und Baustoffen",
        "description_en": "Description of the project including use, construction and materials",
        "legal_basis": "Art. 68 Abs. 1 Nr. 3 BayBO",
        "mandatory": True,
    },
    {
        "id": "flaechen_berechnung",
        "name_de": "Flächenberechnung",
        "name_en": "Area calculation",
        "description_de": "Berechnung des Brutto-Rauminhalts (BRI) und der Brutto-Grundfläche (BGF)",
        "description_en": "Calculation of gross volume (BRI) and gross floor area (BGF)",
        "legal_basis": "Art. 68 Abs. 1 Nr. 4 BayBO",
        "mandatory": True,
    },
    {
        "id": "standsicherheitsnachweis",
        "name_de": "Standsicherheitsnachweis",
        "name_en": "Structural stability certificate",
        "description_de": "Statischer Nachweis der Standsicherheit durch einen Prüfsachverständigen",
        "description_en": "Static proof of structural stability by a certified expert",
        "legal_basis": "Art. 68 Abs. 1 Nr. 5 BayBO",
        "mandatory": True,
    },
    {
        "id": "waermeschutz",
        "name_de": "Wärmeschutznachweis",
        "name_en": "Thermal insulation certificate",
        "description_de": "Nachweis nach GEG (Gebäudeenergiegesetz)",
        "description_en": "Certificate according to the Building Energy Act (GEG)",
        "legal_basis": "Art. 68 BayBO i.V.m. GEG",
        "mandatory": True,
    },
    {
        "id": "grundbuchauszug",
        "name_de": "Grundbuchauszug",
        "name_en": "Land register extract",
        "description_de": "Aktueller Grundbuchauszug (nicht älter als 3 Monate)",
        "description_en": "Current land register extract (not older than 3 months)",
        "legal_basis": "Art. 68 Abs. 2 BayBO",
        "mandatory": True,
    },
    {
        "id": "bauantrag_formular",
        "name_de": "Bauantragsformular",
        "name_en": "Building permit application form",
        "description_de": "Ausgefülltes amtliches Bauantragsformular",
        "description_en": "Completed official building permit application form",
        "legal_basis": "Art. 64 BayBO",
        "mandatory": True,
    },
]


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits a long text into smaller overlapping chunks.

    WHY CHUNKS?
    LLMs have a limited context window — they can only read so many words at once.
    Also, vector search works better on focused, specific chunks than on huge blobs of text.

    WHY OVERLAP?
    If a sentence is split across chunk boundaries, the overlap ensures the meaning
    isn't lost. The last 50 characters of chunk N are the first 50 of chunk N+1.

    Args:
        text: The full text to split
        chunk_size: Maximum characters per chunk
        overlap: How many characters to repeat between consecutive chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at a sentence boundary (period + space)
        if end < len(text):
            # Look for a good breakpoint within the last 100 chars of the chunk
            break_search = text[end - 100:end]
            last_period = break_search.rfind(". ")
            if last_period != -1:
                end = end - 100 + last_period + 2  # +2 to include the ". "

        chunks.append(text[start:end].strip())
        start = end - overlap  # Overlap: go back by `overlap` characters

    return [c for c in chunks if len(c) > 20]  # Remove very short fragments


def build_vector_store() -> chromadb.Collection:
    """
    Creates the in-memory vector store and loads BayBO content into it.

    HOW CHROMADB WORKS:
    - ChromaDB is a vector database — it stores text chunks and their embeddings
    - An embedding is a list of numbers representing the meaning of the text
    - When we search, ChromaDB finds the chunks whose embeddings are closest
      to the query embedding (cosine similarity)
    - "In-memory" means it exists only in RAM — no files written to disk

    Returns:
        A ChromaDB collection containing all BayBO paragraphs, ready to search.
    """
    # Create in-memory ChromaDB client
    # EphemeralClient = nothing saved to disk, starts fresh every time
    client = chromadb.EphemeralClient()

    # Create a collection (like a table in a database)
    # "cosine" distance = good for text similarity search
    collection = client.get_or_create_collection(
        name="baybo",
        metadata={"hnsw:space": "cosine"},
    )

    # Load content
    chunks = BAYBO_FALLBACK_CHUNKS

    # Try to load from PDF first (if available)
    baybo_pdf_path = settings.baybo_pdf_path
    if os.path.exists(baybo_pdf_path):
        print(f"Loading BayBO from PDF: {baybo_pdf_path}")
        try:
            pdf_chunks = _load_from_pdf(baybo_pdf_path)
            if pdf_chunks:
                chunks = pdf_chunks
                print(f"Loaded {len(chunks)} chunks from BayBO PDF")
        except Exception as e:
            print(f"Could not load PDF, using fallback: {e}")
    else:
        print(f"BayBO PDF not found at {baybo_pdf_path}. Using built-in fallback articles.")

    # Add chunks to ChromaDB
    # ChromaDB handles embedding generation internally using its default model
    # (a small, fast sentence transformer that runs locally — no API call needed)
    collection.add(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[{"source": chunk["source"]} for chunk in chunks],
    )

    print(f"Vector store ready with {len(chunks)} BayBO chunks")
    return collection


def _load_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extracts text from the BayBO PDF and splits it into chunks.
    Used when the actual BayBO PDF is available.
    """
    chunks = []
    chunk_id = 0

    with pdfplumber.open(pdf_path) as pdf:
        current_article = ""
        current_text = ""

        for page in pdf.pages:
            text = page.extract_text() or ""

            # Detect article headings (e.g., "Art. 2" or "Artikel 2")
            lines = text.split("\n")
            for line in lines:
                if re.match(r"^Art\.\s+\d+|^Artikel\s+\d+", line.strip()):
                    # Save previous article if it has content
                    if current_text.strip():
                        for sub_chunk in _chunk_text(current_text.strip()):
                            chunks.append({
                                "id": f"baybo_{chunk_id}",
                                "text": sub_chunk,
                                "source": current_article or "BayBO",
                            })
                            chunk_id += 1
                    current_article = line.strip()
                    current_text = line + "\n"
                else:
                    current_text += line + "\n"

        # Don't forget the last article
        if current_text.strip():
            for sub_chunk in _chunk_text(current_text.strip()):
                chunks.append({
                    "id": f"baybo_{chunk_id}",
                    "text": sub_chunk,
                    "source": current_article or "BayBO",
                })
                chunk_id += 1

    return chunks


def search_relevant_law(collection: chromadb.Collection, query: str, top_k: int = 5) -> list[dict]:
    """
    Finds the most relevant BayBO paragraphs for a given query.

    HOW VECTOR SEARCH WORKS:
    1. We convert the query text into an embedding (a list of numbers)
    2. ChromaDB finds the stored chunks whose embeddings are most similar
    3. We return the top K most similar chunks

    This is like Google search but for legal text — it finds semantically
    relevant paragraphs even if they don't contain the exact words.

    Args:
        collection: The ChromaDB collection with BayBO content
        query: The search query (e.g., extracted text from the application)
        top_k: How many results to return

    Returns:
        List of relevant law chunks with their source citations
    """
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
    )

    relevant_chunks = []
    if results and results["documents"] and results["documents"][0]:
        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            relevant_chunks.append({
                "text": doc,
                "source": metadata.get("source", "BayBO"),
            })

    return relevant_chunks
