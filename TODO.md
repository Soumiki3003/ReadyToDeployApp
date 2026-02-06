# KnowledgeGraph Refactoring TODO

## 🔴 Critical Security Fixes

- [ ] **Rotate exposed credentials** — Neo4j password and Google API keys are in git history
- [ ] **Remove hardcoded Neo4j credentials** — `app.py` (L16-19), `neo4j_loader.py` (L5-9), `extras.py` (L21-27)
- [ ] **Remove hardcoded API keys** — `parsers/dual_parser.py` (L11)
- [ ] **Add `.env` to `.gitignore`** — prevent future leaks
- [ ] **Update `.env.example`** — document all required env vars

---

## 🟠 Flask Restructure

### Application Factory
- [ ] **Create `app/__init__.py`** — factory pattern with `create_app()`, register blueprints
- [ ] **Setup `app/config.py`** — load from env vars, Flask config class

### Dependency Injection
- [ ] **Configure `config.yaml`** — YAML with `${ENV_VAR}` interpolation for Neo4j, Google, Flask settings
- [ ] **Setup `app/containers.py`** — dependency-injector with Neo4j driver and GenAI client singletons
- [ ] **Wire views** — use `@inject` decorator in blueprints

### Blueprints
- [ ] **Create `app/views/main.py`** — home/login routes
- [ ] **Create `app/views/upload.py`** — file upload routes
- [ ] **Create `app/views/graph.py`** — graph API routes

### Services (Merged Structure)
- [ ] **Create `app/services/llm.py`** — shared `OllamaLLM` wrapper used by all agents
- [ ] **Create `app/services/graph.py`** — Neo4j operations: loader, query, embeddings (merges `neo4j_loader.py`, `reembed_neo4j.py`)
- [ ] **Create `app/services/rag.py`** — GraphRAG retrieval, context search (merges common logic from `supervisor_agent.py` + `extras.py`)
- [ ] **Create `app/services/student.py`** — student state management, trajectory logging
- [ ] **Create `app/services/agents/supervisor.py`** — supervisor agent logic (uses `rag.py`, `student.py`)
- [ ] **Create `app/services/agents/companion.py`** — companion agent UI wrapper (uses supervisor)
- [ ] **Move `parsers/`** → `app/services/parsers/` — dual-path parser + extractors
- [ ] **Delete root files** — `app.py`, `extras.py`, `supervisor_agent.py`, `companion_agent.py`, `neo4j_loader.py`, `reembed_neo4j.py`

### Storage (SQLModel)
- [ ] **Add `sqlmodel` to dependencies** — SQLAlchemy + Pydantic models, production-ready
- [ ] **Create `app/models/student.py`** — `Student`, `Trajectory` models with relationships
- [ ] **Create `app/models/upload.py`** — `Upload` model for file metadata
- [ ] **Create `app/services/database.py`** — engine, session factory, migrations
- [ ] **Add SQLite for dev, PostgreSQL for prod** — configure via `config.yaml`
- [ ] **Add to containers.py** — inject session factory via dependency-injector

### Background Tasks (Huey)
- [ ] **Add `huey` to dependencies** — lightweight task queue
- [ ] **Create `app/tasks/__init__.py`** — Huey instance configuration with Redis/SQLite backend
- [ ] **Create `app/tasks/embeddings.py`** — async task for generating/updating embeddings
- [ ] **Create `app/tasks/parsing.py`** — async task for dual-path document parsing
- [ ] **Integrate with upload view** — trigger tasks on file upload, return job ID
- [ ] **Add task status endpoint** — check progress via HTMX polling

---

## 🟡 Frontend (Jinja2 + DaisyUI + HTMX)

### Base Template
- [ ] **Update `base.html`** — add DaisyUI CDN, Tailwind CDN, HTMX, define blocks (title, navbar, content)

### Page Templates (Jinja2 Inheritance)
- [ ] **Refactor `login.html`** — extend base, use DaisyUI card/form, HTMX `hx-post`
- [ ] **Refactor `upload.html`** — extend base, DaisyUI file-input, HTMX multipart upload
- [ ] **Refactor `graph.html`** — extend base, integrate D3 visualization

### HTMX Partials
- [ ] **Create `templates/partials/`** — `_alert.html`, `_upload_success.html` for fragment responses

---

## 🔵 Security Hardening

- [ ] **Add file upload validation** — `secure_filename`, allowed extensions, size limit
- [ ] **Disable debug mode** — use env var `FLASK_DEBUG`
- [ ] **Add error handlers** — 404, 500 custom pages

---

## ⚪ Optional Enhancements

- [ ] Implement Flask-Login authentication
- [ ] Add pytest test suite
- [ ] Configure logging
- [ ] Add health check endpoint

---

*Updated: 2026-02-06*
