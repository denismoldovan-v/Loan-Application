import json
import re
from functools import lru_cache
from typing import Any, Literal, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from openai import OpenAI


@lru_cache(maxsize=1)
def get_settings():
    # Loads backend/.env if present; cached for the lifetime of the process.
    load_dotenv()
    return {
        "openai_api_key": None if not _env("OPENAI_API_KEY") else _env("OPENAI_API_KEY"),
        "openai_model": _env("OPENAI_MODEL", "gpt-4.1-mini"),
    }


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    import os

    val = os.getenv(key)
    return default if val is None else val


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


_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_FALLBACK_NAME_RE = re.compile(
    r"(?:my name is|name is)\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-.\s]{2,60}?)(?=\s+from\s+|[.,])",
    flags=re.IGNORECASE,
)
_FALLBACK_CURRENCY_RE = re.compile(r"\b(PLN|EUR|USD)\b", flags=re.IGNORECASE)


def _fallback_extract(raw_text: str) -> dict[str, Any]:
    """
    Lightweight best-effort extraction so the app can run without OPENAI_API_KEY.
    This is only for demos; the main path uses OpenAI.
    """
    text = raw_text or ""
    email_match = _EMAIL_RE.search(text)
    email = email_match.group(0).rstrip(".,;:") if email_match else None

    currency_match = _FALLBACK_CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else None

    loan_amount = None
    loan_amount_match = re.search(
        r"(?:loan|financing|request)\w*[^0-9]{0,30}([0-9]{1,3}(?:[.,][0-9]{3})*|[0-9]+(?:[.,][0-9]+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if loan_amount_match:
        raw_amt = loan_amount_match.group(1).replace(",", "").replace(" ", "")
        try:
            loan_amount = float(raw_amt)
        except ValueError:
            loan_amount = None

    annual_revenue = None
    annual_match = re.search(
        r"(?:annual revenue|revenue)\w*[^0-9]{0,30}([0-9]{1,3}(?:[.,][0-9]{3})*|[0-9]+(?:[.,][0-9]+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if annual_match:
        raw_amt = annual_match.group(1).replace(",", "").replace(" ", "")
        try:
            annual_revenue = float(raw_amt)
        except ValueError:
            annual_revenue = None

    purpose = None
    purpose_match = re.search(
        r"(?:purpose(?: of)?(?: the)? loan|to finance|for (?:equipment|expansion|renovation|home renovation|purchase|working capital|general use|general purpose))[^.\n]{0,120}",
        text,
        flags=re.IGNORECASE,
    )
    if purpose_match:
        purpose = purpose_match.group(0).strip()
        purpose = re.sub(r"^(?:to finance|for)\s+", "", purpose, flags=re.IGNORECASE).strip()

    applicant_name = None
    name_match = _FALLBACK_NAME_RE.search(text)
    if name_match:
        applicant_name = name_match.group(1).strip()

    company_name = None
    company_match = re.search(
        r"(?:from|at)\s+([A-Z][A-Za-z0-9À-ÖØ-öø-ÿ&'\-.,\s]{2,80}(?:Sp\.?\s*z\s*o\.?\s*o\.|LLC|Ltd|S\.?A\.?|Inc\.?))",
        text,
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
    if company_name and any(k in company_name.lower() for k in ["sp.", "llc", "ltd"]):
        applicant_type = "SME"
    elif applicant_name:
        applicant_type = "retail"
    else:
        applicant_type = "unknown"

    source_channel = None
    if "@" in text:
        source_channel = "email"
    elif re.search(r"\bportal\b", text, flags=re.IGNORECASE):
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
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                # Some SDK versions accept this; retry without if needed.
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
        data = json.loads(content)
        if "missing_fields" not in data:
            data["missing_fields"] = []
        return data
    except Exception as e:
        # When billing/credits are not available, we still want the demo to work.
        # Fall back to heuristic extraction instead of failing the whole request.
        msg = str(e).lower()
        if "insufficient_quota" in msg or "quota" in msg or "billing" in msg:
            return _fallback_extract(raw_text)
        raise


_REQUIRED_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_missing_str(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate_extracted_data(extracted: ExtractedData) -> tuple[list[str], list[str]]:
    """
    Deterministic validation and completeness checks.
    Returns: (missing_fields, validation_issues)
    """
    missing_fields: list[str] = []
    validation_issues: list[str] = []

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

    if extracted.contact_email and not _REQUIRED_EMAIL_RE.match(extracted.contact_email):
        validation_issues.append("Contact email format looks invalid")

    if extracted.loan_amount is not None and extracted.loan_amount <= 0:
        validation_issues.append("Loan amount must be a positive number")

    if extracted.annual_revenue is not None and extracted.annual_revenue <= 0:
        validation_issues.append("Annual revenue must be a positive number")

    return missing_fields, validation_issues


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
    required_missing = len(missing_fields)

    if annual_revenue is not None and loan_amount is not None and loan_amount > 0.5 * annual_revenue:
        flags.append("Requested loan exceeds 50% of annual revenue")

    if required_missing >= 3:
        flags.append("Multiple required fields missing")

    if loan_amount is not None and loan_amount >= 500_000 and annual_revenue is None:
        flags.append("Loan amount very high while annual revenue is missing")

    if annual_revenue is None:
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

    return flags, risk_level


def map_to_crm_ready_json(extracted: ExtractedData) -> tuple[dict[str, Any], str]:
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


def frontend_html() -> str:
    # Single-file UI (no Vite/React build needed).
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Loan Application Intake Assistant</title>
    <style>
      :root {
        --bg: #f7f8fb;
        --card: #ffffff;
        --stroke: #e5e7eb;
        --text: #111827;
        --muted: #6b7280;
        --accent: #2563eb;
        --danger: #b91c1c;
        --warning: #b45309;
        --success: #047857;
      }
      * { box-sizing: border-box; }
      html, body { margin: 0; padding: 0; }
      body {
        font-family: Inter, Segoe UI, Arial, sans-serif;
        color: var(--text);
        background: var(--bg);
      }
      .shell {
        max-width: 1280px;
        margin: 0 auto;
        padding: 22px;
      }
      .hero {
        border: 1px solid var(--stroke);
        border-radius: 12px;
        padding: 22px;
        background: #ffffff;
        box-shadow: none;
        margin-bottom: 14px;
      }
      .title {
        margin: 0;
        font-size: 30px;
        letter-spacing: 0.2px;
      }
      .subtitle {
        margin-top: 8px;
        color: var(--muted);
        font-size: 15px;
      }
      .quick {
        margin-top: 14px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      .chip {
        border: 1px solid #dbe4ff;
        background: #f3f6ff;
        color: #334155;
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 500;
      }
      .grid {
        display: grid;
        grid-template-columns: minmax(360px, 1.08fr) minmax(430px, 1fr);
        gap: 14px;
        align-items: start;
      }
      @media (max-width: 980px) {
        .grid { grid-template-columns: 1fr; }
      }
      .stack { display: grid; gap: 14px; }
      .card {
        border: 1px solid var(--stroke);
        border-radius: 12px;
        background: var(--card);
        padding: 16px;
      }
      .cardTop {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 10px;
      }
      .cardTitle {
        margin: 0;
        font-size: 15px;
        font-weight: 700;
        color: #0f172a;
      }
      .muted { color: var(--muted); font-size: 13px; line-height: 1.45; }
      textarea {
        width: 100%;
        min-height: 260px;
        resize: vertical;
        border: 1px solid var(--stroke);
        background: #ffffff;
        color: var(--text);
        border-radius: 10px;
        padding: 12px;
        outline: none;
        font-size: 14px;
      }
      textarea:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
      }
      .row {
        margin-top: 10px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      button {
        border: 1px solid var(--stroke);
        background: #ffffff;
        color: #111827;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: 160ms ease;
      }
      button:hover { transform: translateY(-1px); background: #f9fafb; }
      button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
      .primary {
        border-color: #1d4ed8;
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #fff;
      }
      .primary:hover {
        background: linear-gradient(135deg, #1d4ed8, #1e40af);
        border-color: #1e40af;
        box-shadow: 0 6px 14px rgba(37,99,235,0.22);
      }
      .ghost { background: #ffffff; }
      .sampleBtn {
        border-radius: 999px;
        padding: 8px 11px;
        background: #ffffff;
        border-color: #d1d5db;
      }
      .error {
        margin-top: 10px;
        border: 1px solid #fecaca;
        background: #fff1f2;
        color: #7f1d1d;
        border-radius: 10px;
        padding: 10px;
        font-size: 13px;
      }
      .meta {
        margin-top: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        color: var(--muted);
      }
      .progress {
        width: 100%;
        height: 8px;
        border-radius: 999px;
        background: #f3f4f6;
        border: 1px solid var(--stroke);
        overflow: hidden;
      }
      .progress > i {
        display: block;
        height: 100%;
        width: 0%;
        background: #2563eb;
        transition: width 300ms ease;
      }
      .fieldGrid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 9px;
      }
      @media (max-width: 620px) { .fieldGrid { grid-template-columns: 1fr; } }
      .field {
        border: 1px solid var(--stroke);
        border-radius: 10px;
        background: #ffffff;
        padding: 10px;
      }
      .field .k { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
      .field .v { margin-top: 5px; font-size: 14px; color: #111827; word-break: break-word; }
      .list {
        margin: 6px 0 0;
        padding-left: 18px;
      }
      .list li { margin: 4px 0; color: #374151; }
      .riskBadge {
        border-radius: 999px;
        padding: 6px 11px;
        font-size: 12px;
        font-weight: 700;
        border: 1px solid transparent;
      }
      .risk-low { color: #065f46; background: #ecfdf5; border-color: #a7f3d0; }
      .risk-medium { color: #92400e; background: #fffbeb; border-color: #fcd34d; }
      .risk-high { color: #991b1b; background: #fef2f2; border-color: #fca5a5; }
      pre {
        margin: 0;
        border: 1px solid var(--stroke);
        border-radius: 12px;
        padding: 12px;
        background: #f9fafb;
        color: #1f2937;
        overflow: auto;
        max-height: 300px;
        font-size: 12.5px;
      }
      .footnote {
        margin-top: 10px;
        border: 1px dashed #d1d5db;
        border-radius: 12px;
        padding: 10px;
        color: var(--muted);
        font-size: 12.5px;
      }
      .hidden { display: none !important; }
    </style>
  </head>
  <body>
    <div class="shell">
      <section class="hero">
        <h1 class="title">AI Loan Application Intake Assistant</h1>
        <div class="subtitle">Convert unstructured application text into validated, risk-scored, CRM-ready data.</div>
        <div class="quick">
          <span class="chip">Single endpoint flow</span>
          <span class="chip">OpenAI extraction</span>
          <span class="chip">Deterministic rule engine</span>
          <span class="chip">CRM JSON output</span>
        </div>
      </section>

      <section class="grid">
        <div class="stack">
          <article class="card">
            <div class="cardTop">
              <h2 class="cardTitle">Application input</h2>
              <span class="muted">Tip: Ctrl+Enter to analyze</span>
            </div>
            <textarea id="rawText" placeholder="Paste raw email / portal notes / application text here..."></textarea>
            <div class="meta">
              <span id="charCount">0 chars</span>
              <span id="wordCount">0 words</span>
            </div>
            <div class="row">
              <button class="primary" id="analyzeBtn">Analyze application</button>
              <button class="ghost" id="clearBtn">Clear</button>
            </div>
            <div class="row" id="sampleRow"></div>
            <div id="errorBox" class="error hidden"></div>
          </article>

          <article class="card">
            <div class="cardTop">
              <h2 class="cardTitle">Pipeline status</h2>
              <span id="statusLabel" class="muted">Idle</span>
            </div>
            <div class="progress"><i id="progressBar"></i></div>
            <div class="muted" id="statusText" style="margin-top:8px;">Waiting for input...</div>
          </article>
        </div>

        <div class="stack">
          <article class="card">
            <div class="cardTop"><h2 class="cardTitle">Extracted structured data</h2></div>
            <div id="extractedBox" class="muted">Paste application text and click <b>Analyze application</b>.</div>
            <div id="extractedGrid" class="fieldGrid hidden"></div>
          </article>

          <article class="card">
            <div class="cardTop"><h2 class="cardTitle">Missing fields and validation</h2></div>
            <div id="validationBox" class="muted">Validation findings will appear here.</div>
          </article>

          <article class="card">
            <div class="cardTop">
              <h2 class="cardTitle">Risk assessment</h2>
              <span id="riskBadge" class="riskBadge hidden"></span>
            </div>
            <div id="riskBox" class="muted">Risk level and flags will appear here.</div>
          </article>

          <article class="card">
            <div class="cardTop">
              <h2 class="cardTitle">CRM-ready JSON</h2>
              <button id="copyBtn" class="ghost hidden">Copy JSON</button>
            </div>
            <pre id="crmPre" class="hidden"></pre>
            <div id="crmPlaceholder" class="muted">The integration-ready CRM payload will appear here after analysis.</div>
          </article>
        </div>
      </section>

      <div id="note" class="footnote hidden">
        Note: this is an illustrative pre-screening layer for intake only, not a real credit decision engine.
      </div>
    </div>

    <script>
      const samples = [
        {
          id: "decent",
          label: "Sample: good SME",
          text: `Hello, my name is Jan Kowalski from ABC Sp. z o.o. We are requesting a loan of 150,000 PLN to finance new equipment. Our annual revenue is approximately 1,200,000 PLN. You can contact me at jan@abc.pl.`
        },
        {
          id: "incomplete",
          label: "Sample: incomplete",
          text: `Hi, I run a small transport company and need around 300k financing for expansion. Please let me know next steps.`
        },
        {
          id: "retail",
          label: "Sample: retail",
          text: `My name is Anna Nowak. I would like a personal loan of 20,000 PLN for home renovation. My email is anna.nowak@gmail.com.`
        }
      ];

      const rawTextEl = document.getElementById("rawText");
      const analyzeBtn = document.getElementById("analyzeBtn");
      const clearBtn = document.getElementById("clearBtn");
      const errorBox = document.getElementById("errorBox");
      const sampleRow = document.getElementById("sampleRow");

      const charCount = document.getElementById("charCount");
      const wordCount = document.getElementById("wordCount");

      const extractedBox = document.getElementById("extractedBox");
      const extractedGrid = document.getElementById("extractedGrid");
      const validationBox = document.getElementById("validationBox");
      const riskBox = document.getElementById("riskBox");
      const riskBadge = document.getElementById("riskBadge");

      const crmPlaceholder = document.getElementById("crmPlaceholder");
      const crmPre = document.getElementById("crmPre");
      const copyBtn = document.getElementById("copyBtn");
      const note = document.getElementById("note");

      const statusText = document.getElementById("statusText");
      const statusLabel = document.getElementById("statusLabel");
      const progressBar = document.getElementById("progressBar");

      function setProgress(label, text, percent) {
        statusLabel.textContent = label;
        statusText.textContent = text;
        progressBar.style.width = percent + "%";
      }

      function updateCounts() {
        const text = rawTextEl.value || "";
        charCount.textContent = text.length + " chars";
        const words = text.trim() ? text.trim().split(/\\s+/).length : 0;
        wordCount.textContent = words + " words";
      }
      rawTextEl.addEventListener("input", updateCounts);
      updateCounts();

      samples.forEach(s => {
        const b = document.createElement("button");
        b.className = "sampleBtn";
        b.textContent = s.label;
        b.onclick = () => { rawTextEl.value = s.text; updateCounts(); setError(""); };
        sampleRow.appendChild(b);
      });

      function setError(msg) {
        if (!msg) {
          errorBox.classList.add("hidden");
          errorBox.textContent = "";
          return;
        }
        errorBox.textContent = "Error: " + msg;
        errorBox.classList.remove("hidden");
      }

      function displayValue(v) {
        if (v === null || v === undefined || v === "") return "—";
        return String(v);
      }

      function renderExtracted(extracted) {
        extractedBox.classList.add("hidden");
        extractedGrid.classList.remove("hidden");

        const rows = [
          ["Applicant name", extracted?.applicant_name],
          ["Company name", extracted?.company_name],
          ["Loan amount", extracted?.loan_amount],
          ["Currency", extracted?.currency],
          ["Annual revenue", extracted?.annual_revenue],
          ["Purpose of loan", extracted?.purpose_of_loan],
          ["Contact email", extracted?.contact_email],
          ["Applicant type", extracted?.applicant_type],
          ["Contact phone", extracted?.contact_phone],
          ["Source channel", extracted?.source_channel],
          ["Summary", extracted?.summary]
        ];

        extractedGrid.innerHTML = rows.map(([label, v]) => `
          <div class="field">
            <div class="k">${label}</div>
            <div class="v">${displayValue(v)}</div>
          </div>
        `).join("");
      }

      function renderValidation(missing, issues) {
        const missingList = missing?.length ? `<ul class="list">${missing.map(x => `<li>${x}</li>`).join("")}</ul>` : "<div>None</div>";
        const issuesList = issues?.length ? `<ul class="list">${issues.map(x => `<li>${x}</li>`).join("")}</ul>` : "<div>None</div>";

        validationBox.innerHTML = `
          <div class="muted" style="font-size:12px;">Missing fields</div>
          ${missingList}
          <div style="height:10px;"></div>
          <div class="muted" style="font-size:12px;">Validation issues</div>
          ${issuesList}
        `;
      }

      function riskClass(level) {
        if (level === "HIGH") return "risk-high";
        if (level === "MEDIUM") return "risk-medium";
        return "risk-low";
      }

      function renderRisk(level, flags) {
        riskBadge.className = "riskBadge " + riskClass(level);
        riskBadge.textContent = "Risk: " + level;
        riskBadge.classList.remove("hidden");

        const list = flags?.length ? `<ul class="list">${flags.map(f => `<li>${f}</li>`).join("")}</ul>` : "<div>No major flags.</div>";
        riskBox.innerHTML = `
          <div class="muted" style="font-size:12px;">Risk flags</div>
          ${list}
        `;
      }

      function setLoading(on) {
        analyzeBtn.disabled = on;
        clearBtn.disabled = on;
        [...sampleRow.querySelectorAll("button")].forEach(b => b.disabled = on);
        analyzeBtn.textContent = on ? "Analyzing..." : "Analyze application";
      }

      async function handleAnalyze() {
        setError("");
        const text = rawTextEl.value || "";
        if (!text.trim()) {
          setError("Please paste some application text.");
          return;
        }

        setLoading(true);
        setProgress("Running", "Extracting fields with AI...", 20);

        try {
          const res = await fetch("/process-application", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ raw_text: text })
          });

          setProgress("Running", "Applying validation and risk engine...", 70);

          const data = await res.json();
          if (!res.ok) throw new Error(data?.detail || "Request failed");

          renderExtracted(data.extracted_data);
          renderValidation(data.missing_fields, data.validation_issues);
          renderRisk(data.risk_level, data.risk_flags);

          const crm = data.crm_ready_json;
          crmPlaceholder.classList.add("hidden");
          crmPre.classList.remove("hidden");
          copyBtn.classList.remove("hidden");
          crmPre.textContent = JSON.stringify(crm, null, 2);

          note.classList.remove("hidden");
          copyBtn.onclick = async () => {
            try {
              await navigator.clipboard.writeText(JSON.stringify(crm, null, 2));
              const old = copyBtn.textContent;
              copyBtn.textContent = "Copied!";
              setTimeout(() => { copyBtn.textContent = old; }, 1200);
            } catch (_) {
              setError("Clipboard blocked by browser.");
            }
          };

          setProgress("Done", "Analysis complete. Results are ready.", 100);
        } catch (e) {
          setError(e?.message || "Failed to analyze application.");
          setProgress("Failed", "Analysis failed. Check error and retry.", 100);
        } finally {
          setLoading(false);
        }
      }

      analyzeBtn.onclick = handleAnalyze;
      clearBtn.onclick = () => {
        rawTextEl.value = "";
        updateCounts();
        setError("");
        setProgress("Idle", "Waiting for input...", 0);
      };
      rawTextEl.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleAnalyze();
      });
    </script>
  </body>
</html>
"""


app = FastAPI(title="AI Loan Application Intake Assistant (single-file)")

# Same-origin UI uses no CORS, but keep it open for local/dev usage.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def index():
    return frontend_html()


@app.post("/process-application", response_model=ProcessApplicationResponse)
def process_application(req: ProcessApplicationRequest) -> ProcessApplicationResponse:
    try:
        extracted_dict = extract_application_data(req.raw_text)
        extracted = ExtractedData.model_validate(extracted_dict)

        missing_fields, validation_issues = validate_extracted_data(extracted)
        risk_flags, risk_level = compute_risk(extracted, missing_fields)
        crm_ready_json, _completeness = map_to_crm_ready_json(extracted)

        return ProcessApplicationResponse(
            extracted_data=extracted,
            missing_fields=missing_fields,
            validation_issues=validation_issues,
            risk_flags=risk_flags,
            risk_level=risk_level,
            crm_ready_json=crm_ready_json,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    # Run with: python single_file_app.py
    uvicorn.run(app, host="0.0.0.0", port=8000)

