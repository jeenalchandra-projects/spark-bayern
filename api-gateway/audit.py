# =============================================================================
# audit.py — GDPR Audit Logging
# =============================================================================
# WHAT THIS FILE DOES:
# Records every action taken by the system: who uploaded what, when, and what
# happened. This is stored in memory only (never written to disk or database).
#
# WHY THIS EXISTS (GDPR Article 5(2) — Accountability):
# GDPR requires that organisations can demonstrate they are handling personal
# data correctly. An audit log proves:
# - When data was received
# - What was done with it
# - That it was NOT retained beyond its purpose
#
# WHAT WE LOG vs. WHAT WE DON'T:
# We log:   timestamps, document type, action performed, result summary
# We DON'T log: document content, names, addresses, personal identifiers
#
# The log lives only in memory (a Python list). It resets every time
# the service restarts. For production, this would go to an encrypted database.
# =============================================================================

from datetime import datetime, timezone
from typing import Optional
import uuid


# In-memory log storage — this is just a Python list.
# Each entry is a dictionary describing one action.
# When the server restarts, this list is cleared — intentional for GDPR.
_audit_log: list[dict] = []

# Maximum number of entries to keep in memory.
# Prevents unbounded memory growth during a long demo session.
MAX_LOG_ENTRIES = 1000


def log_event(
    action: str,
    document_type: Optional[str] = None,
    result_summary: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    language: Optional[str] = None,
) -> str:
    """
    Records one event in the audit log.

    Args:
        action: What happened. Examples: "upload_received", "quality_check",
                "completeness_check", "translation_requested", "result_delivered"
        document_type: The type of document (e.g., "Lageplan", "Bauzeichnung")
                       NOT the content — just the category.
        result_summary: A brief non-personal summary (e.g., "score: 85/100",
                        "3 missing documents identified")
        file_size_bytes: Size of the uploaded file (metadata only, no content)
        language: Which language was used (de/en/tr/ar)

    Returns:
        A unique event ID (UUID) for cross-referencing if needed.
    """
    event_id = str(uuid.uuid4())

    entry = {
        "event_id": event_id,
        # Always store time in UTC with timezone info — GDPR audit trails require this
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "action": action,
        # Only add optional fields if they were provided
        **({"document_type": document_type} if document_type else {}),
        **({"result_summary": result_summary} if result_summary else {}),
        **({"file_size_bytes": file_size_bytes} if file_size_bytes else {}),
        **({"language": language} if language else {}),
        # EXPLICIT NOTE: We record that no personal data was logged.
        # This is intentional documentation for GDPR compliance.
        "personal_data_logged": False,
    }

    # Add to log, but cap the size to prevent memory overflow
    _audit_log.append(entry)
    if len(_audit_log) > MAX_LOG_ENTRIES:
        # Remove the oldest entry (first in the list)
        _audit_log.pop(0)

    return event_id


def get_audit_log() -> list[dict]:
    """
    Returns a copy of the current audit log.
    We return a copy (not the original) so callers can't accidentally modify it.
    """
    return list(_audit_log)


def get_log_summary() -> dict:
    """
    Returns summary statistics about the current session.
    Useful for showing in the admin panel during a demo.
    """
    if not _audit_log:
        return {"total_events": 0, "session_started": None}

    action_counts: dict[str, int] = {}
    for entry in _audit_log:
        action = entry["action"]
        action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "total_events": len(_audit_log),
        "session_started": _audit_log[0]["timestamp_utc"],
        "latest_event": _audit_log[-1]["timestamp_utc"],
        "action_counts": action_counts,
        "personal_data_stored": False,  # Always false — this is our GDPR guarantee
        "data_retention_policy": "In-memory only. All data cleared on service restart.",
    }
