# =============================================================================
# translations.py — Static UI translations + dynamic LLM translation
# =============================================================================
# Merged from translation-service/main.py.
# Static strings (buttons, labels) are returned instantly from dictionaries.
# Dynamic AI-generated text is translated by the LLM via Requesty.
# =============================================================================

from openai import OpenAI
from config import get_settings

settings = get_settings()

TRANSLATIONS: dict[str, dict] = {
    "de": {
        "app_title": "SPARK Bayern – Baugenehmigungsprüfung",
        "app_subtitle": "KI-gestützte Prüfung von Bauanträgen gemäß BayBO",
        "access_code_label": "Zugangscode",
        "access_code_placeholder": "Zugangscode eingeben",
        "access_code_submit": "Anmelden",
        "access_code_error": "Ungültiger Zugangscode. Bitte erneut versuchen.",
        "upload_title": "Dokument hochladen",
        "upload_instructions": "PDF-Datei hier ablegen oder klicken zum Auswählen",
        "upload_size_hint": "Maximale Dateigröße: 20 MB · Nur PDF",
        "upload_button": "Dokument prüfen",
        "upload_processing": "Dokument wird analysiert...",
        "quality_title": "Dokumentqualität",
        "quality_score_label": "Qualitätsbewertung",
        "quality_native_pdf": "Natives PDF",
        "quality_scanned": "Scan (OCR empfohlen)",
        "quality_pages": "Seiten",
        "quality_issues": "Probleme",
        "quality_no_issues": "Keine Qualitätsprobleme",
        "legal_title": "Rechtliche Prüfung (BayBO)",
        "legal_status_complete": "Vollständig",
        "legal_status_incomplete": "Unvollständig",
        "legal_status_review": "Prüfungsbedürftig",
        "legal_findings": "Befunde",
        "legal_summary": "Zusammenfassung",
        "legal_next_steps": "Nächste Schritte",
        "legal_basis": "Rechtsgrundlage",
        "legal_recommendation": "Empfehlung",
        "legal_sources": "Konsultierte BayBO-Artikel",
        "docs_title": "Erforderliche Unterlagen (Art. 68 BayBO)",
        "severity_critical": "Kritisch",
        "severity_warning": "Warnung",
        "severity_info": "Info",
        "ai_notice": "KI-Unterstützung – Endentscheidung beim Sachbearbeiter.",
        "gdpr_notice": "Datenschutz: Kein Dokument wird gespeichert.",
        "new_analysis": "Neue Prüfung",
        "rtl": False,
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
        "upload_size_hint": "Maximum file size: 20 MB · PDF only",
        "upload_button": "Analyze Document",
        "upload_processing": "Analyzing document...",
        "quality_title": "Document Quality",
        "quality_score_label": "Quality Score",
        "quality_native_pdf": "Native PDF",
        "quality_scanned": "Scan (OCR recommended)",
        "quality_pages": "Pages",
        "quality_issues": "Issues",
        "quality_no_issues": "No quality issues",
        "legal_title": "Legal Analysis (BayBO)",
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
        "severity_critical": "Critical",
        "severity_warning": "Warning",
        "severity_info": "Info",
        "ai_notice": "AI Assistance – Final decision rests with the case worker.",
        "gdpr_notice": "Privacy: No document is stored.",
        "new_analysis": "New Analysis",
        "rtl": False,
    },
    "tr": {
        "app_title": "SPARK Bayern – Yapı İzni Kontrolü",
        "app_subtitle": "BayBO kapsamında YZ destekli inceleme",
        "access_code_label": "Erişim Kodu",
        "access_code_placeholder": "Erişim kodunu girin",
        "access_code_submit": "Giriş",
        "access_code_error": "Geçersiz erişim kodu.",
        "upload_title": "Belge Yükle",
        "upload_instructions": "PDF dosyasını buraya bırakın",
        "upload_size_hint": "Maks. 20 MB · Yalnızca PDF",
        "upload_button": "Belgeyi Analiz Et",
        "upload_processing": "Analiz ediliyor...",
        "quality_title": "Belge Kalitesi",
        "quality_score_label": "Kalite Puanı",
        "quality_native_pdf": "Yerel PDF",
        "quality_scanned": "Tarama (OCR önerilir)",
        "quality_pages": "Sayfa",
        "quality_issues": "Sorunlar",
        "quality_no_issues": "Kalite sorunu yok",
        "legal_title": "Hukuki İnceleme (BayBO)",
        "legal_status_complete": "Tam",
        "legal_status_incomplete": "Eksik",
        "legal_status_review": "İnceleme Gerekli",
        "legal_findings": "Bulgular",
        "legal_summary": "Özet",
        "legal_next_steps": "Sonraki Adımlar",
        "legal_basis": "Hukuki Dayanak",
        "legal_recommendation": "Öneri",
        "legal_sources": "BayBO Maddeleri",
        "docs_title": "Gerekli Belgeler",
        "severity_critical": "Kritik",
        "severity_warning": "Uyarı",
        "severity_info": "Bilgi",
        "ai_notice": "YZ Desteği – Nihai karar yetkili memura aittir.",
        "gdpr_notice": "Gizlilik: Hiçbir belge saklanmaz.",
        "new_analysis": "Yeni Analiz",
        "rtl": False,
    },
    "ar": {
        "app_title": "SPARK Bayern – التحقق من تصريح البناء",
        "app_subtitle": "مراجعة بمساعدة الذكاء الاصطناعي وفق BayBO",
        "access_code_label": "رمز الدخول",
        "access_code_placeholder": "أدخل رمز الدخول",
        "access_code_submit": "تسجيل الدخول",
        "access_code_error": "رمز الدخول غير صحيح.",
        "upload_title": "رفع المستند",
        "upload_instructions": "أسقط ملف PDF هنا",
        "upload_size_hint": "الحجم الأقصى: 20 ميغابايت · PDF فقط",
        "upload_button": "تحليل المستند",
        "upload_processing": "جارٍ التحليل...",
        "quality_title": "جودة المستند",
        "quality_score_label": "درجة الجودة",
        "quality_native_pdf": "PDF أصلي",
        "quality_scanned": "مسح ضوئي (يُنصح بـ OCR)",
        "quality_pages": "الصفحات",
        "quality_issues": "المشكلات",
        "quality_no_issues": "لا توجد مشكلات",
        "legal_title": "التحليل القانوني (BayBO)",
        "legal_status_complete": "مكتمل",
        "legal_status_incomplete": "غير مكتمل",
        "legal_status_review": "يحتاج مراجعة",
        "legal_findings": "النتائج",
        "legal_summary": "الملخص",
        "legal_next_steps": "الخطوات التالية",
        "legal_basis": "الأساس القانوني",
        "legal_recommendation": "التوصية",
        "legal_sources": "مواد BayBO",
        "docs_title": "المستندات المطلوبة",
        "severity_critical": "حرج",
        "severity_warning": "تحذير",
        "severity_info": "معلومة",
        "ai_notice": "مساعدة الذكاء الاصطناعي – القرار النهائي للموظف المختص.",
        "gdpr_notice": "الخصوصية: لا يتم تخزين أي مستند.",
        "new_analysis": "تحليل جديد",
        "rtl": True,
    },
}


async def translate_text(text: str, target_language: str) -> str:
    """Translates German text to the target language via LLM."""
    if target_language == "de" or not settings.llm_api_key:
        return text
    lang_names = {"en": "English", "tr": "Turkish (Türkçe)", "ar": "Arabic (العربية)"}
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url,
                    default_headers={"X-Title": settings.llm_app_title})
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": (
                    f"Translate the following German administrative text to {lang_names.get(target_language, 'English')}. "
                    "Preserve all legal references (e.g., Art. 68 BayBO). Return only the translation."
                )},
                {"role": "user", "content": text[:3000]}
            ],
            temperature=0.2, max_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return text
