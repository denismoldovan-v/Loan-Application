import React, { useState } from "react";

export default function CrmJsonCard({ loading, error, result }) {
  const crm = result?.crm_ready_json;
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!crm) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(crm, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      // Clipboard may be blocked; ignore.
    }
  }

  return (
    <div className="card">
      <div className="cardTitle">CRM-ready JSON</div>

      {error ? (
        <div className="muted">No CRM JSON (error occurred).</div>
      ) : loading ? (
        <div className="muted">Preparing CRM JSON...</div>
      ) : !crm ? (
        <div className="muted">
          The backend will return an integration-ready object here.
        </div>
      ) : (
        <>
          <div className="row" style={{ marginTop: 0 }}>
            <button onClick={handleCopy} disabled={loading}>
              {copied ? "Copied!" : "Copy JSON"}
            </button>
          </div>
          <pre style={{ marginTop: 10 }}>
            {JSON.stringify(crm, null, 2)}
          </pre>
        </>
      )}
    </div>
  );
}

