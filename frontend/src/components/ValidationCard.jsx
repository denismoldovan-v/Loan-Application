import React from "react";

function List({ items }) {
  return (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      {items.map((x, idx) => (
        <li key={`${idx}-${x}`}>{x}</li>
      ))}
    </ul>
  );
}

export default function ValidationCard({ loading, error, result }) {
  const missing = result?.missing_fields || [];
  const issues = result?.validation_issues || [];

  return (
    <div className="card">
      <div className="cardTitle">Missing fields / validation</div>

      {error ? (
        <div className="muted">No validation results (error occurred).</div>
      ) : loading ? (
        <div className="muted">Running validation...</div>
      ) : !result ? (
        <div className="muted">Validation issues will appear here.</div>
      ) : (
        <>
          <div className="muted" style={{ fontSize: 12 }}>
            Missing fields
          </div>
          {missing.length ? <List items={missing} /> : <div>None</div>}

          <div style={{ height: 10 }} />

          <div className="muted" style={{ fontSize: 12 }}>
            Validation issues
          </div>
          {issues.length ? <List items={issues} /> : <div>None</div>}
        </>
      )}
    </div>
  );
}

