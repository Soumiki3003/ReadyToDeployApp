# KnowledgeGraph TODO

## ✅ Done
- [x] Removed legacy root scripts and moved to package-based app flow
- [x] Added config-driven fake graph generation toggle (`FAKE_GENERATION`)
- [x] Added fake graph factories for development data generation
- [x] Added basic test scaffold (`tests/`)
- [x] Configured structured logging via DI container + `config.yaml`

---

## ✅ Student & Instructor Views with RBAC (Complete)

### Phase 1: Foundation
- [x] Add `flask-login>=0.6.3` to `pyproject.toml`, run `uv sync`
- [x] Create `app/models/user.py` (User, UserRole, UserTrajectory) — replaces Student model
- [x] Delete `app/models/student.py`
- [x] Create `app/schemas/user.py` (CreateUser, UpdateUser)
- [x] Delete `app/schemas/student.py`
- [x] Update `app/models/__init__.py` and `app/schemas/__init__.py` exports

### Phase 2: Service Refactor (Student → User)
- [x] Rename `app/services/student.py` → `app/services/user.py`, StudentService → UserService
- [x] Add `authenticate(email, password)` method to UserService
- [x] Update `app/services/supervisor_agent.py` (student_service → user_service)
- [x] Update `app/services/__init__.py` exports

### Phase 3: Knowledge Model Changes
- [x] RootKnowledge: unlock `name`, add `description`, `source` → `sources: list[str]`
- [x] KnowledgeRootNode schema: add `description`, `sources`
- [x] Fix cascading `source` → `sources` in prompts.py, prompt templates, graph.html, controllers

### Phase 4: Knowledge Service Changes
- [x] Update `get_root_nodes` Cypher to project `description`, `sources`
- [x] Add `create_empty_course(name, description)` method
- [x] Add `add_document_to_course(course_id, file_path)` method

### Phase 5: Auth System
- [x] Create `app/views/guards.py` with `roles_required()` decorator
- [x] Create `app/controllers/auth.py` (AuthController)
- [x] Create `app/views/auth.py` (login, register, logout routes)
- [x] Wire Flask-Login in `main.py` (LoginManager, user_loader, secret_key)

### Phase 6: Templates — Base & Auth
- [x] Create `app/templates/web/base_app.html` (navbar with role badge)
- [x] Rewrite `app/templates/web/auth/login.html`
- [x] Create `app/templates/web/auth/register.html`

### Phase 7: Course Dashboard
- [x] Create `app/controllers/course.py` (CourseController)
- [x] Create `app/views/course.py` (dashboard, chat, settings, upload routes)
- [x] Create `app/templates/web/course/dashboard.html`

### Phase 8: Chat Page
- [x] Chat routes in course blueprint
- [x] Create `app/templates/web/course/chat.html` (disabled file upload with WIP tooltip)
- [x] Create `app/templates/web/course/chat_message.html` (HTMX fragment)

### Phase 9: Settings Page (Instructor)
- [x] Settings route with `@roles_required("instructor")`
- [x] Upload-to-course route
- [x] Create `app/templates/web/course/settings.html` (tabbed: graph, upload, prompts WIP, domain WIP)

### Phase 10: DI Wiring & Cleanup
- [x] Wire auth/user services and auth/course controllers in `app/containers.py`
- [x] Register auth + course blueprints in `main.py`
- [x] Move knowledge blueprint to `/knowledge` prefix
- [x] Update `app/controllers/__init__.py` exports

### Phase 11: Polish
- [x] `ruff check` and `ruff format` pass
- [ ] Manual smoke test of all routes

---

## 📋 Backlog (UI + Data Flow)
- [ ] Wire upload success to graph view handoff (carry upload/root id)
- [ ] Add graph data endpoint for UI consumption
- [ ] Render fake-generated graph path in `templates/web/knowledge/graph.html`
- [ ] Fix graph node coloring so each node type is visually distinct
- [ ] Show upload processing/completed/failed status in upload list/view
- [ ] Document local fake-gen workflow in `README.md`

## 🔒 Hardening (Later)
- [ ] Add upload validation (`secure_filename`, extension + size checks)
- [ ] Ensure production-safe debug setting from env only
- [ ] Add user-facing 404/500 handlers

---

*Updated: 2026-02-22*
