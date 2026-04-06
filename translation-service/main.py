# =============================================================================
# main.py — Translation Service
# =============================================================================
# WHAT THIS FILE DOES:
# Translates AI-generated analysis results and UI text into German, English,
# Turkish, and Arabic using the LLM via Requesty.
#
# TWO TYPES OF TRANSLATION:
# 1. STATIC TEXT — Labels, buttons, fixed messages
#    These are stored in translation dictionaries in this file.
#    No LLM needed. Instant and free.
#
# 2. DYNAMIC TEXT — AI-generated analysis results (findings, summaries)
#    These vary per document and cannot be pre-translated.
#    The LLM translates these on demand.
#
# ARABIC SPECIAL HANDLING:
# Arabic is written right-to-left (RTL). We add a flag to the response
# so the frontend knows to apply RTL CSS layout.
# =============================================================================

import os
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://router.requesty.ai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral/mistral-large-latest")
LLM_APP_TITLE = os.getenv("LLM_APP_TITLE", "SPARK-Bayern")


# =============================================================================
# STATIC TRANSLATIONS
# =============================================================================
# All fixed UI text in all four languages.
# Keys are language-independent identifiers.
# Values are the translated strings.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "de": {
        # App-wide
        "app_title": "SPARK Bayern – Baugenehmigungsprüfung",
        "app_subtitle": "KI-gestützte Prüfung von Bauanträgen gemäß BayBO",

        # Access gate
        "access_code_label": "Zugangscode",
        "access_code_placeholder": "Zugangscode eingeben",
        "access_code_submit": "Anmelden",
        "access_code_error": "Ungültiger Zugangscode. Bitte erneut versuchen.",

        # Upload
        "upload_title": "Dokument hochladen",
        "upload_instructions": "PDF-Datei hier ablegen oder klicken zum Auswählen",
        "upload_size_hint": "Maximale Dateigröße: 20 MB",
        "upload_button": "Dokument prüfen",
        "upload_processing": "Dokument wird analysiert...",

        # Quality section
        "quality_title": "Dokumentqualität",
        "quality_score_label": "Qualitätsbewertung",
        "quality_native_pdf": "Natives PDF (Text extrahierbar)",
        "quality_scanned": "Scan (Text nicht direkt extrahierbar)",
        "quality_pages": "Seiten",
        "quality_issues": "Gefundene Probleme",
        "quality_no_issues": "Keine Qualitätsprobleme gefunden",

        # Legal analysis section
        "legal_title": "Rechtliche Prüfung",
        "legal_status_complete": "Vollständig",
        "legal_status_incomplete": "Unvollständig",
        "legal_status_review": "Prüfungsbedürftig",
        "legal_findings": "Befunde",
        "legal_summary": "Zusammenfassung",
        "legal_next_steps": "Nächste Schritte",
        "legal_basis": "Rechtsgrundlage",
        "legal_recommendation": "Empfehlung",
        "legal_sources": "Konsultierte BayBO-Artikel",

        # Required documents
        "docs_title": "Erforderliche Unterlagen (Art. 68 BayBO)",
        "docs_mandatory": "Pflichtdokument",

        # Severity labels
        "severity_critical": "Kritisch",
        "severity_warning": "Warnung",
        "severity_info": "Information",
        "finding_type_missing": "Fehlend",
        "finding_type_issue": "Problem",
        "finding_type_ok": "In Ordnung",
        "finding_type_info": "Information",

        # Footer / Legal notices
        "ai_notice": "KI-Unterstützung — Die Endentscheidung liegt beim Sachbearbeiter.",
        "gdpr_notice": "Datenschutz: Dieses Dokument wird nicht gespeichert. Alle Daten werden nach der Verarbeitung gelöscht.",
        "eu_ai_act_notice": "EU-KI-Gesetz: Dieses System dient als Entscheidungsunterstützung. Ein Mensch trifft die finale Entscheidung.",

        # Audit log
        "audit_title": "Sitzungsprotokoll (Audit-Log)",
        "audit_no_events": "Noch keine Ereignisse in dieser Sitzung.",

        # Errors
        "error_upload_failed": "Upload fehlgeschlagen. Bitte erneut versuchen.",
        "error_file_too_large": "Datei zu groß. Maximale Größe: 20 MB.",
        "error_not_pdf": "Nur PDF-Dateien werden akzeptiert.",
        "error_service_unavailable": "Dienst vorübergehend nicht verfügbar.",
    },
    "en": {
        "app_title": "SPARK Bayern – Building Permit Checker",
        "app_subtitle": "AI-assisted review of building permit applications under BayBO",
        "access_code_label": "Access Code",
        "access_code_placeholder": "Enter access code",
        "access_code_submit": "Log in",
        "access_code_error": "Invalid access code. Please try again.",
        "upload_title": "Upload Document",
        "upload_instructions": "Drop PDF file here or click to select",
        "upload_size_hint": "Maximum file size: 20 MB",
        "upload_button": "Analyze Document",
        "upload_processing": "Analyzing document...",
        "quality_title": "Document Quality",
        "quality_score_label": "Quality Score",
        "quality_native_pdf": "Native PDF (text extractable)",
        "quality_scanned": "Scan (text not directly extractable)",
        "quality_pages": "Pages",
        "quality_issues": "Issues Found",
        "quality_no_issues": "No quality issues found",
        "legal_title": "Legal Analysis",
        "legal_status_complete": "Complete",
        "legal_status_incomplete": "Incomplete",
        "legal_status_review": "Needs Review",
        "legal_findings": "Findings",
        "legal_summary": "Summary",
        "legal_next_steps": "Next Steps",
        "legal_basis": "Legal Basis",
        "legal_recommendation": "Recommendation",
        "legal_sources": "BayBO Articles Consulted",
        "docs_title": "Required Documents (Art. 68 BayBO)",
        "docs_mandatory": "Mandatory document",
        "severity_critical": "Critical",
        "severity_warning": "Warning",
        "severity_info": "Information",
        "finding_type_missing": "Missing",
        "finding_type_issue": "Issue",
        "finding_type_ok": "OK",
        "finding_type_info": "Info",
        "ai_notice": "AI Assistance — The final decision rests with the case worker.",
        "gdpr_notice": "Privacy: This document is not stored. All data is deleted after processing.",
        "eu_ai_act_notice": "EU AI Act: This system serves as decision support. A human makes the final decision.",
        "audit_title": "Session Log (Audit Trail)",
        "audit_no_events": "No events in this session yet.",
        "error_upload_failed": "Upload failed. Please try again.",
        "error_file_too_large": "File too large. Maximum size: 20 MB.",
        "error_not_pdf": "Only PDF files are accepted.",
        "error_service_unavailable": "Service temporarily unavailable.",
    },
    "tr": {
        "app_title": "SPARK Bayern – Yapı İzni Kontrolü",
        "app_subtitle": "BayBO kapsamında yapı izni başvurularının YZ destekli incelemesi",
        "access_code_label": "Erişim Kodu",
        "access_code_placeholder": "Erişim kodunu girin",
        "access_code_submit": "Giriş",
        "access_code_error": "Geçersiz erişim kodu. Lütfen tekrar deneyin.",
        "upload_title": "Belge Yükle",
        "upload_instructions": "PDF dosyasını buraya bırakın veya seçmek için tıklayın",
        "upload_size_hint": "Maksimum dosya boyutu: 20 MB",
        "upload_button": "Belgeyi Analiz Et",
        "upload_processing": "Belge analiz ediliyor...",
        "quality_title": "Belge Kalitesi",
        "quality_score_label": "Kalite Puanı",
        "quality_native_pdf": "Yerel PDF (metin çıkarılabilir)",
        "quality_scanned": "Tarama (metin doğrudan çıkarılamaz)",
        "quality_pages": "Sayfa",
        "quality_issues": "Bulunan Sorunlar",
        "quality_no_issues": "Kalite sorunu bulunamadı",
        "legal_title": "Hukuki İnceleme",
        "legal_status_complete": "Tam",
        "legal_status_incomplete": "Eksik",
        "legal_status_review": "İnceleme Gerekli",
        "legal_findings": "Bulgular",
        "legal_summary": "Özet",
        "legal_next_steps": "Sonraki Adımlar",
        "legal_basis": "Hukuki Dayanak",
        "legal_recommendation": "Öneri",
        "legal_sources": "Başvurulan BayBO Maddeleri",
        "docs_title": "Gerekli Belgeler (Mad. 68 BayBO)",
        "docs_mandatory": "Zorunlu belge",
        "severity_critical": "Kritik",
        "severity_warning": "Uyarı",
        "severity_info": "Bilgi",
        "finding_type_missing": "Eksik",
        "finding_type_issue": "Sorun",
        "finding_type_ok": "Tamam",
        "finding_type_info": "Bilgi",
        "ai_notice": "YZ Desteği — Nihai karar yetkili memura aittir.",
        "gdpr_notice": "Gizlilik: Bu belge saklanmamaktadır. Tüm veriler işlendikten sonra silinir.",
        "eu_ai_act_notice": "AB YZ Yasası: Bu sistem karar desteği olarak hizmet verir. Nihai kararı bir insan verir.",
        "audit_title": "Oturum Günlüğü",
        "audit_no_events": "Bu oturumda henüz olay yok.",
        "error_upload_failed": "Yükleme başarısız. Lütfen tekrar deneyin.",
        "error_file_too_large": "Dosya çok büyük. Maksimum boyut: 20 MB.",
        "error_not_pdf": "Yalnızca PDF dosyaları kabul edilmektedir.",
        "error_service_unavailable": "Hizmet geçici olarak kullanılamıyor.",
    },
    "ar": {
        "app_title": "SPARK Bayern – التحقق من تصريح البناء",
        "app_subtitle": "مراجعة طلبات تصاريح البناء بمساعدة الذكاء الاصطناعي وفق BayBO",
        "access_code_label": "رمز الدخول",
        "access_code_placeholder": "أدخل رمز الدخول",
        "access_code_submit": "تسجيل الدخول",
        "access_code_error": "رمز الدخول غير صحيح. يرجى المحاولة مرة أخرى.",
        "upload_title": "رفع المستند",
        "upload_instructions": "أسقط ملف PDF هنا أو انقر للاختيار",
        "upload_size_hint": "الحجم الأقصى للملف: 20 ميغابايت",
        "upload_button": "تحليل المستند",
        "upload_processing": "جارٍ تحليل المستند...",
        "quality_title": "جودة المستند",
        "quality_score_label": "درجة الجودة",
        "quality_native_pdf": "PDF أصلي (يمكن استخراج النص)",
        "quality_scanned": "مسح ضوئي (لا يمكن استخراج النص مباشرة)",
        "quality_pages": "الصفحات",
        "quality_issues": "المشكلات المكتشفة",
        "quality_no_issues": "لم يتم العثور على مشكلات في الجودة",
        "legal_title": "التحليل القانوني",
        "legal_status_complete": "مكتمل",
        "legal_status_incomplete": "غير مكتمل",
        "legal_status_review": "يحتاج إلى مراجعة",
        "legal_findings": "النتائج",
        "legal_summary": "الملخص",
        "legal_next_steps": "الخطوات التالية",
        "legal_basis": "الأساس القانوني",
        "legal_recommendation": "التوصية",
        "legal_sources": "مواد BayBO المُستشارة",
        "docs_title": "المستندات المطلوبة (المادة 68 BayBO)",
        "docs_mandatory": "مستند إلزامي",
        "severity_critical": "حرج",
        "severity_warning": "تحذير",
        "severity_info": "معلومة",
        "finding_type_missing": "مفقود",
        "finding_type_issue": "مشكلة",
        "finding_type_ok": "موافق",
        "finding_type_info": "معلومة",
        "ai_notice": "مساعدة الذكاء الاصطناعي — القرار النهائي يعود للموظف المختص.",
        "gdpr_notice": "الخصوصية: لا يتم تخزين هذا المستند. تُحذف جميع البيانات بعد المعالجة.",
        "eu_ai_act_notice": "قانون الذكاء الاصطناعي الأوروبي: يعمل هذا النظام كدعم للقرار. الإنسان هو من يتخذ القرار النهائي.",
        "audit_title": "سجل الجلسة",
        "audit_no_events": "لا توجد أحداث في هذه الجلسة حتى الآن.",
        "error_upload_failed": "فشل الرفع. يرجى المحاولة مرة أخرى.",
        "error_file_too_large": "الملف كبير جداً. الحجم الأقصى: 20 ميغابايت.",
        "error_not_pdf": "يُقبل فقط ملفات PDF.",
        "error_service_unavailable": "الخدمة غير متوفرة مؤقتاً.",
        "rtl": "true",  # Flag for the frontend to apply RTL layout
    },
}


