# KnowledgeGraph TODO

## ✅ Done
- [x] Removed legacy root scripts and moved to package-based app flow
- [x] Added config-driven fake graph generation toggle (`FAKE_GENERATION`)
- [x] Added fake graph factories for development data generation
- [x] Added basic test scaffold (`tests/`)
- [x] Configured structured logging via DI container + `config.yaml`

---

## 🎯 Current Focus (UI + Data Flow)
- [ ] Wire upload success to graph view handoff (carry upload/root id)
- [ ] Add graph data endpoint for UI consumption
- [ ] Render fake-generated graph path in `templates/web/knowledge/graph.html`
- [ ] Fix graph node coloring so each node type (root/conceptual/procedural/assessment) is visually distinct
- [ ] Show upload processing/completed/failed status in upload list/view
- [ ] Document local fake-gen workflow in `README.md`

---

## 🔒 Hardening (Next)
- [ ] Add upload validation (`secure_filename`, extension + size checks)
- [ ] Ensure production-safe debug setting from env only
- [ ] Add user-facing 404/500 handlers

---

*Updated: 2026-02-21*
