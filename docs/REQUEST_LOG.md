# Request Log

## Request ID: REQ-001
**Date:** 2025-12-08
**User Query:** "read and implement" (Initial Prototype)
**Deliverables:**
- Scaffolded Backend (FastAPI).
- Scaffolded Frontend (React + Tailwind).
- Implemented `Weaver` graph logic (F0-F2).
- Implemented `ChatBridge` with Gemini.
- Created `start_nexus.bat` for easy launch.

## Request ID: REQ-002
**Date:** 2025-12-08
**User Query:** "get me something like a bat file to run everything at once"
**Deliverables:**
- Created `start_nexus.bat`.

## Request ID: REQ-003
**Date:** 2025-12-08
**User Query:** "this is my key... use gemini flash 2.5"
**Deliverables:**
- Updated Backend to use `gemini-2.5-flash-preview-09-2025`.
- Updated batch file to set `GEMINI_API_KEY`.

## Request ID: REQ-004
**Date:** 2025-12-08
**User Query:** "Cant see the Frontend... fix bat file"
**Deliverables:**
- Refactored `start_nexus.bat` to handle Node.js installation detection and environment setup robustly.

## Request ID: REQ-005
**Date:** 2025-12-08
**User Query:** "remove placeholder data, file management system, ingest documents"
**Deliverables:**
- Removed seed data.
- Implemented Persistence (JSON).
- Implemented File Upload API & UI.
- Implemented Ingestion Logic.

## Request ID: REQ-006
**Date:** 2025-12-08
**User Query:** "why it takes forever to upload... fix"
**Deliverables:**
- Fixed `uvicorn` reload loop by moving data directory.
- Added absolute path resolution.
- Added debug logs.

## Request ID: REQ-007
**Date:** 2025-12-08
**User Query:** "stuck at uploading... fix"
**Deliverables:**
- Fixed `Content-Type` header issue in `api.js` (Boundary bug).
- Implemented `IngestionWidget` (Minimizable, Progress, Logs).
- Added timeouts and better error handling.

## Request ID: REQ-008 (Current)
**Date:** 2025-12-08
**User Query:** "Graph drag link not working, file content view, AI metadata parsing"
**Status:** In Progress
**Plan:**
1.  **Graph Interaction**: Implement `onConnect` in React Flow with a "Justification" prompt to create edges.
2.  **Node Viewer**: Add a UI component to view node content/metadata.
3.  **AI Ingestion**: Integrate Gemini to parse metadata (Title, Summary) during file upload.

## Request ID: REQ-009
**Date:** 2025-12-09
**User Query:** "clone from https://github.com/pdtoan2811-bit/nexus-ver3"
**Deliverables:**
- Cloned repository into workspace.
- Organized file structure.
- Verified environment.

## Request ID: REQ-010
**Date:** 2025-12-09
**User Query:** "check why I got LLM unvailable error messages... use this one: [KEY]"
**Deliverables:**
- Created `backend/.env` with provided API key.
- Updated `backend/main.py` to force load `.env` variables, overriding potential stale system variables.
- Verified `ChatBridge` initialization logic.

## Request ID: REQ-011
**Date:** 2025-12-09
**User Query:** "create Nexus own data entities... two way interaction... context registry"
**Deliverables:**
- **Backend**: Implemented `ContextRegistry` in `graph_logic.py` to persist Topic/Module hierarchy.
- **Backend**: Updated `ChatBridge` to use the registry for context-aware metadata extraction and propose new structures.
- **Backend**: Updated `main.py` to handle `main_topic` and two-way registry updates during ingestion.
- **Frontend**: Created `ContextRegistryPanel` to visualize the knowledge hierarchy.
- **Frontend**: Updated `IngestionWidget` and `NodeInspector` to support "Main Topic" field.

## Request ID: REQ-012
**Date:** 2025-12-09
**User Query:** "improve node design with shapes, effect, color scheme... intuitive position arrangement... Apple UI UX"
**Deliverables:**
- **Apple-Style UI/UX**: 
    - Implemented Glassmorphism (`backdrop-blur-xl`, `border-white/10`) across all nodes.
    - Defined distinct visual templates for **Topic** (Large Pill), **Module** (Structured Card), and **Child** (Minimal Card).
    - Used iOS System Colors in backend palette.
- **Intuitive Layout**:
    - Updated `dagre` layout logic to allocate variable space based on node type.
    - Enforced hierarchical flow (`TB/LR`) that respects the `Topic > Module > Child` structure visually.
- **Strict Data Hierarchy**: 
    - Backend enforces edge direction (Child -> Parent -> Module -> Topic).
    - Frontend Inspector allows manual "Node Type" reassignment.

## Request ID: REQ-013
**Date:** 2025-12-09
**User Query:** "get me a config to adjust the nodes connection feature... turn automation off/adjust number... edit/delete nodes connection"
**Deliverables:**
- **Global Settings**:
    - Created `SettingsRegistry` in backend (`nexus_settings.json`).
    - Implemented `SettingsModal` in frontend to toggle **Auto-Linking**, set **Max Connections**, and **Confidence Threshold**.
    - Updated `ChatBridge` to respect these settings during ingestion.
