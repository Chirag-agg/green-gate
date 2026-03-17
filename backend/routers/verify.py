"""
Public verification router for GreenGate.
Allows EU importers to verify carbon certificates — NO authentication required.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.blockchain import BlockchainService

router = APIRouter(prefix="/api", tags=["Verification"])


# ──── Pydantic Schemas ────


class VerificationResponse(BaseModel):
    is_valid: bool
    report_id: str
    timestamp: int
    timestamp_readable: str
    message: str


# ──── Endpoints ────


@router.get("/verify/{report_hash}", response_model=VerificationResponse)
async def verify_report(report_hash: str) -> VerificationResponse:
    """
    PUBLIC endpoint — verify a carbon report certificate on the blockchain.
    Anyone (EU importers, auditors) can call this without authentication.

    Args:
        report_hash: The SHA-256 hash of the report (0x-prefixed hex string).

    Returns:
        Verification result with report metadata from the blockchain.
    """
    # Ensure hash is properly formatted
    if not report_hash.startswith("0x"):
        report_hash = f"0x{report_hash}"

    try:
        blockchain = BlockchainService()
        result = await blockchain.verify_on_blockchain(report_hash)

        if result["is_valid"]:
            return VerificationResponse(
                is_valid=True,
                report_id=result["report_id"],
                timestamp=result["timestamp"],
                timestamp_readable=result["timestamp_readable"],
                message=(
                    f"✅ Valid certificate. Report {result['report_id']} was certified "
                    f"on {result['timestamp_readable']} and is permanently stored on "
                    f"the Polygon blockchain."
                ),
            )
        else:
            # Check if report exists but was revoked
            if result["report_id"]:
                return VerificationResponse(
                    is_valid=False,
                    report_id=result["report_id"],
                    timestamp=result["timestamp"],
                    timestamp_readable=result["timestamp_readable"],
                    message="❌ This certificate has been revoked.",
                )
            return VerificationResponse(
                is_valid=False,
                report_id="",
                timestamp=0,
                timestamp_readable="",
                message="❌ No certificate found for this hash. The report may not have been certified.",
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification service error: {str(e)}",
        )
