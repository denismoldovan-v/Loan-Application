# AI Loan Application Intake Assistant

Jedna aplikacja (FastAPI + strona w przeglądarce): trzeba wkleić tekst wniosku, backend wywołuje OpenAI, waliduje dane, liczy ryzyko i zwraca JSON pod CRM.

---

## Szybki start (polecane)

1. Sklonuj repozytorium.
2. **Windows:** dwuklik **`setup_and_run.bat`** (albo `run_app.bat` — to to samo).  
   **Linux / macOS:** `chmod +x setup_and_run.sh` (tylko raz), potem `./setup_and_run.sh`
3. Przy pierwszym uruchomieniu skrypt zapyta o **klucz OpenAI API** i utworzy plik `.env`, zainstaluje zależności w `.venv` i uruchomi serwer. Przeglądarka otworzy się pod adresem **http://localhost:8000/**

Bez klucza (pusty Enter) aplikacja nadal działa w trybie uproszczonego ekstraktora (fallback), bez pełnego OpenAI.

---

## Docker (opcjonalnie)

Jeśli masz Dockera i wolisz kontener:

```bash
cp .env.example .env   # uzupełnij OPENAI_API_KEY
docker compose up --build -d
```

Potem: http://localhost:8000/

---

## API (dla integracji)

- `POST /process-application`  
- Body: `{ "raw_text": "..." }`

---

## Reszta repozytorium (opcjonalnie)

W folderze są też starszy podział `backend/` + `frontend/` (Vite/React) oraz pliki z zadania — **do uruchomienia demo wystarczy `single_file_app.py` + `setup_and_run`**.
