import { useState, useEffect } from "react";
import axios from "axios";
import { translations, supportedLanguages } from "./translations";
import AccessGate from "./components/AccessGate";
import UploadScreen from "./components/UploadScreen";
import ResultsScreen from "./components/ResultsScreen";
import "./App.css";

// The API Gateway URL — resolved in this priority order:
// 1. window.SPARK_CONFIG.apiUrl  → set by docker-entrypoint.sh at runtime (Railway)
// 2. import.meta.env.VITE_API_URL → set at build time (local dev fallback)
// 3. "http://localhost:8000"      → hardcoded fallback for development
const API_BASE_URL =
  window?.SPARK_CONFIG?.apiUrl ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

function App() {
  // -------------------------------------------------------------------------
  // STATE — variables that control what the UI shows
  // useState(initialValue) returns [currentValue, setterFunction]
  // When you call setterFunction, React re-renders the component
  // -------------------------------------------------------------------------
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessCode, setAccessCode] = useState("");
  const [accessError, setAccessError] = useState("");
  const [language, setLanguage] = useState("de");
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  // "t" = current translations — shorthand for translations[language]
  const t = translations[language];

  // -------------------------------------------------------------------------
  // RTL support for Arabic — runs every time language changes
  // -------------------------------------------------------------------------
  useEffect(() => {
    document.documentElement.dir = t.rtl ? "rtl" : "ltr";
    document.documentElement.lang = language;
  }, [language, t.rtl]);

  // -------------------------------------------------------------------------
  // HANDLER: Verify passphrase
  // -------------------------------------------------------------------------
  const handleVerifyAccess = async () => {
    setAccessError("");
    try {
      await axios.post(
        `${API_BASE_URL}/verify-access`,
        {},
        { headers: { "X-Access-Code": accessCode } }
      );
      setIsAuthenticated(true);
    } catch {
      setAccessError(t.access_code_error);
    }
  };

  // -------------------------------------------------------------------------
  // HANDLER: Upload PDF and trigger analysis
  // -------------------------------------------------------------------------
  const handleAnalyze = async (file) => {
    setUploadError("");
    setResults(null);
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("language", language);

      const response = await axios.post(
        `${API_BASE_URL}/analyze`,
        formData,
        {
          headers: {
            "X-Access-Code": accessCode,
            "Content-Type": "multipart/form-data",
          },
        }
      );
      setResults(response.data);
    } catch (error) {
      if (error.response?.status === 413) {
        setUploadError(t.error_file_too_large || "File too large");
      } else if (error.response?.status === 415) {
        setUploadError(t.error_not_pdf || "Only PDFs accepted");
      } else {
        setUploadError(t.error_upload_failed || "Upload failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewAnalysis = () => {
    setResults(null);
    setUploadError("");
  };

  // -------------------------------------------------------------------------
  // RENDER — what the user sees
  // -------------------------------------------------------------------------
  return (
    <div className={`app ${t.rtl ? "rtl" : "ltr"}`}>

      {/* Language switcher — always visible at top */}
      <div className="language-bar">
        {supportedLanguages.map((lang) => (
          <button
            key={lang.code}
            className={`lang-btn ${language === lang.code ? "active" : ""}`}
            onClick={() => setLanguage(lang.code)}
          >
            {lang.flag} {lang.label}
          </button>
        ))}
      </div>

      {/* Screen 1: Not logged in */}
      {!isAuthenticated && (
        <AccessGate
          t={t}
          accessCode={accessCode}
          setAccessCode={setAccessCode}
          onSubmit={handleVerifyAccess}
          error={accessError}
        />
      )}

      {/* Screen 2: Logged in, no results yet */}
      {isAuthenticated && !results && (
        <UploadScreen
          t={t}
          onAnalyze={handleAnalyze}
          isLoading={isLoading}
          error={uploadError}
        />
      )}

      {/* Screen 3: Results available */}
      {isAuthenticated && results && (
        <ResultsScreen
          t={t}
          results={results}
          language={language}
          onNewAnalysis={handleNewAnalysis}
        />
      )}

    </div>
  );
}

export default App;
