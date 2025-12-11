# Implementation Plan & Version History

## Versioning Strategy
- **Format:** `v2.X.Y` (Major.Minor.Patch)
- **Timestamping:** Every version update includes a UTC timestamp.
- **Cycle:** Updated after every completed user request/feature implementation.

## Current Version
**Version:** v2.1.0
**Timestamp:** 2025-01-XX XX:XX:XX UTC
**Status:** Vercel Deployment Ready (Serverless Functions + Storage Adapter)

---

## Recent Updates

### v2.1.0 (Vercel Deployment Support)
- [x] **Vercel Serverless Functions**:
    - [x] Created `api/[...path].py` handler using Mangum for FastAPI compatibility
    - [x] Updated `vercel.json` configuration for routing and builds
    - [x] Added `requirements.txt` at root level for Python dependencies
- [x] **Storage Adapter**:
    - [x] Created `backend/core/storage_adapter.py` for serverless environment compatibility
    - [x] Automatic detection of Vercel environment
    - [x] Fallback to `/tmp` for ephemeral storage on Vercel
    - [x] Updated all file paths to use Path objects for cross-platform compatibility
- [x] **Frontend Configuration**:
    - [x] Updated `frontend/src/api.js` to use relative URLs for Vercel deployment
    - [x] Maintained localhost fallback for development
- [x] **Documentation**:
    - [x] Created `VERCEL_DEPLOYMENT.md` with deployment instructions
    - [x] Added `.vercelignore` for build optimization
    - [x] Documented storage limitations and solutions

### v2.0.9 (Canvas Management & AI Tools)
- [x] **Multi-Canvas Management** (REQ-017):
    - [x] Backend `CanvasRegistry` for managing isolated graph/context environments.
    - [x] Frontend `CanvasManager` UI for browsing, creating, and switching projects.
    - [x] Persistent storage separation per canvas (`data/canvases/{id}/`).
- [x] **AI Hierarchy Expansion** (REQ-016):
    - [x] MECE Breakdown (Top-Down) and Abstraction (Bottom-Up) algorithms.
    - [x] UI Controls in `NodeInspector` for expansion.
- [x] **Chat UI Overhaul** (REQ-015):
    - [x] Modern, bubble-less, document-style chat interface.
    - [x] Full Markdown/Table support.
    - [x] "Turn to Doc" feature.
    - [x] Resizable Layout.
- [x] **Refined User Experience** (REQ-014):
    - [x] AI-assisted Manual Connections (`EdgeCreationModal`).
    - [x] Context-aware Node Rewriting.
    - [x] Fixed UI flickering bugs.

### v2.0.8 (Visuals & Settings)
- [x] **Global Settings Management** (REQ-013):
    - [x] `SettingsRegistry` backend persistence.
    - [x] Frontend UI (`SettingsModal`) to toggle Auto-Linking and thresholds.
- [x] **Edge Management**:
    - [x] `EdgeInspector` UI for viewing, editing justifications, and deleting edges.
- [x] **Apple-Style Node Design** (REQ-012):
    - [x] Redesigned Nodes: Glassmorphism, distinct shapes for Topics (Pill), Modules (Card), Children.
    - [x] Smart Layout: `dagre` now respects node type sizes.

## Backlog & Roadmap

### Phase 1: Foundation (Completed)
- [x] Basic Backend Setup (FastAPI, NetworkX)
- [x] Basic Frontend Setup (React, React Flow)
- [x] Chat Bridge Integration (Gemini 1.5/2.5)
- [x] Graph Visualization (Lasso, Depth F0/F1/F2)

### Phase 2: Data Ingestion & Management (Completed)
- [x] **Remove Placeholder Data**: Clear hardcoded seeds in `Weaver`.
- [x] **File Management System**:
    - [x] API for File Upload (Markdown/Text).
    - [x] Storage subsystem (Local file storage for documents).
- [x] **Ingestion Logic (The Weaver)**:
    - [x] Convert uploaded files into Graph Nodes.
    - [x] Basic "Registry" for defining edge logic (mock implementation).
- [x] **Persistence**:
    - [x] Save Graph state to disk (JSON/DB).
    - [x] Save Chat Sessions to disk.

### Phase 3: Advanced Features (Next Steps)
- [ ] **Real-time Collaboration**: WebSockets for multi-user editing.
- [ ] **Search & Filtering**: Global search across all nodes and canvases.
- [ ] **Export Options**: Export canvas to PDF/Image/JSON.
- [ ] **Knowledge Graph Analytics**: Centrality metrics, cluster detection.
