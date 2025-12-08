# Implementation Plan & Version History

## Versioning Strategy
- **Format:** `v2.X.Y` (Major.Minor.Patch)
- **Timestamping:** Every version update includes a UTC timestamp.
- **Cycle:** Updated after every completed user request/feature implementation.

## Current Version
**Version:** v2.0.2
**Timestamp:** 2025-12-08 15:00:00 UTC
**Status:** Prototype (Graph + Chat Basic Integration)

---

## Recent Updates
- [x] Configured valid Google Gemini API key.
- [x] Verified dependency integration with new key.

## Backlog & Roadmap

### Phase 1: Foundation (Completed)
- [x] Basic Backend Setup (FastAPI, NetworkX)
- [x] Basic Frontend Setup (React, React Flow)
- [x] Chat Bridge Integration (Gemini 1.5/2.5)
- [x] Graph Visualization (Lasso, Depth F0/F1/F2)

### Phase 2: Data Ingestion & Management (Current Focus)
- [ ] **Remove Placeholder Data**: Clear hardcoded seeds in `Weaver`.
- [ ] **File Management System**:
    - [ ] API for File Upload (Markdown/Text).
    - [ ] Storage subsystem (Local file storage for documents).
- [ ] **Ingestion Logic (The Weaver)**:
    - [ ] Convert uploaded files into Graph Nodes.
    - [ ] Basic "Registry" for defining edge logic (mock implementation).
- [ ] **Persistence**:
    - [ ] Save Graph state to disk (JSON/DB).
    - [ ] Save Chat Sessions to disk.

### Phase 3: Advanced Features (Upcoming)
- [ ] Entity Normalization (Synonym resolution).
- [ ] Advanced Edge Justification extraction (NLP).
- [ ] Session History / Management UI (Sidebar).

