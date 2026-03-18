from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from .config import get_settings


_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _fallback_extract(raw_text: str) -> dict[str, Any]:
    """
    Lightweight best-effort extraction so the app can run without OpenAI.
    This is only for demos; the main path uses OpenAI.
    """
    email_match = _EMAIL_RE.search(raw_text or "")
    email = email_match.group(0).rstrip(".,;:") if email_match else None

    # Currency detection
    currency_match = re.search(r"\b(PLN|EUR|USD)\b", raw_text, flags=re.IGNORECASE)
    currency = currency_match.group(1).upper() if currency_match else None

    # Loan amount (very rough)
    loan_amount = None
    loan_amount_match = re.search(
        r"(?:loan|financing|request)\w*[^0-9]{0,30}([0-9]{1,3}(?:[.,][0-9]{3})*|[0-9]+(?:[.,][0-9]+)?)",
        raw_text,
        flags=re.IGNORECASE,
    )
    if loan_amount_match:
        raw_amt = loan_amount_match.group(1).replace(",", "").replace(" ", "")
        try:
            loan_amount = float(raw_amt)
        except ValueError:
            loan_amount = None

    # Annual revenue (rough)
    annual_revenue = None
    annual_match = re.search(
        r"(?:annual revenue|revenue)\w*[^0-9]{0,30}([0-9]{1,3}(?:[.,][0-9]{3})*|[0-9]+(?:[.,][0-9]+)?)",
        raw_text,
        flags=re.IGNORECASE,
    )
    if annual_match:
        raw_amt = annual_match.group(1).replace(",", "").replace(" ", "")
        try:
            annual_revenue = float(raw_amt)
        except ValueError:
            annual_revenue = None

    # Purpose (rough)
    purpose = None
    purpose_match = re.search(
        r"(?:purpose(?: of)?(?: the)? loan|to finance|for (?:equipment|expansion|renovation|home renovation|purchase|working capital|general use|general purpose))[^.\n]{0,120}",
        raw_text,
        flags=re.IGNORECASE,
    )
    if purpose_match:
        purpose = purpose_match.group(0).strip()
        # trim prefix noise
        purpose = re.sub(r"^(?:to finance|for)\s+", "", purpose, flags=re.IGNORECASE).strip()

    # Applicant name (rough)
    applicant_name = None
    # Capture up to "from" (common in SME examples) or punctuation.
    name_match = re.search(
        r"(?:my name is|name is)\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-.\s]{2,60}?)(?=\s+from\s+|[.,])",
        raw_text,
        flags=re.IGNORECASE,
    )
    if name_match:
        applicant_name = name_match.group(1).strip()

    # Company name (rough)
    company_name = None
    company_match = re.search(
        r"(?:from|at)\s+([A-Z][A-Za-z0-9À-ÖØ-öø-ÿ&'\-.,\s]{2,80}(?:Sp\.?\s*z\s*o\.?\s*o\.|LLC|Ltd|S\.?A\.?|Inc\.?))",
        raw_text,
        flags=re.IGNORECASE,
    )
    if company_match:
        company_name = company_match.group(1).strip()

    summary = None
    if loan_amount and currency and purpose:
        summary = f"Requesting {loan_amount:g} {currency} for {purpose}."
    elif loan_amount and currency:
        summary = f"Requesting {loan_amount:g} {currency}."
    elif purpose:
        summary = f"Loan purpose: {purpose}."

    applicant_type = None
    if company_name and ("sp." in company_name.lower() or "llc" in company_name.lower() or "ltd" in company_name.lower()):
        applicant_type = "SME"
    elif applicant_name:
        applicant_type = "retail"
    else:
        applicant_type = "unknown"

    source_channel = None
    if "@" in (raw_text or ""):
        source_channel = "email"
    elif re.search(r"\bportal\b", raw_text, flags=re.IGNORECASE):
        source_channel = "portal"
    else:
        source_channel = "unknown"

    return {
        "applicant_name": applicant_name,
        "company_name": company_name,
        "loan_amount": loan_amount,
        "currency": currency,
        "annual_revenue": annual_revenue,
        "purpose_of_loan": purpose,
        "contact_email": email,
        "applicant_type": applicant_type,
        "contact_phone": None,
        "source_channel": source_channel,
        "summary": summary,
        # OpenAI prompt includes missing_fields, but we recompute in Python validators.
        "missing_fields": [],
    }


def extract_application_data(raw_text: str) -> dict[str, Any]:
    """
    Extract structured loan fields from messy application text.

    Main path: OpenAI JSON-only extraction.
    Fallback: heuristic extraction when OPENAI_API_KEY is missing.
    """
    settings = get_settings()
    api_key = settings["openai_api_key"]
    model = settings["openai_model"]

    if not api_key:
        return _fallback_extract(raw_text)

    client = OpenAI(api_key=api_key)

    system_prompt = """
You are extracting loan application information from unstructured financial application text.
Return only valid JSON. Do not invent facts.
If a field is not present or unclear, return null.
Determine missing required fields from the required set:
applicant_name OR company_name, loan_amount, currency, purpose_of_loan, contact_email.
Create a short business-style summary for staff.

Return JSON with keys:
applicant_name
company_name
loan_amount
currency
annual_revenue
purpose_of_loan
contact_email
applicant_type
contact_phone
source_channel
summary
missing_fields

Constraints:
- Return ONLY JSON (no markdown, no extra text)
- Use null for missing values
- Do not fabricate values
""".strip()

    user_prompt = f"Application text:\n{raw_text}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            # Not all SDK versions accept response_format; retry without if needed.
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )

    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"OpenAI returned non-JSON content: {e}") from e

    # Ensure missing_fields exists.
    if "missing_fields" not in data:
        data["missing_fields"] = []
    return data

