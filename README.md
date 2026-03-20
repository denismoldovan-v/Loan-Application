# AI Loan Application Intake Assistant

A single app (FastAPI + browser UI): paste application text, the backend calls OpenAI, validates fields, scores risk, and returns CRM-ready JSON.

---

## Quick start (recommended)

1. Clone the repository.
2. **Windows:** double-click **`setup_and_run.bat`**.  
   **Linux / macOS:** `chmod +x setup_and_run.sh` (once), then `./setup_and_run.sh`
3. On first run, the script asks for your **OpenAI API key**, creates a `.env` file, installs dependencies into `.venv`, and starts the server. Your browser opens at **http://localhost:8000/**

If you skip the key (empty Enter), the app still runs using a simplified rule-based extractor (fallback), without full OpenAI extraction.

---

## Docker (optional)

If you use Docker and prefer a container:

```bash
cp .env.example .env   # set OPENAI_API_KEY
docker compose up --build -d
```

Then open: http://localhost:8000/

---

## API (for integration)

- `POST /process-application`  
- Body: `{ "raw_text": "..." }`

