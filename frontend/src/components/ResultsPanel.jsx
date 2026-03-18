import React from "react";
import ExtractedDataCard from "./ExtractedDataCard.jsx";
import ValidationCard from "./ValidationCard.jsx";
import RiskCard from "./RiskCard.jsx";
import CrmJsonCard from "./CrmJsonCard.jsx";

export default function ResultsPanel({ loading, error, result }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <ExtractedDataCard loading={loading} error={error} result={result} />
      <ValidationCard loading={loading} error={error} result={result} />
      <RiskCard loading={loading} error={error} result={result} />
      <CrmJsonCard loading={loading} error={error} result={result} />
    </div>
  );
}

