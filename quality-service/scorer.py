# =============================================================================
# scorer.py — PDF Quality Analysis Engine
# =============================================================================
# WHAT THIS FILE DOES:
# Analyzes a PDF document and produces a quality score from 0 to 100,
# plus specific warnings about problems found.
#
# WHY THIS MATTERS:
# Before a government worker opens a 150-page document, they should know:
# - Is this a readable native PDF or an unreadable blurry scan?
# - Are there blank pages wasting their time?
# - Is the file complete, or does it seem truncated?
#
# HOW THE SCORING WORKS:
# We start at 100 points and subtract points for each problem found.
# Every deduction is explained in plain language.
#
# IMPORTANTLY: This runs entirely without AI. It's pure document analysis.
# This means it's instant, free, and works even if the LLM is unavailable.
# =============================================================================

import io
import pdfplumber
from pypdf import PdfReader
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QualityIssue:
    """
    Represents one specific problem found in a document.

    severity:
        "critical" — document likely unusable (e.g., all pages blank)
        "warning"  — significant issue that needs attention
        "info"     — minor issue or observation
    """
    severity: str          # "critical", "warning", or "info"
    code: str              # Short machine-readable identifier (e.g., "BLANK_PAGES")
    message_de: str        # Human-readable description in German
    message_en: str        # Human-readable description in English
    points_deducted: int   # How much this issue reduces the score
    details: Optional[str] = None  # Additional technical detail


@dataclass
class QualityReport:
    """The complete quality report for one document."""
    score: int                          # 0-100, higher is better
    grade: str                          # A/B/C/D/F based on score
    is_native_pdf: bool                 # True = text is selectable; False = scanned image
    page_count: int
    has_extractable_text: bool
    issues: list[QualityIssue] = field(default_factory=list)
    summary_de: str = ""
    summary_en: str = ""


def _calculate_grade(score: int) -> str:
    """Converts a numeric score to a letter grade."""
    if score >= 90: return "A"
    if score >= 75: return "B"
    if score >= 60: return "C"
    if score >= 40: return "D"
    return "F"


