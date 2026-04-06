# =============================================================================
# auth.py — Passphrase-based access control
# =============================================================================
# WHAT THIS FILE DOES:
# Every request that comes into the API Gateway must include the demo passphrase.
# If it doesn't, or if the passphrase is wrong, the request is rejected with
# a 401 Unauthorized error.
#
# WHY THIS EXISTS (GDPR Article 25 — Data Protection by Design):
# The app processes real government documents containing personal data
# (names, addresses, parcel numbers). Deploying it with no access control
# would mean anyone on the internet could upload or view that data.
# This passphrase gate ensures only authorised users (government workers
# attending the demo) can access the system.
#
# HOW IT WORKS:
# The frontend sends the passphrase in an HTTP header called "X-Access-Code"
# with every single request. The gateway checks it here before doing anything else.
# =============================================================================

from fastapi import Header, HTTPException, Depends
from config import get_settings


async def verify_access_code(
    x_access_code: str = Header(
        ...,                              # "..." means this header is required
        alias="X-Access-Code",            # The exact header name the client must send
        description="Demo access passphrase"
    )
) -> bool:
    """
    FastAPI dependency that checks the access code on every protected request.

    HOW FASTAPI DEPENDENCIES WORK:
    Instead of copy-pasting this check into every endpoint, we write it once here
    and add it as a "dependency" to any endpoint that needs protection.
    FastAPI automatically calls this function before the endpoint runs.

    Args:
        x_access_code: The passphrase sent by the client in the X-Access-Code header.

    Returns:
        True if the code is correct.

    Raises:
        HTTPException 401: If the code is missing or wrong.
    """
    settings = get_settings()

    # Compare the submitted code against the real code from .env
    # We use a simple string comparison — for a production system we would
    # use a cryptographic constant-time comparison to prevent timing attacks,
    # but for a hackathon demo this is sufficient.
    if x_access_code != settings.demo_access_code:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Ungültiger Zugangscode",          # German: Invalid access code
                "error_en": "Invalid access code",
                "hint": "Bitte geben Sie den korrekten Zugangscode ein."  # Please enter the correct access code
            }
        )

    return True


# This is a shorthand we can import in main.py
# Instead of writing Depends(verify_access_code) every time, we write Depends(AuthRequired)
AuthRequired = Depends(verify_access_code)
