// =============================================================================
// ResultsScreen.jsx — Analysis results dashboard
// =============================================================================
// Shows the combined results from quality analysis and legal RAG analysis.
// Uses a traffic-light system (green/yellow/red) for visual status indicators.
// =============================================================================

function ResultsScreen({ t, results, language, onNewAnalysis }) {
  const quality = results?.quality || {};
  const legal = results?.legal_analysis || {};

  // -------------------------------------------------------------------------
  // TRAFFIC LIGHT COLORS
  // -------------------------------------------------------------------------
  // We map scores and statuses to colors for instant visual feedback.

  const getQualityColor = (score) => {
    if (score >= 75) return "green";
    if (score >= 50) return "yellow";
    return "red";
  };

  const getLegalColor = (status) => {
    if (status === "vollständig" || status === "complete") return "green";
    if (status === "prüfungsbedürftig" || status === "needs review") return "yellow";
    return "red";
  };

  const getSeverityColor = (severity) => {
    if (severity === "critical") return "red";
    if (severity === "warning") return "yellow";
    return "blue";
  };

  const getFindingColor = (type) => {
    if (type === "ok") return "green";
    if (type === "missing" || type === "issue") return "red";
    return "blue";
  };

  const getFindingIcon = (type) => {
    if (type === "ok") return "✓";
    if (type === "missing") return "✗";
    if (type === "issue") return "⚠";
    return "ℹ";
  };

  const getStatusLabel = (status) => {
    const map = {
      vollständig: t.legal_status_complete,
      unvollständig: t.legal_status_incomplete,
      prüfungsbedürftig: t.legal_status_review,
      complete: t.legal_status_complete,
      incomplete: t.legal_status_incomplete,
    };
    return map[status] || status;
  };

  return (
    <div className="screen results-screen">
      <div className="results-container">

        {/* Header with overall traffic light */}
        <div className="results-header">
          <div className="logo-badge small">SPARK</div>
          <h1>Bayern Baugenehmigung</h1>

          {/* Overall status indicator */}
          <div className={`status-badge ${getLegalColor(legal.overall_status)}`}>
            {getStatusLabel(legal.overall_status)}
          </div>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* SECTION 1: DOCUMENT QUALITY                                       */}
        {/* ---------------------------------------------------------------- */}
        <section className="result-section">
          <h2>{t.quality_title}</h2>

          <div className="quality-grid">
            {/* Score circle */}
            <div className={`score-circle ${getQualityColor(quality.score || 0)}`}>
              <span className="score-number">{quality.score ?? "—"}</span>
              <span className="score-label">{quality.grade ?? ""}</span>
            </div>

            {/* Quality metadata */}
            <div className="quality-meta">
              <div className="meta-item">
                <span className="meta-icon">{quality.is_native_pdf ? "✓" : "⚠"}</span>
                <span>{quality.is_native_pdf ? t.quality_native_pdf : t.quality_scanned}</span>
              </div>
              <div className="meta-item">
                <span className="meta-icon">📄</span>
                <span>{quality.page_count ?? "—"} {t.quality_pages}</span>
              </div>
            </div>

            {/* Summary */}
            <div className="quality-summary">
              <p>{language === "de" ? quality.summary_de : quality.summary_en}</p>
            </div>
          </div>

          {/* Quality issues */}
          {quality.issues && quality.issues.length > 0 ? (
            <div className="issues-list">
              <h3>{t.quality_issues}</h3>
              {quality.issues.map((issue, i) => (
                <div key={i} className={`issue-card ${getSeverityColor(issue.severity)}`}>
                  <div className="issue-header">
                    <span className={`severity-badge ${getSeverityColor(issue.severity)}`}>
                      {t[`severity_${issue.severity}`] || issue.severity}
                    </span>
                    <span className="issue-code">{issue.code}</span>
                    <span className="points-deducted">-{issue.points_deducted} Punkte</span>
                  </div>
                  <p>{language === "de" ? issue.message_de : issue.message_en}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-issues">✓ {t.quality_no_issues}</p>
          )}
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* SECTION 2: LEGAL ANALYSIS                                         */}
        {/* ---------------------------------------------------------------- */}
        <section className="result-section">
          <h2>{t.legal_title}</h2>

          {/* Summary */}
          {legal.summary && (
            <div className="legal-summary">
              <p>{legal.summary}</p>
            </div>
          )}

          {/* Findings */}
          {legal.findings && legal.findings.length > 0 && (
            <div className="findings-list">
              <h3>{t.legal_findings}</h3>
              {legal.findings.map((finding, i) => (
                <div key={i} className={`finding-card ${getFindingColor(finding.type)}`}>
                  <div className="finding-icon">{getFindingIcon(finding.type)}</div>
                  <div className="finding-content">
                    <h4>{finding.title}</h4>
                    <p>{finding.description}</p>
                    {finding.legal_basis && (
                      <div className="finding-meta">
                        <span className="label">{t.legal_basis}:</span>
                        <span className="legal-basis">{finding.legal_basis}</span>
                      </div>
                    )}
                    {finding.recommendation && (
                      <div className="finding-meta">
                        <span className="label">{t.legal_recommendation}:</span>
                        <span>{finding.recommendation}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Next steps */}
          {legal.next_steps && legal.next_steps.length > 0 && (
            <div className="next-steps">
              <h3>{t.legal_next_steps}</h3>
              <ol>
                {legal.next_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          )}

          {/* Law sources consulted */}
          {legal.law_sources && legal.law_sources.length > 0 && (
            <div className="law-sources">
              <h3>{t.legal_sources}</h3>
              <ul>
                {legal.law_sources.map((src, i) => (
                  <li key={i} className="law-source">{src}</li>
                ))}
              </ul>
            </div>
          )}

          {/* RAG metadata */}
          {legal.rag_used && (
            <div className="rag-badge">
              ⚖️ RAG — {legal.law_chunks_consulted} BayBO-Abschnitte konsultiert
            </div>
          )}
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* SECTION 3: REQUIRED DOCUMENTS CHECKLIST                           */}
        {/* ---------------------------------------------------------------- */}
        {legal.required_documents && (
          <section className="result-section">
            <h2>{t.docs_title}</h2>
            <div className="docs-grid">
              {legal.required_documents.map((doc) => (
                <div key={doc.id} className="doc-card">
                  <div className="doc-icon">📋</div>
                  <div className="doc-info">
                    <strong>{language === "de" ? doc.name_de : doc.name_en}</strong>
                    <p>{language === "de" ? doc.description_de : doc.description_en}</p>
                    <span className="doc-legal-basis">{doc.legal_basis}</span>
                  </div>
                  {doc.mandatory && (
                    <span className="mandatory-badge">{t.docs_mandatory}</span>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* COMPLIANCE NOTICES                                                 */}
        {/* ---------------------------------------------------------------- */}
        <div className="compliance-bar">
          <p>⚖️ {results?.ai_notice?.[language === "de" ? "de" : "en"] || t.ai_notice}</p>
          <p>🔒 {results?.gdpr_notice?.[language === "de" ? "de" : "en"] || t.gdpr_notice}</p>
        </div>

        {/* New analysis button */}
        <button className="btn-primary" onClick={onNewAnalysis}>
          ← {t.new_analysis}
        </button>

      </div>
    </div>
  );
}

export default ResultsScreen;