- **Edge Management**:
    - Implemented **Edge Inspector**: Click on any edge to view details.
    - Features: **Edit Justification** (Reasoning) and **Delete Connection**.
    - Updated `GraphCanvas` to handle edge selection events.

## Request ID: REQ-014
**Date:** 2025-12-09
**User Query:** "fix flickering bug, improve manual connection UI/UX, add modal for connection description, node rewrite feature"
**Deliverables:**
- **Bug Fix**: Resolved UI flickering by wrapping callbacks in `useCallback` and optimizing `GraphCanvas` state updates.
- **Manual Connection UI**:
    - Added large transparent handles to `CustomNode` for easier dragging.
    - Replaced browser prompt with `EdgeCreationModal`.
    - Added "AI Enhance" button to modal to generate justification using LLM.
    - Added "Auto Assist" setting to global config.
- **Node Rewriting**:
    - Implemented `rewrite_node_context_aware` in backend.
    - Added "Rewrite" button (Wand icon) to `NodeInspector`.
    - Updates Title, Summary, Content, Topic, and Module based on neighbors.

## Request ID: REQ-015
**Date:** 2025-12-09
**User Query:** "enhance chat experience (no bubbles, table parsing, loading state, turn to doc), better typography, adjustable size"
**Deliverables:**
- **Chat UI Overhaul**:
    - Removed chat bubbles for a centered, document-style layout.
    - Integrated `react-markdown` and `remark-gfm` for full Markdown and Table support.
    - Added "Thinking..." indicator.
    - Added "Turn to Doc" button to save AI responses as nodes.
- **Typography & Layout**:
    - Switched to `Inter` font (Google Sans alternative).
    - Implemented resizable split-pane layout with drag handle.
    - Added Maximize/Minimize toggle for chat view.
- **System Prompt**:
    - Updated `ChatBridge` system instruction to enforce rich Markdown formatting (H1, H2, Bold, Tables).

## Request ID: REQ-016
**Date:** 2025-12-09
**User Query:** "MECE breakdown, AI abstraction, fill all node details"
**Deliverables:**
- **AI Hierarchy Expansion**:
    - Implemented `generate_mece_breakdown` (Top-Down) to create sub-nodes.
    - Implemented `generate_abstraction` (Bottom-Up) to create parent nodes.
    - Added "Break Down" and "Abstract" buttons to `NodeInspector`.
- **Configurable AI**:
    - Added `expansion` (Max Sub-nodes) and `content_generation` (Tone, Detail Level) settings to `SettingsRegistry`.
    - Exposed these settings in `SettingsModal`.

## Request ID: REQ-017
**Date:** 2025-12-09
**User Query:** "create new canva, manage canvas like by browse through them - which mean auto save canva and conversation inside each canva etc"
**Deliverables:**
- **Canvas Management System**:
    - Backend: Created `CanvasRegistry` to manage multiple canvas instances (`nexus_graph.json`, `nexus_context.json`, `chat.json` per canvas).
    - Backend: Updated `Weaver` to switch contexts dynamically based on active canvas ID.
    - Backend: Added API endpoints for Create, List, Activate, and Delete Canvas.
- **Frontend UI**:
    - Created `CanvasManager` component: A visual gallery to browse, create, delete, and switch canvases.
    - Added "Manage Canvases" button to the main toolbar.
    - Implemented persistence logic ensuring each canvas retains its own Graph and Context Registry.

## Request ID: REQ-018
**Date:** 2025-01-XX
**User Query:** "I want to modify this one for me to easy deploy on vercel"
**Deliverables:**
- **Vercel Serverless Functions**:
    - Created `api/[...path].py` handler using Mangum to wrap FastAPI for Vercel compatibility
    - Updated `vercel.json` with proper routing and build configuration
    - Added `requirements.txt` at root level for Python dependencies (including `mangum`)
- **Storage Adapter**:
    - Created `backend/core/storage_adapter.py` to handle serverless environment
    - Automatic detection of Vercel environment (`VERCEL` env variable)
    - Uses `/tmp/nexus_data` for ephemeral storage on Vercel
    - Falls back to `data/` directory for local development
    - Updated all file path references to use `Path` objects for cross-platform compatibility
- **Frontend Configuration**:
    - Updated `frontend/src/api.js` to use relative URLs (`/api/v2`) for production
    - Maintained localhost fallback (`http://localhost:8000/api/v2`) for development
    - Uses `import.meta.env.DEV` to detect environment
- **Build Configuration**:
    - Created root-level `package.json` for Vercel build settings
    - Added `.vercelignore` to exclude unnecessary files from deployment
    - Configured build command: `cd frontend && npm install && npm run build`
    - Set output directory: `frontend/dist`
- **Documentation**:
    - Created `VERCEL_DEPLOYMENT.md` with comprehensive deployment guide
    - Documented storage limitations and solutions (Vercel Blob, external databases)
    - Updated `IMPLEMENTATION_PLAN.md` to v2.1.0 with deployment changes
