from __future__ import annotations

import re
from typing import Any

from .schemas import ExtractedData


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_missing_str(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate_extracted_data(extracted: ExtractedData) -> tuple[list[str], list[str]]:
    """
    Deterministic validation and completeness checks.
    Returns: (missing_fields, validation_issues)
    """
    missing_fields: list[str] = []
    validation_issues: list[str] = []

    # Required set from Plan.docx:
    # applicant_name OR company_name
    if _is_missing_str(extracted.applicant_name) and _is_missing_str(extracted.company_name):
        missing_fields.append("applicant_name OR company_name")

    if extracted.loan_amount is None or extracted.loan_amount <= 0:
        missing_fields.append("loan_amount")

    if _is_missing_str(extracted.currency):
        missing_fields.append("currency")

    if _is_missing_str(extracted.purpose_of_loan):
        missing_fields.append("purpose_of_loan")

    if _is_missing_str(extracted.contact_email):
        missing_fields.append("contact_email")

    # Email validation (issue, not necessarily missing)
    if extracted.contact_email and not _EMAIL_RE.match(extracted.contact_email):
        validation_issues.append("Contact email format looks invalid")

    # Numeric sanity
    if extracted.loan_amount is not None and extracted.loan_amount <= 0:
        validation_issues.append("Loan amount must be a positive number")

    if extracted.annual_revenue is not None and extracted.annual_revenue <= 0:
        validation_issues.append("Annual revenue must be a positive number")

    return missing_fields, validation_issues