app = FastAPI(
    title="SPARK-Bayern Translation Service",
    description="Provides static UI translations and dynamic LLM-based translation for DE/EN/TR/AR.",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "translation-service"}


@app.get("/ui-translations/{language}")
async def get_ui_translations(language: str):
    """
    Returns all static UI translations for the requested language.
    Falls back to German if the language is not supported.
    """
    if language not in TRANSLATIONS:
        language = "de"
    return {
        "language": language,
        "rtl": language == "ar",  # Arabic is right-to-left
        "translations": TRANSLATIONS[language],
    }


@app.post("/translate")
async def translate_text(
    target_language: str = Form(...),
    text: str = Form(...),
):
    """
    Translates dynamic text (AI-generated results) to the target language.
    Uses the LLM via Requesty.

    Args:
        target_language: One of "de", "en", "tr", "ar"
        text: The text to translate (analysis results, summaries, findings)
    """
    if target_language == "de":
        # No translation needed — source is already German
        return {"translated_text": text, "language": "de"}

    if not LLM_API_KEY:
        return {"translated_text": text, "language": target_language, "error": "LLM not configured"}

    language_names = {
        "en": "English",
        "tr": "Turkish (Türkçe)",
        "ar": "Arabic (العربية)",
    }
    target_name = language_names.get(target_language, "English")

    client = OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        default_headers={"X-Title": LLM_APP_TITLE},
    )

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a professional translator specializing in German administrative and legal texts. "
                        f"Translate the following German text to {target_name}. "
                        f"Preserve all technical terms, article references (e.g., Art. 68 BayBO), "
                        f"and the formal tone. Return only the translation, no explanations."
                    )
                },
                {"role": "user", "content": text[:3000]}  # Limit to avoid token overflow
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        translated = response.choices[0].message.content.strip()
        return {
            "translated_text": translated,
            "language": target_language,
            "rtl": target_language == "ar",
        }
    except Exception as e:
        # If translation fails, return the original text
        return {
            "translated_text": text,
            "language": "de",
            "error": str(e),
        }
