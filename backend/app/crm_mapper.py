from __future__ import annotations

from .schemas import ExtractedData


def map_to_crm_ready_json(extracted: ExtractedData) -> tuple[dict, str]:
    completeness = "COMPLETE"
    missing_count = 0
    for v in [
        extracted.applicant_name,
        extracted.company_name,
        extracted.loan_amount,
        extracted.currency,
        extracted.purpose_of_loan,
        extracted.contact_email,
    ]:
        if v is None:
            missing_count += 1
    completeness = "PARTIAL" if missing_count >= 1 else "COMPLETE"

    crm = {
        "customer_name": extracted.applicant_name,
        "business_name": extracted.company_name,
        "requested_amount": extracted.loan_amount,
        "currency": extracted.currency,
        "annual_revenue": extracted.annual_revenue,
        "loan_purpose": extracted.purpose_of_loan,
        "email": extracted.contact_email,
        "phone": extracted.contact_phone,
        "application_source": extracted.source_channel or "unknown",
        "status": "NEW_APPLICATION",
        "completeness": completeness,
    }
    return crm, completeness

