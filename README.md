# SPARK-Bayern

**KI-gestützte Baugenehmigungsprüfung für Bayern**
**AI-assisted building permit processing for Bavaria**

> An extension layer for [SPARK Workflow](https://gitlab.opencode.de/bmds/planungs-und-genehmigungsbeschleunigung/spark-workflow) — built for the BMDS hackathon, June 2026.

---

## What This Is

SPARK-Bayern extends the SPARK Workflow system (published by the German Federal Ministry for Digital and State Modernization) with five new capabilities:

| Feature | What it does |
|---|---|
| **Smart Dashboard** | Traffic-light status visualization for permit applications |
| **Multi-Language UI** | German, English, Turkish, Arabic — with full RTL support for Arabic |
| **Document Quality Scorer** | Analyzes PDF quality before AI processing (no LLM needed) |
| **Bayern RAG Pipeline** | AI analysis grounded in actual Bayerische Bauordnung (BayBO) law text |
| **Federated Deployment** | One Docker Compose command to run everything, anywhere |

**Target:** Bayern (Bavaria), Germany
**Permit type:** Baugenehmigung (building permit)
**Users:** Government employees (Sachbearbeiter)
**License:** EUPL-1.2

---

## Quick Start (Local)

### Prerequisites

You need these installed on your Mac:

```bash
# Check if installed
docker --version    # Should show 20+
node --version      # Should show 18+
git --version       # Any version
```

If not installed:
```bash
# Install Homebrew first (Mac package manager)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then install the tools
brew install node
brew install --cask docker
```

### Step 1 — Clone the repository

```bash
git clone https://github.com/jeenalchandra-projects/spark-bayern.git
cd spark-bayern
```

### Step 2 — Set up your environment file

```bash
cp .env.example .env
```

Now open `.env` in any text editor and fill in these two values:

```env
LLM_API_KEY=your-requesty-api-key-here
DEMO_ACCESS_CODE=choose-any-passphrase-here
```

**How to get your Requesty API key:**
1. Go to [app.requesty.ai](https://app.requesty.ai)
2. Sign in → API Keys → Create Key
3. Copy the key and paste it in `.env`

**What to put as DEMO_ACCESS_CODE:**
Choose any phrase you want. During your demo, everyone in the room will use this phrase to log in. Example: `hackathon2026`

### Step 3 — Run

```bash
./deploy.sh
```

This script:
1. Checks Docker is running
2. Validates your `.env` file
3. Builds all Docker containers (first time: 3–5 minutes)
4. Starts all services
5. Confirms everything is healthy

**After it finishes:**
- Frontend: [http://localhost:3000](http://localhost:3000)
- API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- RAG service docs: [http://localhost:8002/docs](http://localhost:8002/docs)

### Step 4 — Test with demo documents

Three synthetic test PDFs are provided in `synthetic-data/`:

| File | What it demonstrates |
|---|---|
| `vollstaendig.pdf` | Complete application — should achieve high quality score and "vollständig" legal status |
| `unvollstaendig.pdf` | Missing 5 required documents — RAG analysis should identify each missing item |
| `schlechte_qualitaet.pdf` | Minimal content — quality scorer should flag low score |

Upload these at [http://localhost:3000](http://localhost:3000) to demonstrate all features.

---

## Architecture — How Everything Connects

```
Browser (http://localhost:3000)
    │
    │  HTTP requests with X-Access-Code header
    ▼
┌─────────────────────────────────────────────┐
│  API GATEWAY  (port 8000, FastAPI/Python)   │
│                                             │
│  • Validates passphrase (auth.py)           │
│  • Validates file (size, PDF check)         │
│  • Logs events for GDPR audit (audit.py)    │
│  • Routes to services in parallel           │
│  • Combines results                         │
│  • File bytes freed from memory             │
└──────┬──────────────┬───────────────┬───────┘
       │              │               │
       ▼              ▼               ▼
┌──────────┐  ┌──────────────┐  ┌─────────────────┐
│ QUALITY  │  │     RAG      │  │   TRANSLATION   │
│ SERVICE  │  │   SERVICE    │  │    SERVICE      │
│ (8001)   │  │   (8002)     │  │    (8003)       │
│          │  │              │  │                 │
│ pdfplumber│ │ ChromaDB     │  │ Requesty/Mistral│
│ pypdf    │  │ + BayBO text │  │ DE/EN/TR/AR     │
│ No LLM   │  │ + LLM query  │  │                 │
└──────────┘  └──────┬───────┘  └─────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  REQUESTY API   │
            │  (Frankfurt, DE)│
            │  Mistral Large  │
            │  EU GDPR ✓      │
            └─────────────────┘
```

### Service descriptions

**API Gateway** (`api-gateway/`)
- The front door for all requests
- Validates the passphrase on every request
- Reads uploaded files into memory (never writes to disk)
- Calls quality and RAG services in parallel (faster)
- Logs all events without logging personal data
- Returns combined results, then frees memory

**Quality Service** (`quality-service/`)
- Analyzes PDF quality without any AI
- Checks: text extractability, blank pages, encryption, metadata, file size ratios
- Returns a score (0–100), grade (A–F), and specific issues with German/English descriptions
- Instant and free — no API call needed

**RAG Service** (`rag-service/`)
- Loads Bayern Bauordnung (BayBO) law text on startup
- Splits law text into chunks and stores as vectors in ChromaDB (in-memory)
- When a document arrives: finds relevant law paragraphs via vector search
- Sends application text + relevant law to Mistral via Requesty
- Returns structured JSON with findings, legal citations, and recommendations

**Translation Service** (`translation-service/`)
- Stores all static UI text for DE/EN/TR/AR (no API call needed)
- Translates dynamic AI-generated text via Mistral for EN/TR/AR
- Flags Arabic as RTL so the frontend flips the layout

**Frontend** (`frontend/`)
- React + Vite single-page application
- Three screens: passphrase gate → upload → results
- Language switcher always visible (flags + language names)
- Traffic-light colors: green (good), yellow (attention), red (problem)
- RTL layout for Arabic

---

## File Structure Explained

```
spark-bayern/
│
├── api-gateway/
│   ├── main.py          ← Central router: receives uploads, coordinates services
│   ├── auth.py          ← Passphrase validation (GDPR Article 25)
│   ├── audit.py         ← GDPR audit logging (metadata only, no personal data)
│   ├── config.py        ← Reads .env variables
│   ├── requirements.txt ← Python dependencies
│   └── Dockerfile       ← Container recipe
│
├── quality-service/
│   ├── main.py          ← FastAPI endpoint that receives PDFs
│   ├── scorer.py        ← Core quality analysis logic (no AI)
│   ├── requirements.txt
│   └── Dockerfile
│
├── rag-service/
│   ├── main.py          ← FastAPI endpoint + vector store initialization
│   ├── ingest.py        ← BayBO loading, chunking, vector storage
│   ├── query.py         ← Prompt construction + LLM call + JSON parsing
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── translation-service/
│   ├── main.py          ← Static translations + dynamic LLM translation
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx           ← Root component, state management, screen routing
│   │   ├── App.css           ← Complete design system
│   │   ├── translations.js   ← All UI strings in DE/EN/TR/AR
│   │   └── components/
│   │       ├── AccessGate.jsx    ← Passphrase entry screen
│   │       ├── UploadScreen.jsx  ← Drag-and-drop upload
│   │       └── ResultsScreen.jsx ← Traffic-light results dashboard
│   ├── Dockerfile
│   └── package.json
│
├── synthetic-data/
│   ├── generate_test_pdfs.py ← Script that creates demo PDFs
│   ├── vollstaendig.pdf      ← Complete application (demo)
│   ├── unvollstaendig.pdf    ← Incomplete application (demo)
│   └── schlechte_qualitaet.pdf ← Poor quality document (demo)
│
├── docker-compose.yml    ← Starts all 5 services together locally
├── railway.toml          ← Railway cloud deployment config
├── deploy.sh             ← One-command local setup script
├── .env.example          ← Template for environment variables
├── .gitignore            ← Files never committed to GitHub
└── README.md             ← This file
```

---

## GDPR and Security — Full Explanation

This system was designed with GDPR compliance as a first-class requirement, not an afterthought.

### 1. No Document Storage (Article 5(1)(e) — Storage Limitation)

When you upload a PDF:
1. The browser sends the file as HTTP request bytes
2. The API Gateway reads those bytes into a Python variable (RAM only)
3. Those bytes are passed to quality and RAG services via HTTP (also in RAM)
4. Results are computed and returned
5. The Python variable goes out of scope → Python's garbage collector frees the memory
6. **No file is ever written to disk. No database entry is created. Nothing persists.**

This is implemented in `api-gateway/main.py`, specifically in the `/analyze` endpoint. The comment `# STEP 9: file_bytes goes out of scope here → Python frees memory` marks exactly where this happens.

### 2. Access Control (Article 25 — Data Protection by Design)

Every request must include a passphrase in the `X-Access-Code` HTTP header. This is checked in `api-gateway/auth.py` before any processing occurs. Without the correct code, the server returns `401 Unauthorized` and processes nothing.

This prevents unauthorized access to the system, even if the Railway URL becomes known.

### 3. Audit Logging Without Personal Data (Article 5(2) — Accountability)

Every action is logged in `api-gateway/audit.py`. What we log:
- Timestamp (UTC)
- Action type (e.g., "document_uploaded", "quality_check")
- File size in bytes
- Language selected
- Result summary (e.g., "score: 85/100")

What we **never** log:
- Document content
- Names, addresses, parcel numbers
- Any extracted text

The audit log is in-memory only and resets when the server restarts.

### 4. Data Minimisation (Article 5(1)(c))

The system extracts only what is needed for analysis. Names and addresses in a permit application are never displayed in the UI — only document-level status (complete/incomplete, quality score).

### 5. EU AI Act Compliance (Article 14 — Human Oversight)

Every analysis result includes this notice:
- German: "KI-Unterstützung – Die Endentscheidung liegt beim Sachbearbeiter."
- English: "AI assistance – The final decision rests with the case worker."

The AI never takes action. It only presents findings. The government worker must explicitly review and decide.

### 6. GDPR-Compliant LLM Provider

The system uses [Requesty](https://requesty.ai) as the LLM gateway, which:
- Is hosted in Frankfurt, Germany (AWS eu-central-1)
- Has zero data retention — requests are proxied in real-time, nothing stored
- Is GDPR-compliant with DPA available
- Is SOC 2 Type II certified
- Has built-in PII detection

### 7. For Production Use

The following additional steps would be required before deploying this to handle real permit applications in production:

- [ ] Replace passphrase gate with proper identity management (Keycloak, Active Directory)
- [ ] Enable HTTPS everywhere (Railway provides this automatically)
- [ ] Set `allow_origins` in CORS to the exact frontend URL (not `"*"`)
- [ ] Add rate limiting to prevent abuse
- [ ] Store audit logs in an encrypted, persistent database
- [ ] Conduct a Data Protection Impact Assessment (DPIA) under GDPR Article 35
- [ ] Sign a Data Processing Agreement (DPA) with Requesty
- [ ] Review under EU AI Act risk classification (likely "limited risk" or "minimal risk")

---

## Deployment to Railway

### One-time setup

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select `jeenalchandra-projects/spark-bayern`
4. Railway will detect the Dockerfile and start building

### Environment variables in Railway

In the Railway dashboard, for each service, add these environment variables:

```
LLM_API_KEY        = your-requesty-api-key
LLM_BASE_URL       = https://router.requesty.ai/v1
LLM_MODEL          = mistral/mistral-large-latest
LLM_APP_TITLE      = SPARK-Bayern
DEMO_ACCESS_CODE   = your-chosen-passphrase
```

For the frontend service, also add:
```
VITE_API_URL = https://your-api-gateway-url.up.railway.app
```

(Railway gives you the URL after the first deploy)

### Multi-service deployment

Railway supports deploying multiple services from one repository. Create one Railway service per folder:
- `api-gateway/` → Service 1
- `quality-service/` → Service 2
- `rag-service/` → Service 3
- `translation-service/` → Service 4
- `frontend/` → Service 5

Each gets its own Railway URL. The API Gateway URL is what you put in `VITE_API_URL` for the frontend.

---

## Federated Deployment (Feature 10)

This system is designed so any German state or municipality can run their own instance.

### To deploy for a different Bundesland

1. Clone this repository
2. In `.env`, configure:
   ```env
   # Example: Adapting for Baden-Württemberg
   LLM_API_KEY=your-key
   DEMO_ACCESS_CODE=your-code
   # No other changes needed for basic operation
   ```
3. To add state-specific building laws, place a PDF in `rag-service/data/baybo.pdf`
   (the file name is configured via `BAYBO_PDF_PATH` in `.env`)
4. Run `./deploy.sh`

The RAG service will automatically detect and load the PDF on startup. If no PDF is found, it falls back to built-in BayBO articles.

### Customizing for different permit types

The required documents checklist is defined in `rag-service/ingest.py` in the `REQUIRED_DOCUMENTS` list. Edit this list to add, remove, or modify required documents for different permit types.

---

## Relation to SPARK Workflow

This project is an **extension layer** for SPARK Workflow. It does not replace SPARK — it adds on top of it.

SPARK Workflow provides:
- Core document management (MinIO storage)
- Workflow orchestration (Temporal)
- Formal completeness check workflows
- Plausibility check services
- Project management (PostgreSQL)

SPARK-Bayern adds:
- A modern multilingual frontend
- Document quality pre-screening
- Bayern-specific legal RAG pipeline
- Federated deployment tooling

### Integration with SPARK

If you have a running SPARK installation, set in `.env`:
```
SPARK_BASE_URL=http://your-spark-host:8004
```

The API Gateway will then forward project creation and workflow triggers to SPARK. With `SPARK_BASE_URL=disabled` (default), SPARK-Bayern runs fully standalone.

---

## Contributing

This project was built for the BMDS hackathon. Contributions welcome:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes with clear messages
4. Push and open a pull request

Areas where contributions are most valuable:
- Additional Bundesland law PDFs for the RAG pipeline
- Improved prompt engineering for more accurate legal analysis
- Additional permit types beyond Baugenehmigung
- Test coverage for the Python services

---

## License

EUPL-1.2 — European Union Public Licence

This license is compatible with the SPARK Workflow project's license. See [LICENSE](LICENSE) for full text.

---

## Acknowledgements

- [SPARK Workflow](https://gitlab.opencode.de/bmds/planungs-und-genehmigungsbeschleunigung/spark-workflow) by BMDS — the foundation this extends
- [Requesty](https://requesty.ai) — GDPR-compliant EU LLM gateway
- [Mistral AI](https://mistral.ai) — LLM provider
- [ChromaDB](https://www.trychroma.com) — vector database for RAG
- Bayerische Bauordnung (BayBO) — public domain law text

---

*Built with ❤️ for the BMDS Hackathon 2026*
