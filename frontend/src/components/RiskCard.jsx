import React from "react";

export default function RiskCard({ loading, error, result }) {
  const riskLevel = result?.risk_level;
  const flags = result?.risk_flags || [];

  function pillColor(level) {
    if (level === "HIGH") return "#b91c1c";
    if (level === "MEDIUM") return "#b45309";
    return "#047857";
  }

  return (
    <div className="card">
      <div className="cardTitle">Risk assessment</div>

      {error ? (
        <div className="muted">No risk results (error occurred).</div>
      ) : loading ? (
        <div className="muted">Scoring risk...</div>
      ) : !result ? (
        <div className="muted">Risk flags and level will appear here.</div>
      ) : (
        <>
          <div style={{ marginBottom: 10 }}>
            <span
              style={{
                display: "inline-block",
                padding: "6px 10px",
                borderRadius: 999,
                background: pillColor(riskLevel),
                color: "white",
                fontWeight: 700
              }}
            >
              Risk level: {riskLevel}
            </span>
          </div>

          <div className="muted" style={{ fontSize: 12 }}>
            Risk flags
          </div>
          {flags.length ? (
            <ul style={{ marginTop: 8, paddingLeft: 18 }}>
              {flags.map((f, idx) => (
                <li key={`${idx}-${f}`}>{f}</li>
              ))}
            </ul>
          ) : (
            <div style={{ marginTop: 8 }}>None</div>
          )}
        </>
      )}
    </div>
  );
}

