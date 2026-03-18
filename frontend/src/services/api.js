const DEFAULT_API_BASE_URL = "http://localhost:8000";

export async function processApplication(rawText) {
  const baseUrl =
    import.meta.env.VITE_API_BASE_URL?.toString() || DEFAULT_API_BASE_URL;

  const res = await fetch(`${baseUrl}/process-application`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ raw_text: rawText })
  });

  if (!res.ok) {
    const maybeJson = await res.json().catch(() => null);
    const detail = maybeJson?.detail || res.statusText;
    throw new Error(detail);
  }

  return res.json();
}

