# Nexus Core v2.0 - Prototype

This is a functional prototype of the Nexus Core v2.0 Contextual Chat Module, implemented according to the SRS and PRD.

## Prerequisites

- Python 3.9+
- Node.js 16+
- Google Gemini API Key (Required for Chat features)

## Configuration

Before running the application, you need to set up your Google Gemini API key:

1. Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a `.env` file in the `backend/` directory:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```
3. Alternatively, you can set the `GEMINI_API_KEY` environment variable in your system.

**Note:** The `.env` file is already in `.gitignore` and will not be committed to the repository.

## Project Structure

- `backend/`: FastAPI application with NetworkX graph logic.
- `frontend/`: React application with React Flow and Tailwind CSS.
- `docs/`: Implementation logs and plans.

## Setup & Run

### Local Development

We provide a robust launcher for Windows.

1.  **Run the Launcher:**
    ```powershell
    .\start_nexus.bat
    ```
    This script will:
    -   Check for Python and Node.js.
    -   Install Node.js via Winget if missing.
    -   Set up the Python Virtual Environment.
    -   Install dependencies.
    -   Launch Backend and Frontend servers.
    -   Open your browser to `http://localhost:5173`.

### Vercel Deployment

For deploying to Vercel, see [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md) for detailed instructions.

**Quick Start:**
1. Push your code to a Git repository
2. Import the project in Vercel
3. Set `GEMINI_API_KEY` environment variable
4. Deploy!

**Note:** Vercel uses ephemeral storage (`/tmp`). For production, consider using Vercel Blob Storage or an external database (see deployment guide).

## Features

### 1. Data Ingestion (New in v2.0.2)
-   Click the **Blue Plus (+)** button in the bottom-right of the graph.
-   Upload Markdown (`.md`) or Text (`.txt`) files.
-   Assign a Module Tag (e.g., "Payments").
-   The file becomes a **Graph Node**.

### 2. Graph Interaction
-   **View Graph**: Visualize your ingested documents as nodes.
-   **Lasso Select**: Hold `Shift` + `Left Click & Drag` to select multiple nodes.
-   **Context Depth**: Use the toolbar (top-left) to toggle `F0` (Selection), `F1` (Neighbors), `F2` (Extended).

### 3. Contextual Chat
-   Select nodes and click **Chat with Selection**.
-   Ask questions. Nexus uses **only** the selected graph context to answer.
-   **Citations**: Answers include `[NODE-ID]` citations.

## Persistence
-   Graph data is saved to `backend/data/nexus_graph.json`.
-   Data persists across server restarts.
