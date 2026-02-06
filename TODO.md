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

### File Migrations
- [ ] **Move `parsers/`** → `app/services/parsers/`
- [ ] **Move `neo4j_loader.py`** → `app/services/neo4j_loader.py`
- [ ] **Move `supervisor_agent.py`** → `app/services/agents/supervisor.py`
- [ ] **Move `companion_agent.py`** → `app/services/agents/companion.py`
- [ ] **Move `extras.py`** → `app/services/rag.py`
- [ ] **Move `reembed_neo4j.py`** → `scripts/reembed_neo4j.py`
- [ ] **Delete old `app.py`** — replaced by factory pattern

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
