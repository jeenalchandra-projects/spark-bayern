// =============================================================================
// AccessGate.jsx — Passphrase entry screen
// =============================================================================
// The first screen the user sees. They must enter the correct passphrase
// before they can access the application.
// This satisfies GDPR Article 25 (data protection by design).
// =============================================================================

function AccessGate({ t, accessCode, setAccessCode, onSubmit, error }) {
  // Allow submitting with the Enter key (better UX than click-only)
  const handleKeyDown = (e) => {
    if (e.key === "Enter") onSubmit();
  };

  return (
    <div className="screen access-gate">
      <div className="access-card">

        {/* Logo / branding */}
        <div className="access-logo">
          <div className="logo-badge">SPARK</div>
          <div className="logo-sub">Bayern</div>
        </div>

        {/* Title */}
        <h1 className="access-title">{t.app_title}</h1>
        <p className="access-subtitle">{t.app_subtitle}</p>

        {/* Passphrase input */}
        <div className="input-group">
          <label htmlFor="access-code">{t.access_code_label}</label>
          <input
            id="access-code"
            type="password"
            value={accessCode}
            onChange={(e) => setAccessCode(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t.access_code_placeholder}
            autoFocus
            autoComplete="off"
          />
        </div>

        {/* Error message */}
        {error && <div className="error-msg">{error}</div>}

        {/* Submit button */}
        <button className="btn-primary" onClick={onSubmit}>
          {t.access_code_submit}
        </button>

        {/* GDPR notice at bottom */}
        <p className="gdpr-notice">{t.gdpr_notice}</p>
      </div>
    </div>
  );
}

export default AccessGate;
