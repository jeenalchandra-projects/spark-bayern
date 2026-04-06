# =============================================================================
# quality.py — PDF Quality Scorer
# =============================================================================
# Merged from quality-service/scorer.py.
# Analyzes a PDF and returns a quality score 0-100 with specific issues.
# Runs entirely without AI — fast, free, always available.
# =============================================================================

import io
import pdfplumber
from pypdf import PdfReader
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QualityIssue:
    severity: str        # "critical", "warning", "info"
    code: str
    message_de: str
    message_en: str
    points_deducted: int
    details: Optional[str] = None


@dataclass
class QualityReport:
    score: int
    grade: str
    is_native_pdf: bool
    page_count: int
    has_extractable_text: bool
    issues: list[QualityIssue] = field(default_factory=list)
    summary_de: str = ""
    summary_en: str = ""


def _grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 75: return "B"
    if score >= 60: return "C"
    if score >= 40: return "D"
    return "F"


def analyze_pdf(file_bytes: bytes) -> QualityReport:
    """
    Analyzes a PDF in memory and returns a QualityReport.
    No disk writes. No AI calls.
    """
    issues: list[QualityIssue] = []
    score = 100

    pdf_buffer = io.BytesIO(file_bytes)
    try:
        plumber_pdf = pdfplumber.open(pdf_buffer)
        pypdf_reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as e:
        return QualityReport(
            score=0, grade="F", is_native_pdf=False, page_count=0,
            has_extractable_text=False,
            issues=[QualityIssue(
                severity="critical", code="UNREADABLE_FILE",
                message_de="Datei konnte nicht geöffnet werden. Möglicherweise beschädigt.",
                message_en="File could not be opened. It may be corrupted.",
                points_deducted=100, details=str(e),
            )],
            summary_de="Dokument konnte nicht analysiert werden.",
            summary_en="Document could not be analyzed.",
        )

    page_count = len(plumber_pdf.pages)

    if page_count == 0:
        issues.append(QualityIssue(severity="critical", code="NO_PAGES",
            message_de="Das Dokument enthält keine Seiten.",
            message_en="The document contains no pages.", points_deducted=100))
        score = 0

    # Text extractability check
    total_chars = 0
    blank_pages = []
    for i in range(min(page_count, 5)):
        text = plumber_pdf.pages[i].extract_text() or ""
        char_count = len(text.strip())
        total_chars += char_count
        if char_count < 10:
            blank_pages.append(i + 1)

    has_extractable_text = total_chars > 50
    is_native_pdf = has_extractable_text

    if not has_extractable_text:
        issues.append(QualityIssue(severity="critical", code="NO_TEXT_EXTRACTABLE",
            message_de="Kein Text extrahierbar. Das Dokument scheint ein eingescanntes Bild zu sein. OCR wird benötigt.",
            message_en="No text could be extracted. The document appears to be a scanned image. OCR is required.",
            points_deducted=40))
        score -= 40

    if blank_pages and has_extractable_text:
        issues.append(QualityIssue(severity="warning", code="BLANK_PAGES",
            message_de=f"Leere Seiten gefunden: {blank_pages}",
            message_en=f"Blank pages found: {blank_pages}",
            points_deducted=5 * len(blank_pages)))
        score -= 5 * len(blank_pages)

    if 0 < page_count < 3:
        issues.append(QualityIssue(severity="warning", code="VERY_FEW_PAGES",
            message_de=f"Das Dokument hat nur {page_count} Seite(n). Möglicherweise unvollständig.",
            message_en=f"The document has only {page_count} page(s). It may be incomplete.",
            points_deducted=10))
        score -= 10

    if pypdf_reader.is_encrypted:
        issues.append(QualityIssue(severity="critical", code="ENCRYPTED",
            message_de="Das Dokument ist verschlüsselt und kann nicht automatisch verarbeitet werden.",
            message_en="The document is encrypted and cannot be processed automatically.",
            points_deducted=50))
        score -= 50

    metadata = pypdf_reader.metadata or {}
    missing_meta = [f for f, k in [("Titel", "/Title"), ("Autor", "/Author"), ("Datum", "/CreationDate")]
                    if not metadata.get(k)]
    if len(missing_meta) >= 2:
        issues.append(QualityIssue(severity="info", code="MISSING_METADATA",
            message_de=f"PDF-Metadaten unvollständig. Fehlend: {', '.join(missing_meta)}",
            message_en=f"PDF metadata incomplete. Missing: {', '.join(missing_meta)}",
            points_deducted=5))
        score -= 5

    size_kb = len(file_bytes) / 1024
    if (size_kb / max(page_count, 1)) < 5 and not is_native_pdf:
        issues.append(QualityIssue(severity="warning", code="LOW_RESOLUTION_LIKELY",
            message_de="Dateigröße pro Seite sehr gering. Wahrscheinlich niedrige Scan-Auflösung.",
            message_en="File size per page very small. Likely low scan resolution.",
            points_deducted=15))
        score -= 15

    score = max(0, score)

    if score >= 90:
        summary_de = "Sehr gute Dokumentqualität. Gut für automatische Verarbeitung geeignet."
        summary_en = "Excellent quality. Well-suited for automated processing."
    elif score >= 75:
        summary_de = "Gute Qualität mit kleineren Problemen. Verarbeitung möglich."
        summary_en = "Good quality with minor issues. Processing is possible."
    elif score >= 60:
        summary_de = "Ausreichende Qualität. Einige Probleme sollten behoben werden."
        summary_en = "Adequate quality. Some issues should be addressed."
    elif score >= 40:
        summary_de = "Schlechte Qualität. Manuelle Überprüfung empfohlen."
        summary_en = "Poor quality. Manual review recommended."
    else:
        summary_de = "Sehr schlechte Qualität. Dokument sollte neu eingereicht werden."
        summary_en = "Very poor quality. Document should be resubmitted."

    plumber_pdf.close()
    return QualityReport(score=score, grade=_grade(score), is_native_pdf=is_native_pdf,
                         page_count=page_count, has_extractable_text=has_extractable_text,
                         issues=issues, summary_de=summary_de, summary_en=summary_en)
