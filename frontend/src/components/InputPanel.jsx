import React from "react";

export default function InputPanel({
  rawText,
  setRawText,
  loading,
  error,
  sampleInputs,
  onAnalyze
}) {
  return (
    <div className="card">
      <div className="cardTitle">Input</div>
      <textarea
        value={rawText}
        onChange={(e) => setRawText(e.target.value)}
        placeholder="Paste raw email/application text here..."
      />

      <div className="row">
        <button className="primary" onClick={onAnalyze} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>
        <button
          onClick={() => setRawText("")}
          disabled={loading || !rawText}
          title="Clear input"
        >
          Clear
        </button>
      </div>

      <div className="row">
        {sampleInputs.map((s) => (
          <button
            key={s.id}
            onClick={() => setRawText(s.text)}
            disabled={loading}
            title={s.label}
          >
            {s.label}
          </button>
        ))}
      </div>

      {error ? <div className="error">Error: {error}</div> : null}
    </div>
  );
}

