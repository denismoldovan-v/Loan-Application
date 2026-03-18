from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .crm_mapper import map_to_crm_ready_json
from .openai_service import extract_application_data
from .risk_engine import compute_risk
from .schemas import ExtractedData, ProcessApplicationRequest, ProcessApplicationResponse
from .validators import validate_extracted_data


def create_app() -> FastAPI:
    app = FastAPI(title="AI Loan Application Intake Assistant")

    # Frontend dev server default for Vite
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/process-application", response_model=ProcessApplicationResponse)
    def process_application(req: ProcessApplicationRequest) -> ProcessApplicationResponse:
        try:
            raw = req.raw_text
            extracted_dict = extract_application_data(raw)
            extracted = ExtractedData.model_validate(extracted_dict)

            missing_fields, validation_issues = validate_extracted_data(extracted)
            risk_flags, risk_level = compute_risk(extracted, missing_fields)

            crm_ready_json, _completeness = map_to_crm_ready_json(extracted)

            # Missing fields: recompute in Python as the deterministic source of truth.
            # (Even if the model provided missing_fields, we override for consistency.)
            return ProcessApplicationResponse(
                extracted_data=extracted,
                missing_fields=missing_fields,
                validation_issues=validation_issues,
                risk_flags=risk_flags,
                risk_level=risk_level,
                crm_ready_json=crm_ready_json,
            )
        except Exception as e:
            # Avoid leaking raw stack traces to the client.
            raise HTTPException(status_code=400, detail=str(e))

    return app


app = create_app()

