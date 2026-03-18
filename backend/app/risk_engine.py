from __future__ import annotations

from typing import Literal

from .schemas import ExtractedData


def _required_count_missing(missing_fields: list[str]) -> int:
    # missing_fields already includes required field names; treat it as count.
    return len(missing_fields)


def compute_risk(extracted: ExtractedData, missing_fields: list[str]) -> tuple[list[str], Literal["LOW", "MEDIUM", "HIGH"]]:
    """
    Explainable, MVP risk scoring.

    Note: this is pre-screening only, not a credit decision engine.
    """
    flags: list[str] = []

    loan_amount = extracted.loan_amount
    annual_revenue = extracted.annual_revenue
    contact_email = extracted.contact_email
    purpose = extracted.purpose_of_loan

    required_missing = _required_count_missing(missing_fields)

    # High risk rules
    if annual_revenue is not None and loan_amount is not None and loan_amount > 0.5 * annual_revenue:
        flags.append("Requested loan exceeds 50% of annual revenue")

    if required_missing >= 3:
        flags.append("Multiple required fields missing")

    if loan_amount is not None and loan_amount >= 500_000 and annual_revenue is None:
        flags.append("Loan amount very high while annual revenue is missing")

    # Medium risk rules
    if annual_revenue is None and ("annual_revenue" not in missing_fields):
        # annual_revenue isn't strictly required in validators, but missing it should still raise medium risk
        flags.append("Annual revenue missing")

    if not contact_email:
        flags.append("Contact email missing")

    if purpose:
        vague_markers = ["general use", "general purpose", "general"]
        lowered = purpose.lower()
        if any(m in lowered for m in vague_markers):
            flags.append("Loan purpose too vague")

    if annual_revenue is not None and loan_amount is not None and loan_amount > 0.25 * annual_revenue:
        flags.append("Requested loan is high vs annual revenue")

    # Deduce level: if any high-risk flag present, escalate.
    high_risk_signals = {
        "Requested loan exceeds 50% of annual revenue",
        "Multiple required fields missing",
        "Loan amount very high while annual revenue is missing",
    }
    has_high = any(f in high_risk_signals for f in flags)

    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    if has_high:
        risk_level = "HIGH"
    elif flags:
        risk_level = "MEDIUM"

    # Low risk: required fields present and no major flags.
    # Keep it simple: if no flags were added, it is LOW.
    return flags, risk_level

