# KnowledgeGraph

KnowledgeGraph is a Flask application that extracts structured knowledge graphs from uploaded documents (PDF, PPTX, HTML), stores them in Neo4j, and powers course workflows for students and instructors.

## Tech Stack

- Python 3.12+
- Flask + dependency-injector
- Neo4j (+ neo4j-graphrag)
- pydantic-ai (default local Ollama model)

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (for Neo4j + Ollama)
- Poppler
- Tesseract OCR

This project requires **Poppler** for PDF processing and **Tesseract OCR** for OCR/text extraction.

### Installing Poppler

- **Windows**: Download from [poppler-windows releases](https://github.com/oschwartz10612/poppler-windows/releases) and add the `bin` folder to your system PATH
- **macOS**: `brew install poppler`
- **Linux**: `sudo apt-get install poppler-utils` (Debian/Ubuntu) or `sudo yum install poppler-utils` (RedHat/CentOS)

Verify installation:

```bash
pdftoppm -v
```

### Installing Tesseract OCR

- **Windows**:
  - Install `tesseract` and `tesseract-languages` via Scoop:
    - `scoop install tesseract`
    - `scoop install tesseract-languages`
  - If `tesseract-languages` fails with symbolic link privilege errors, enable **Windows Developer Mode** or run PowerShell as Administrator, then retry.
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt-get install tesseract-ocr tesseract-ocr-all` (Debian/Ubuntu)

Verify installation:

```bash
tesseract --version
```

## Quickstart

1. Install Python dependencies:

```bash
uv sync
```

2. Create your env file from the example:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

3. Start local infrastructure:

```bash
docker compose up -d
```

4. Run the app:

```bash
uv run python main.py
```

App runs on Flask default host/port unless configured otherwise (typically `http://127.0.0.1:5000`).

## Environment Variables

Set these in `.env` (see `.env.example`):

- `LOG_LEVEL` (default: `DEBUG`)
- `ALLOWED_EXTENSIONS` (default: `pdf,pptx,html`)
- `DEFAULT_MODEL` (default: `ollama:gpt-oss:20b`)
- `KNOWLEDGE_FILE_MODEL` (default: `ollama:gpt-oss:20b`)
- `GRAPH_MODEL` (default: `ollama:gpt-oss:20b`)
- `EMBEDDER_MODEL` (default: `ollama:qwen3-embedding:8b`)
- `OLLAMA_BASE_URL` (default: `http://localhost:11434/v1`)
- `NEO4J_URI` (default: `neo4j://127.0.0.1:7687`)
- `NEO4J_USER` (default: `neo4j`)
- `NEO4J_PASS` (default: `password`)
- `NEO4J_AUTH` (default: `neo4j/password`, used by Docker Compose)
- `FAKE_GENERATION` (default: `false`)
- `SECRET_KEY` (default: `dev-secret`)
- `FLASK_DEBUG` (default: `true`)

## Development Commands

Run tests:

```bash
uv run pytest
```

Run a single test:

```bash
uv run pytest tests/path/to/test_file.py::test_name
```

Lint and format:

```bash
uv run ruff check .
uv run ruff format .
```

## Fake Generation Mode (No LLM Required)

For local development without Ollama/LLM generation, set:

```env
FAKE_GENERATION=true
```

When enabled, the knowledge graph is generated using test factories instead of calling the model.

## Architecture (High-Level)

Request flow:

```text
Views (app/views/) → Controllers (app/controllers/) → Services (app/services/) → Gateways (app/gateways/)
```

Key points:

- Routes are defined in Flask blueprints under `app/views/`
- Dependency wiring is centralized in `app/containers.py`
- Neo4j and GraphRAG integrations live in `app/gateways/neo4j.py`
- Prompt templates are in `app/templates/prompts/`

## TODO

- Feature: Create hints