def analyze_pdf(file_bytes: bytes) -> QualityReport:
    """
    Main function: analyzes a PDF and returns a QualityReport.

    Args:
        file_bytes: The raw bytes of the PDF file (already in memory, never on disk)

    Returns:
        A QualityReport with score, grade, issues, and explanations.
    """
    issues: list[QualityIssue] = []
    score = 100  # Start perfect, deduct for problems

    # ------------------------------------------------------------------
    # OPEN THE PDF
    # ------------------------------------------------------------------
    # io.BytesIO wraps the bytes in a "fake file" object.
    # pdfplumber expects a file, but we don't want to write to disk,
    # so we give it bytes pretending to be a file. This is a standard
    # Python pattern for in-memory file operations.
    pdf_buffer = io.BytesIO(file_bytes)

    try:
        plumber_pdf = pdfplumber.open(pdf_buffer)
        pypdf_reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as e:
        # If we can't even open it, it's either corrupted or not a real PDF
        return QualityReport(
            score=0,
            grade="F",
            is_native_pdf=False,
            page_count=0,
            has_extractable_text=False,
            issues=[QualityIssue(
                severity="critical",
                code="UNREADABLE_FILE",
                message_de="Datei konnte nicht geöffnet werden. Möglicherweise beschädigt.",
                message_en="File could not be opened. It may be corrupted.",
                points_deducted=100,
                details=str(e),
            )],
            summary_de="Dokument konnte nicht analysiert werden.",
            summary_en="Document could not be analyzed.",
        )

    page_count = len(plumber_pdf.pages)

    # ------------------------------------------------------------------
    # CHECK 1: Empty document
    # ------------------------------------------------------------------
    if page_count == 0:
        issues.append(QualityIssue(
            severity="critical",
            code="NO_PAGES",
            message_de="Das Dokument enthält keine Seiten.",
            message_en="The document contains no pages.",
            points_deducted=100,
        ))
        score = 0

    # ------------------------------------------------------------------
    # CHECK 2: Text extractability (native PDF vs scan)
    # ------------------------------------------------------------------
    # We sample up to 5 pages and try to extract text.
    # If we get meaningful text, it's a native PDF (good).
    # If we get nothing or just whitespace, it's a scanned image (bad).
    total_chars = 0
    blank_pages = []
    pages_to_sample = min(page_count, 5)

    for i in range(pages_to_sample):
        page = plumber_pdf.pages[i]
        text = page.extract_text() or ""
        char_count = len(text.strip())
        total_chars += char_count
        if char_count < 10:  # Fewer than 10 characters = effectively blank
            blank_pages.append(i + 1)  # Page numbers are 1-indexed for humans

    has_extractable_text = total_chars > 50
    is_native_pdf = has_extractable_text

    if not has_extractable_text:
        issues.append(QualityIssue(
            severity="critical",
            code="NO_TEXT_EXTRACTABLE",
            message_de=(
                "Kein Text extrahierbar. Das Dokument scheint ein eingescanntes Bild zu sein. "
                "OCR (Texterkennung) wird benötigt."
            ),
            message_en=(
                "No text could be extracted. The document appears to be a scanned image. "
                "OCR (optical character recognition) is required."
            ),
            points_deducted=40,
        ))
        score -= 40

    # ------------------------------------------------------------------
    # CHECK 3: Blank pages
    # ------------------------------------------------------------------
    if blank_pages and has_extractable_text:
        # Only flag blank pages if the document otherwise has text
        # (blank pages in a scanned doc are already caught above)
        issues.append(QualityIssue(
            severity="warning",
            code="BLANK_PAGES",
            message_de=f"Leere Seiten gefunden: {blank_pages}",
            message_en=f"Blank pages found: {blank_pages}",
            points_deducted=5 * len(blank_pages),
            details=f"Pages {blank_pages} appear to contain no text.",
        ))
        score -= 5 * len(blank_pages)

    # ------------------------------------------------------------------
    # CHECK 4: Very short document (potentially incomplete)
    # ------------------------------------------------------------------
    if page_count < 3 and page_count > 0:
        issues.append(QualityIssue(
            severity="warning",
            code="VERY_FEW_PAGES",
            message_de=(
                f"Das Dokument hat nur {page_count} Seite(n). "
                "Möglicherweise unvollständig."
            ),
            message_en=(
                f"The document has only {page_count} page(s). "
                "It may be incomplete."
            ),
            points_deducted=10,
        ))
        score -= 10

    # ------------------------------------------------------------------
    # CHECK 5: Check if PDF is encrypted/password-protected
    # ------------------------------------------------------------------
    if pypdf_reader.is_encrypted:
        issues.append(QualityIssue(
            severity="critical",
            code="ENCRYPTED",
            message_de=(
                "Das Dokument ist verschlüsselt oder passwortgeschützt. "
                "Es kann nicht automatisch verarbeitet werden."
            ),
            message_en=(
                "The document is encrypted or password-protected. "
                "It cannot be processed automatically."
            ),
            points_deducted=50,
        ))
        score -= 50

    # ------------------------------------------------------------------
    # CHECK 6: Check document metadata completeness
    # ------------------------------------------------------------------
    # PDF metadata can include author, creation date, title.
    # Missing metadata often indicates a hastily prepared document.
    metadata = pypdf_reader.metadata or {}
    missing_metadata = []
    if not metadata.get("/Title"):
        missing_metadata.append("Titel")
    if not metadata.get("/Author"):
        missing_metadata.append("Autor")
    if not metadata.get("/CreationDate"):
        missing_metadata.append("Erstellungsdatum")

    if len(missing_metadata) >= 2:
        issues.append(QualityIssue(
            severity="info",
            code="MISSING_METADATA",
            message_de=f"PDF-Metadaten unvollständig. Fehlend: {', '.join(missing_metadata)}",
            message_en=f"PDF metadata incomplete. Missing: {', '.join(missing_metadata)}",
            points_deducted=5,
        ))
        score -= 5

    # ------------------------------------------------------------------
    # CHECK 7: File size sanity check
    # ------------------------------------------------------------------
    size_kb = len(file_bytes) / 1024
    size_per_page_kb = size_kb / max(page_count, 1)

    if size_per_page_kb < 5 and not is_native_pdf:
        # Scanned PDFs should be at least 50-100KB per page for decent quality.
        # Under 5KB/page is suspiciously low resolution.
        issues.append(QualityIssue(
            severity="warning",
            code="LOW_RESOLUTION_LIKELY",
            message_de=(
                "Dateigröße pro Seite sehr gering. "
                "Bei einem Scan deutet dies auf sehr niedrige Auflösung hin."
            ),
            message_en=(
                "File size per page is very small. "
                "For a scanned document, this suggests very low resolution."
            ),
            points_deducted=15,
        ))
        score -= 15

    # ------------------------------------------------------------------
    # Ensure score doesn't go below 0
    # ------------------------------------------------------------------
    score = max(0, score)
    grade = _calculate_grade(score)

    # ------------------------------------------------------------------
    # Build summary text
    # ------------------------------------------------------------------
    if score >= 90:
        summary_de = "Sehr gute Dokumentqualität. Das Dokument ist gut für die automatische Verarbeitung geeignet."
        summary_en = "Excellent document quality. The document is well-suited for automated processing."
    elif score >= 75:
        summary_de = "Gute Dokumentqualität mit kleineren Problemen. Verarbeitung möglich."
        summary_en = "Good document quality with minor issues. Processing is possible."
    elif score >= 60:
        summary_de = "Ausreichende Dokumentqualität. Einige Probleme sollten behoben werden."
        summary_en = "Adequate document quality. Some issues should be addressed."
    elif score >= 40:
        summary_de = "Schlechte Dokumentqualität. Manuelle Überprüfung empfohlen."
        summary_en = "Poor document quality. Manual review recommended."
    else:
        summary_de = "Sehr schlechte Dokumentqualität. Dokument sollte neu eingereicht werden."
        summary_en = "Very poor document quality. Document should be resubmitted."

    plumber_pdf.close()

    return QualityReport(
        score=score,
        grade=grade,
        is_native_pdf=is_native_pdf,
        page_count=page_count,
        has_extractable_text=has_extractable_text,
        issues=issues,
        summary_de=summary_de,
        summary_en=summary_en,
    )
