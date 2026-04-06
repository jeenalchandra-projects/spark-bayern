// =============================================================================
// UploadScreen.jsx — Document upload and analysis trigger
// =============================================================================
// Shows a drag-and-drop upload area. When a PDF is dropped or selected,
// it calls the onAnalyze handler (defined in App.jsx) which sends it to the API.
// =============================================================================

import { useState, useRef } from "react";

function UploadScreen({ t, onAnalyze, isLoading, error }) {
  // isDragging: true when user drags a file over the drop zone (for visual feedback)
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  // useRef creates a reference to the hidden file input element
  // We use it to programmatically open the file picker when the user clicks
  const fileInputRef = useRef(null);

  // -------------------------------------------------------------------------
  // DRAG AND DROP HANDLERS
  // -------------------------------------------------------------------------
  // Browsers trigger these events when a file is dragged over an element.

  const handleDragOver = (e) => {
    e.preventDefault(); // Required to allow dropping
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0]; // Get the first dropped file
    if (file) handleFileSelected(file);
  };

  // -------------------------------------------------------------------------
  // FILE SELECTION
  // -------------------------------------------------------------------------
  const handleFileSelected = (file) => {
    // Only accept PDF files
    if (file.type !== "application/pdf" && !file.name.endsWith(".pdf")) {
      return; // Let the API handle the error with a proper message
    }
    setSelectedFile(file);
  };

  const handleInputChange = (e) => {
    const file = e.target.files[0];
    if (file) handleFileSelected(file);
  };

  const handleSubmit = () => {
    if (selectedFile) onAnalyze(selectedFile);
  };

  return (
    <div className="screen upload-screen">
      <div className="upload-container">

        {/* Header */}
        <div className="screen-header">
          <div className="logo-badge small">SPARK</div>
          <h1>{t.upload_title}</h1>
        </div>

        {/* Drop zone */}
        <div
          className={`drop-zone ${isDragging ? "dragging" : ""} ${selectedFile ? "has-file" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !selectedFile && fileInputRef.current?.click()}
        >
          {/* Hidden actual file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleInputChange}
            style={{ display: "none" }}
          />

          {selectedFile ? (
            // Show selected file info
            <div className="file-selected">
              <div className="file-icon">📄</div>
              <div className="file-name">{selectedFile.name}</div>
              <div className="file-size">
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
              </div>
              <button
                className="btn-text"
                onClick={(e) => {
                  e.stopPropagation(); // Don't re-open file picker
                  setSelectedFile(null);
                }}
              >
                ✕
              </button>
            </div>
          ) : (
            // Show upload instructions
            <div className="drop-instructions">
              <div className="drop-icon">⬆</div>
              <p>{t.upload_instructions}</p>
              <p className="hint">{t.upload_size_hint}</p>
            </div>
          )}
        </div>

        {/* Error message */}
        {error && <div className="error-msg">{error}</div>}

        {/* Analyze button */}
        <button
          className="btn-primary btn-large"
          onClick={handleSubmit}
          disabled={!selectedFile || isLoading}
        >
          {isLoading ? (
            <span className="loading-spinner">
              <span className="spinner" />
              {t.upload_processing}
            </span>
          ) : (
            t.upload_button
          )}
        </button>

        {/* AI + GDPR notices */}
        <div className="notices">
          <p className="ai-notice">⚖️ {t.ai_notice}</p>
          <p className="gdpr-notice">🔒 {t.gdpr_notice}</p>
        </div>

      </div>
    </div>
  );
}

export default UploadScreen;
