import React from "react";

function Value({ v }) {
  return <span>{v === null || v === undefined ? "—" : String(v)}</span>;
}

export default function ExtractedDataCard({ loading, error, result }) {
  const extracted = result?.extracted_data;

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

  return (
    <div className="card">
      <div className="cardTitle">Extracted structured data</div>

      {error ? (
        <div className="muted">No extracted data (error occurred).</div>
      ) : loading ? (
        <div className="muted">Analyzing with AI...</div>
      ) : !extracted ? (
        <div className="muted">
          Paste application text and click <b>Analyze</b>.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {rows.map(([label, v]) => (
            <div key={label}>
              <div className="muted" style={{ fontSize: 12 }}>
                {label}
              </div>
              <div>
                <Value v={v} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

