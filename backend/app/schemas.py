from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ProcessApplicationRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)


class ExtractedData(BaseModel):
    applicant_name: Optional[str] = None
    company_name: Optional[str] = None
    loan_amount: Optional[float] = None
    currency: Optional[str] = None
    annual_revenue: Optional[float] = None
    purpose_of_loan: Optional[str] = None

    # Additional useful fields (may be null)
    applicant_type: Optional[str] = None  # SME, retail, unknown
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source_channel: Optional[str] = None  # email, portal, notes, unknown

    summary: Optional[str] = None


class ProcessApplicationResponse(BaseModel):
    extracted_data: ExtractedData

    missing_fields: list[str] = Field(default_factory=list)
    validation_issues: list[str] = Field(default_factory=list)

    risk_flags: list[str] = Field(default_factory=list)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]

    crm_ready_json: dict[str, Any]

