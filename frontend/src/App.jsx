import React, { useMemo, useState } from "react";
import { processApplication } from "./services/api";
import InputPanel from "./components/InputPanel.jsx";
import ResultsPanel from "./components/ResultsPanel.jsx";

export default function App() {
  const [rawText, setRawText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const sampleInputs = useMemo(
    () => [
      {
        id: "decent",
        label: "Sample 1 — decent application",
        text: `Hello, my name is Jan Kowalski from ABC Sp. z o.o. We are requesting a loan of 150,000 PLN to finance new equipment. Our annual revenue is approximately 1,200,000 PLN. You can contact me at jan@abc.pl.`
      },
      {
        id: "incomplete",
        label: "Sample 2 — incomplete application",
        text: `Hi, I run a small transport company and need around 300k financing for expansion. Please let me know next steps.`
      },
      {
        id: "retail",
        label: "Sample 3 — retail client",
        text: `My name is Anna Nowak. I would like a personal loan of 20,000 PLN for home renovation. My email is anna.nowak@gmail.com.`
      }
    ],
    []
  );

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await processApplication(rawText);
      setResult(data);
    } catch (e) {
      setError(e?.message || "Failed to analyze application.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="top">
        <div className="title">AI Loan Application Intake Assistant</div>
        <div className="subtitle">
          Convert unstructured application text into CRM-ready data
        </div>
      </div>

      <div className="grid">
        <InputPanel
          rawText={rawText}
          setRawText={setRawText}
          loading={loading}
          error={error}
          sampleInputs={sampleInputs}
          onAnalyze={handleAnalyze}
        />

        <ResultsPanel loading={loading} error={error} result={result} />
      </div>

      {result?.risk_level ? (
        <div className="muted" style={{ marginTop: 12 }}>
          Note: this is an illustrative pre-screening layer for intake only, not
          a real credit decision engine.
        </div>
      ) : null}
    </div>
  );
}

