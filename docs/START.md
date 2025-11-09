# Getting Started

Follow these steps to get the Agent Framework running in your local environment.

## Step 1 — Set up your local environment

Complete the tooling and project setup described in [`docs/INSTALL.md`](INSTALL.md). When finished you should have:

- Required runtimes (Python 3.11.7+, .NET 9, Node.js 18.x, npm 9.x)
- A repo-root virtual environment (`.venv`) activated
- Dependencies restored for any services you plan to run
- The shared environment file copied to `Backend/.env`

## Step 2 — Configure Azure resources

Provision Azure OpenAI (and optionally Azure AI Foundry and **Azure AI Content Safety**) resources by following [`docs/AI_SERVICES.md`](AI_SERVICES.md). Capture the endpoint URLs, API keys, deployment names, and agent identifiers you will paste into `Backend/.env`.

### Content Safety Configuration (Recommended)

Enable Azure AI Content Safety for production deployments:

```env
# Azure Content Safety (Recommended for Production)
CONTENT_SAFETY_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
CONTENT_SAFETY_API_KEY=your-api-key-here
CONTENT_SAFETY_ENABLED=true
CONTENT_SAFETY_SEVERITY_THRESHOLD=4

# Per-category thresholds
CONTENT_SAFETY_THRESHOLD_HATE=4
CONTENT_SAFETY_THRESHOLD_SELFHARM=4
CONTENT_SAFETY_THRESHOLD_SEXUAL=4
CONTENT_SAFETY_THRESHOLD_VIOLENCE=4

# Behavior
CONTENT_SAFETY_BLOCK_UNSAFE_INPUT=true
CONTENT_SAFETY_FILTER_UNSAFE_OUTPUT=true
```

See [`docs/CONTENT_SAFETY.md`](CONTENT_SAFETY.md) for detailed configuration and best practices.

## Step 3 — Explore the .NET Semantic Kernel workshop

1. Launch VS Code or Jupyter and open `Backend/dotnet/sk/workshop_dotnet_semantic_kernel.ipynb`.
2. Select the **.NET Interactive** kernel (C#) when prompted.
3. Work through the cells in order:
   - Environment verification and package restore (#r directives)
   - `.env` loading and Azure OpenAI configuration checks
   - Semantic Kernel agent creation and group chat demos
   - Configuration-based agents that mirror the YAML catalog
   - **Content Safety integration testing** (if enabled)

The notebook mirrors the backend runtime, so completing it ensures your configuration is valid.

## Step 4 — Run the .NET Semantic Kernel API

From the repo root (with `.venv` activated for consistency) start the backend:

```powershell
cd Backend\dotnet\sk
dotnet restore
dotnet run
```

The API hosts at `http://localhost:8000`. Visit `/swagger` for interactive docs or call `/health` to make sure Azure settings are loaded.

**Content Safety Endpoints:**
- `POST /safety/scan-text` - Scan text for unsafe content
- `POST /safety/scan-image` - Scan images for unsafe content

## Step 5 — Explore the Python LangChain workshop

1. Open `Backend/python/langchain/workshop_langchain_agents.ipynb` in VS Code or Jupyter.
2. Use the repo-root virtual environment as the kernel (`.venv`).
3. Execute the cells sequentially:
   - Environment & dependency installer (installs `requirements.txt` automatically)
   - Configuration inspection (`config.yml`, `.env`)
   - Agent creation, routing, and group chat samples
   - Azure AI Foundry examples (skipped gracefully if not configured)
   - **Content Safety examples** (if enabled)

## Step 6 — Run the Python LangChain API

With the virtual environment active:

```powershell
cd Backend\python\langchain
uvicorn main:app --reload --port 8000
```

The service exposes FastAPI docs at `http://localhost:8000/docs`, plus health and chat endpoints that align with the frontend expectations.

## Step 7 — Explore the Python Semantic Kernel workshop

1. Open `Backend/python/sk/workshop_semantic_kernel_agents.ipynb`.
2. Attach the same `.venv` kernel to reuse installed packages.
3. Run each section in order to:
   - Validate Azure OpenAI and (optional) Azure AI Foundry credentials
   - Instantiate generic ChatCompletion agents
   - Exercise the hybrid router and group chat orchestrator
   - Compare YAML-driven instructions with live agent responses
   - **Test Content Safety filtering** (if enabled)

## Step 8 — Run the Python Semantic Kernel API

Still inside the virtual environment, start the SK backend:

```powershell
cd Backend\python\sk
uvicorn main:app --reload --port 8001
```

A different port (8001) avoids clashing with the LangChain service if you keep both running. FastAPI docs are available at `http://localhost:8001/docs`.

## Step 9 — Run the React frontend

With at least one backend running, start the UI from the repo root:

```powershell
cd frontend
npm start             # launches on http://localhost:3001
# macOS/Linux: PORT=3001 npm start
```

The frontend proxies API calls to `http://localhost:8000` by default (see `frontend/package.json`). If you are running a backend on a different port, update the `proxy` entry or set `REACT_APP_API_BASE` accordingly before launching.

### Frontend Content Safety Testing

The React frontend includes a **Content Safety Testing** panel in the sidebar:

1. **Text Scanner** - Enter text and scan for safety violations
2. **Image Scanner** - Upload and scan images
3. **Real-time Results** - View severity levels, flagged categories, blocklist matches
4. **Color-coded UI** - Green for safe, red for unsafe content

Access the testing panel by scrolling to the "Content Safety Testing" section in the left sidebar.

---

## Quick Verification Checklist

✅ **Environment Setup**
- [ ] Python 3.11.7+ installed
- [ ] .NET 9 SDK installed
- [ ] Node.js 18.x installed
- [ ] Virtual environment activated

✅ **Azure Configuration**
- [ ] Azure OpenAI endpoint and key configured
- [ ] (Optional) Azure AI Foundry project and agents configured
- [ ] (Recommended) Azure Content Safety endpoint and key configured

✅ **Backend Services**
- [ ] .NET API running on port 8000
- [ ] (Optional) Python API running on port 8000/8001
- [ ] Swagger UI accessible at `/swagger` or `/docs`
- [ ] Health endpoint returns 200 OK

✅ **Frontend**
- [ ] React app running on port 3001
- [ ] Can send messages to agents
- [ ] (Optional) Voice input/output working
- [ ] (Optional) Content Safety testing panel working

✅ **Content Safety** (if enabled)
- [ ] `CONTENT_SAFETY_ENABLED=true` in `.env`
- [ ] Endpoint and API key configured
- [ ] `/safety/scan-text` endpoint returns results
- [ ] `/safety/scan-image` endpoint returns results
- [ ] Frontend safety testing panel shows results

---

Once each backend is up, you can point the React frontend or API clients at the desired port to compare behaviours across frameworks. Feel free to iterate between notebooks and running services as you experiment with configuration changes.

For detailed Content Safety configuration and best practices, see [`docs/CONTENT_SAFETY.md`](CONTENT_SAFETY.md).
