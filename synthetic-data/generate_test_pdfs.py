#!/usr/bin/env python3
# =============================================================================
# generate_test_pdfs.py — Creates 3 synthetic test PDFs for the demo
# =============================================================================
# WHAT THIS DOES:
# Creates three realistic-looking Bayern Baugenehmigung documents:
#   1. vollstaendig.pdf  — A complete application (should score well)
#   2. unvollstaendig.pdf — An incomplete application (missing documents)
#   3. schlechte_qualitaet.pdf — Simulates a poor quality scan
#
# These are entirely fake. All names, addresses, and parcel numbers are invented.
# They exist so the demo can run without ever uploading real personal data.
#
# HOW TO RUN:
#   cd synthetic-data
#   pip install reportlab
#   python generate_test_pdfs.py
#
# After running, you'll have three .pdf files in this directory.
# =============================================================================

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
import os

# Output directory = same folder as this script
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Color palette
BAVARIAN_BLUE = HexColor("#1a3a6b")
LIGHT_BLUE = HexColor("#e8f0fe")
GRAY = HexColor("#64748b")
LIGHT_GRAY = HexColor("#f1f5f9")

def make_styles():
    """Returns a dict of paragraph styles."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontSize=16, fontName="Helvetica-Bold",
                                 textColor=BAVARIAN_BLUE, spaceAfter=6),
        "subtitle": ParagraphStyle("subtitle", fontSize=11, fontName="Helvetica",
                                    textColor=GRAY, spaceAfter=16),
        "heading": ParagraphStyle("heading", fontSize=12, fontName="Helvetica-Bold",
                                   textColor=BAVARIAN_BLUE, spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body", fontSize=10, fontName="Helvetica",
                                leading=16, spaceAfter=8),
        "small": ParagraphStyle("small", fontSize=8, fontName="Helvetica",
                                 textColor=GRAY, spaceAfter=4),
        "bold": ParagraphStyle("bold", fontSize=10, fontName="Helvetica-Bold", spaceAfter=4),
    }


# ===========================================================================
# DOCUMENT 1: Complete application — should pass all checks
# ===========================================================================
def create_vollstaendig():
    """
    Creates a complete, well-formatted Bayern Baugenehmigung application.
    Contains all required documents referenced in the text.
    Should achieve a high quality score and legal analysis result.
    """
    path = os.path.join(OUT_DIR, "vollstaendig.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2*cm)
    s = make_styles()
    story = []

    # --- Header ---
    story.append(Paragraph("Freistaat Bayern", s["small"]))
    story.append(Paragraph("Landratsamt Musterstadt", s["small"]))
    story.append(Paragraph("Bauaufsichtsbehörde", s["small"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=BAVARIAN_BLUE))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("BAUANTRAG", s["title"]))
    story.append(Paragraph(
        "gemäß Art. 64 Bayerische Bauordnung (BayBO) — Vollständige Unterlagen",
        s["subtitle"]
    ))

    # --- Applicant info ---
    story.append(Paragraph("1. Angaben zum Bauherren", s["heading"]))
    data = [
        ["Name:", "Max Mustermann"],
        ["Vorname:", "Max"],
        ["Straße:", "Musterstraße 42"],
        ["PLZ / Ort:", "80331 München"],
        ["Telefon:", "+49 89 12345678"],
        ["E-Mail:", "m.mustermann@example.com"],
    ]
    t = Table(data, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t)

    # --- Project description ---
    story.append(Paragraph("2. Beschreibung des Bauvorhabens", s["heading"]))
    story.append(Paragraph(
        "Errichtung eines Einfamilienhauses (Gebäudeklasse 1) mit Garage auf dem Grundstück "
        "Flurstück 123/45 in der Gemarkung Musterstadt, Gemeinde Musterstadt, Landkreis Muster. "
        "Das Bauvorhaben umfasst ein freistehendes Wohngebäude mit Satteldach, Keller, "
        "Erdgeschoss und Dachgeschoss. Die Brutto-Grundfläche beträgt 180 m², "
        "der Brutto-Rauminhalt 720 m³.",
        s["body"]
    ))

    # --- Property details ---
    story.append(Paragraph("3. Grundstücksdaten", s["heading"]))
    data2 = [
        ["Flurstück:", "123/45"],
        ["Gemarkung:", "Musterstadt"],
        ["Gemeinde:", "Musterstadt"],
        ["Landkreis:", "Muster"],
        ["Grundstücksfläche:", "650 m²"],
        ["Bebauungsplan:", "B-Plan Nr. 12 — Wohngebiet"],
        ["Nutzungsart:", "Allgemeines Wohngebiet (WA) gem. § 4 BauNVO"],
    ]
    t2 = Table(data2, colWidths=[5*cm, 10*cm])
    t2.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t2)

    # --- Attached documents (Art. 68 BayBO) ---
    story.append(Paragraph("4. Verzeichnis der beigefügten Unterlagen (Art. 68 BayBO)", s["heading"]))
    story.append(Paragraph(
        "Folgende Unterlagen sind dem Bauantrag beigefügt:", s["body"]
    ))

    docs = [
        ["✓", "Lageplan 1:500", "Art. 68 Abs. 1 Nr. 1 BayBO", "Anlage 1"],
        ["✓", "Bauzeichnungen (Grundrisse, Schnitte, Ansichten) 1:100", "Art. 68 Abs. 1 Nr. 2 BayBO", "Anlage 2"],
        ["✓", "Baubeschreibung", "Art. 68 Abs. 1 Nr. 3 BayBO", "Anlage 3"],
        ["✓", "Flächenberechnung (BGF: 180 m², BRI: 720 m³)", "Art. 68 Abs. 1 Nr. 4 BayBO", "Anlage 4"],
        ["✓", "Standsicherheitsnachweis", "Art. 68 Abs. 1 Nr. 5 BayBO", "Anlage 5"],
        ["✓", "Wärmeschutznachweis nach GEG", "Art. 68 BayBO i.V.m. GEG", "Anlage 6"],
        ["✓", "Grundbuchauszug (Datum: 15.03.2026)", "Art. 68 Abs. 2 BayBO", "Anlage 7"],
        ["✓", "Zustimmungserklärung Grundstückseigentümer", "Art. 68 BayBO", "Anlage 8"],
        ["✓", "Nachweis Stellplätze (2 PKW-Stellplätze)", "Art. 47 BayBO", "Anlage 9"],
        ["✓", "Erschließungsnachweis (Wasserver-/Abwasserentsorgung)", "Art. 11 BayBO", "Anlage 10"],
    ]
    doc_table = Table(docs, colWidths=[0.8*cm, 7.5*cm, 5*cm, 2.5*cm])
    doc_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0,0), (0,-1), colors.green),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 5),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(doc_table)

    # --- Abstandsflächen ---
    story.append(Paragraph("5. Abstandsflächen (Art. 6 BayBO)", s["heading"]))
    story.append(Paragraph(
        "Wandhöhe Nordseite: 6,50 m → Abstandsfläche: 6,50 m (1H) ✓ (Mindestabstand 3,00 m eingehalten)\n"
        "Wandhöhe Südseite: 5,80 m → Abstandsfläche: 5,80 m (1H) ✓\n"
        "Alle Abstandsflächen liegen auf dem Baugrundstück. Grenzgarage: Wandhöhe 2,50 m ✓ (unter 3m).",
        s["body"]
    ))

    # --- Signature ---
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("München, den 01. April 2026", s["body"]))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("_______________________________", s["body"]))
    story.append(Paragraph("Max Mustermann (Bauherr)", s["small"]))

    # --- Footer note ---
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "HINWEIS: Dies ist ein synthetisches Testdokument. Alle Personen, Adressen und "
        "Grundstücksdaten sind frei erfunden. Ausschließlich für Demo-Zwecke.",
        s["small"]
    ))

    doc.build(story)
    print(f"✓ Created: {path}")


# ===========================================================================
# DOCUMENT 2: Incomplete application — missing several required documents
# ===========================================================================
def create_unvollstaendig():
    """
    Creates an incomplete application missing 4 required documents.
    The RAG analysis should identify exactly what's missing.
    """
    path = os.path.join(OUT_DIR, "unvollstaendig.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2*cm)
    s = make_styles()
    story = []

    story.append(Paragraph("Gemeinde Musterberg", s["small"]))
    story.append(Paragraph("Bauantrag — Vereinfachtes Verfahren", s["small"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=BAVARIAN_BLUE))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("BAUANTRAG (UNVOLLSTÄNDIG)", s["title"]))
    story.append(Paragraph(
        "Erweiterung eines Wohngebäudes — Art. 59 BayBO — Vereinfachtes Verfahren",
        s["subtitle"]
    ))

    story.append(Paragraph("1. Bauherr", s["heading"]))
    story.append(Paragraph("Anna Beispiel, Bergstraße 7, 85354 Freising", s["body"]))

    story.append(Paragraph("2. Vorhaben", s["heading"]))
    story.append(Paragraph(
        "Anbau eines Wintergartens (15 m²) an ein bestehendes Einfamilienhaus. "
        "Gebäudeklasse 1. Flurstück 99/3, Gemarkung Freising.",
        s["body"]
    ))

    story.append(Paragraph("3. Beigefügte Unterlagen", s["heading"]))
    story.append(Paragraph(
        "WARNUNG: Die folgenden Unterlagen fehlen und wurden NICHT beigefügt:",
        ParagraphStyle("warn", fontSize=10, fontName="Helvetica-Bold",
                        textColor=colors.red, spaceAfter=8)
    ))

    docs = [
        ["✓", "Lageplan 1:500", "Beigefügt"],
        ["✓", "Grundriss Erdgeschoss 1:100", "Beigefügt"],
        ["✗", "Baubeschreibung", "FEHLT — Art. 68 Abs. 1 Nr. 3 BayBO"],
        ["✗", "Flächenberechnung (BGF/BRI)", "FEHLT — Art. 68 Abs. 1 Nr. 4 BayBO"],
        ["✗", "Standsicherheitsnachweis", "FEHLT — Art. 68 Abs. 1 Nr. 5 BayBO"],
        ["✗", "Wärmeschutznachweis (GEG)", "FEHLT — Art. 68 BayBO i.V.m. GEG"],
        ["✗", "Grundbuchauszug", "FEHLT — Art. 68 Abs. 2 BayBO"],
    ]
    doc_table = Table(docs, colWidths=[0.8*cm, 7*cm, 7.5*cm])
    doc_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0,0), (0,0), colors.green),
        ("TEXTCOLOR", (0,1), (0,1), colors.green),
        ("TEXTCOLOR", (0,2), (0,-1), colors.red),
        ("TEXTCOLOR", (2,2), (2,-1), colors.red),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(doc_table)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Freising, den 01. April 2026", s["body"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "HINWEIS: Synthetisches Testdokument. Alle Daten frei erfunden. Nur für Demo-Zwecke.",
        s["small"]
    ))

    doc.build(story)
    print(f"✓ Created: {path}")


# ===========================================================================
# DOCUMENT 3: Poor quality — simulates a badly scanned document
# ===========================================================================
def create_schlechte_qualitaet():
    """
    Creates a very minimal document that simulates a bad scan.
    Only 1 page with minimal text — the quality scorer should flag issues.
    """
    path = os.path.join(OUT_DIR, "schlechte_qualitaet.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2*cm)
    s = make_styles()
    story = []

    story.append(Paragraph("Bauantrag", s["title"]))
    story.append(Spacer(1, 0.5*cm))
    # Very sparse content — simulates a nearly empty scan
    story.append(Paragraph("Antragsteller: Unbekannt", s["body"]))
    story.append(Paragraph("Vorhaben: Anbau", s["body"]))
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(
        "HINWEIS: Dieses Dokument hat absichtlich wenig Inhalt, um ein schlechtes Scan-Dokument "
        "zu simulieren. Der Qualitäts-Scorer sollte dies als niedrige Qualität einstufen. "
        "Synthetisches Testdokument.",
        s["small"]
    ))

    doc.build(story)
    print(f"✓ Created: {path}")


if __name__ == "__main__":
    print("Generating synthetic test PDFs...")
    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        print("ERROR: reportlab not installed. Run: pip install reportlab")
        exit(1)

    create_vollstaendig()
    create_unvollstaendig()
    create_schlechte_qualitaet()
    print("\nDone! Three test PDFs created in synthetic-data/")
    print("  vollstaendig.pdf      — Complete application (demo: should pass)")
    print("  unvollstaendig.pdf    — Missing documents (demo: should flag issues)")
    print("  schlechte_qualitaet.pdf — Poor quality (demo: quality scorer)")
