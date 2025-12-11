from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging
import shutil
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

from core.graph_logic import Weaver
from core.chat_bridge import ChatBridge

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NexusAPI")

app = FastAPI(title="Nexus Core API", version="2.0.4")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Components
try:
    weaver = Weaver()
    chat_bridge = ChatBridge(weaver)
    logger.info("Core components initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize core components: {e}", exc_info=True)
    # Re-raise to prevent silent failures
    raise

# In-Memory Session Storage (Could be moved to file as well for persistence)
# We will now use this only for active sessions, but persist them on creation/update
sessions_db: Dict[str, Dict] = {}

# --- Data Models ---
class ContextRequest(BaseModel):
    selected_nodes: List[str]
    depth_mode: str 

class ChatMessageRequest(BaseModel):
    session_id: str
    user_prompt: str

class EdgeRequest(BaseModel):
    source: str
    target: str
    justification: str

class EdgeSuggestionRequest(BaseModel):
    source: str
    target: str
    user_hint: Optional[str] = None

class ExpansionRequest(BaseModel):
    direction: str = "down" # "down" (breakdown) or "up" (abstraction)

class TextIngestRequest(BaseModel):
    content: str
    module: str = "General"
    main_topic: str = "Uncategorized"

class CanvasCreateRequest(BaseModel):
    name: str

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Nexus Core Operational", "version": "2.0.4"}

@app.get("/api/v2/health")
def health_check():
    """Health check endpoint for debugging"""
    import os
    from core.storage_adapter import get_storage_info
    
    health = {
        "status": "ok",
        "version": "2.0.4",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "storage": get_storage_info(),
        "vercel_env": os.getenv("VERCEL", "false")
    }
    
    try:
        # Test if components are working
        health["weaver_initialized"] = weaver is not None
        health["chat_bridge_initialized"] = chat_bridge is not None
        if chat_bridge:
            health["chat_bridge_model_available"] = chat_bridge.model is not None
    except Exception as e:
        health["error"] = str(e)
        health["status"] = "error"
    
    return health

@app.get("/api/v2/canvases")
def list_canvases():
    """Returns a list of all available canvases."""
    return weaver.canvas_registry.list_canvases()

@app.post("/api/v2/canvases")
def create_canvas(payload: CanvasCreateRequest):
    """Creates a new canvas."""
    new_id = weaver.create_canvas(payload.name)
    return {"status": "success", "canvas_id": new_id, "message": f"Canvas '{payload.name}' created"}

@app.post("/api/v2/canvases/{canvas_id}/activate")
def activate_canvas(canvas_id: str):
    """Switches the active canvas."""
    if weaver.switch_canvas(canvas_id):
        # When switching canvas, we need to clear session_db to avoid context mixups
        sessions_db.clear() 
        return {"status": "success", "message": f"Switched to canvas {canvas_id}"}
    raise HTTPException(status_code=404, detail="Canvas not found")

@app.delete("/api/v2/canvases/{canvas_id}")
def delete_canvas(canvas_id: str):
    """Deletes a canvas."""
    if weaver.delete_canvas(canvas_id):
        return {"status": "success", "message": "Canvas deleted"}
    raise HTTPException(status_code=400, detail="Cannot delete default canvas or canvas not found")

@app.get("/api/v2/graph")
def get_full_graph():
    """Returns the full graph for initial rendering."""
    nodes = []
    for n in weaver.graph.nodes():
        node_data = dict(weaver.graph.nodes[n])
        # Include position if it exists
        if "position" in node_data:
            nodes.append({"id": n, **node_data})
        else:
            nodes.append({"id": n, **node_data})
    edges = [{"source": u, "target": v, **weaver.graph.edges[u, v]} for u, v in weaver.graph.edges()]
    return {"nodes": nodes, "edges": edges}

@app.post("/api/v2/nodes/positions")
def update_node_positions(positions: Dict[str, Dict[str, float]]):
    """
    Updates positions for multiple nodes.
    positions: { node_id: { x: float, y: float }, ... }
    """
    if weaver.update_node_positions(positions):
        return {"status": "success", "message": "Positions updated"}
    raise HTTPException(status_code=400, detail="Failed to update positions")

@app.get("/api/v2/context")
def get_context_registry():
    """Returns the current hierarchy (Topics/Modules)."""
    return weaver.registry.context

@app.get("/api/v2/settings")
def get_settings():
    """Returns the global application settings."""
    return weaver.settings.settings

@app.post("/api/v2/settings")
def update_settings(updates: Dict[str, Any]):
    """Updates the global application settings."""
    weaver.settings.update_settings(updates)
    return {"status": "success", "message": "Settings updated", "settings": weaver.settings.settings}

@app.post("/api/v2/save")
def manual_save():
    """
    Manually saves all canvas data: graph, context, chat history, and settings.
    """
    save_status = weaver.save_all()
    if save_status["errors"]:
        return {
            "status": "partial",
            "message": f"Saved: {', '.join(save_status['saved'])}, Errors: {', '.join(save_status['errors'])}",
            "save_status": save_status
        }
    return {
        "status": "success",
        "message": f"All data saved successfully: {', '.join(save_status['saved'])}",
        "save_status": save_status
    }

@app.get("/api/v2/export")
def export_canvas():
    """
    Exports all canvas data as a ZIP file for backup.
    Includes: graph, context, chat history, settings, and thumbnails.
    """
    import zipfile
    import tempfile
    from pathlib import Path
    
    # Import constants from storage_adapter
    from core.storage_adapter import CANVASES_DIR, DATA_DIR, SETTINGS_FILE, CANVAS_INDEX_FILE, THUMBNAILS_DIR
    
    canvas_id = weaver.active_canvas_id
    canvas_dir = Path(CANVASES_DIR) / canvas_id
    thumbnails_dir = THUMBNAILS_DIR
    
    # Create temporary zip file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"nexus_backup_{canvas_id}_{timestamp}.zip"
    zip_path = Path(DATA_DIR) / zip_filename
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add graph.json
            graph_file = canvas_dir / "graph.json"
            if graph_file.exists():
                zipf.write(graph_file, f"{canvas_id}/graph.json")
            
            # Add context.json
            context_file = canvas_dir / "context.json"
            if context_file.exists():
                zipf.write(context_file, f"{canvas_id}/context.json")
            
            # Add chat.json
            chat_file = canvas_dir / "chat.json"
            if chat_file.exists():
                zipf.write(chat_file, f"{canvas_id}/chat.json")
            
            # Add settings.json
            settings_file = Path(SETTINGS_FILE)
            if settings_file.exists():
                zipf.write(settings_file, "settings.json")
            
            # Add canvas index
            canvas_index_file = Path(CANVAS_INDEX_FILE)
            if canvas_index_file.exists():
                zipf.write(canvas_index_file, "canvases.json")
            
            # Add all thumbnails for this canvas (filter by node IDs in graph)
            if thumbnails_dir.exists():
                node_ids = set(weaver.graph.nodes())
                for thumb_file in thumbnails_dir.glob("*"):
                    # Check if thumbnail belongs to any node in current canvas
                    # Thumbnail format: {node_id}_{uuid}.{ext}
                    if any(node_id in thumb_file.stem for node_id in node_ids):
                        zipf.write(thumb_file, f"thumbnails/{thumb_file.name}")
            
            # Add metadata file
            metadata = {
                "export_timestamp": datetime.now().isoformat(),
                "canvas_id": canvas_id,
                "canvas_name": weaver.canvas_registry.index["canvases"].get(canvas_id, {}).get("name", "Unknown"),
                "node_count": len(weaver.graph.nodes()),
                "edge_count": len(weaver.graph.edges()),
                "version": "2.0.4"
            }
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                json.dump(metadata, tmp, indent=2)
                tmp.flush()
                zipf.write(tmp.name, "metadata.json")
                os.unlink(tmp.name)
        
        logger.info(f"Exported canvas {canvas_id} to {zip_filename}")
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=zip_filename,
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/api/v2/ingest/text")
async def ingest_text(payload: TextIngestRequest):
    """
    Ingests raw text or a YouTube URL.
    """
    start_time = datetime.now()
    content = payload.content.strip()
    
    # Check for YouTube URL
    is_youtube = content.startswith("https://www.youtube.com/") or content.startswith("https://youtu.be/")
    
    node_title = "Text Note"
    final_content = content
    
    # Extract Metadata
    metadata = {} # Initialize metadata dict
    
    # 1. Try Web Scraping first if generic URL (and not YouTube)
    if not is_youtube and (content.startswith("http://") or content.startswith("https://")):
        try:
            logger.info(f"Scraping webpage: {content}")
            from core.scraper import scrape_webpage
            scraped_data = scrape_webpage(content)
            
            # Update content and title from scrape
            final_content = scraped_data["content"]
            node_title = scraped_data["title"]
            
            # Store metadata
            metadata["title"] = scraped_data["title"]
            if scraped_data["description"]:
                metadata["summary"] = scraped_data["description"]
            if scraped_data["thumbnail"]:
                metadata["thumbnail"] = scraped_data["thumbnail"]
                
            # Append source URL to content for reference
            final_content = f"Source: {content}\n\n{final_content}"
            
        except Exception as e:
            logger.error(f"Web scraping failed: {e}")
            final_content = f"Source: {content}\n\n(Scraping Failed: {str(e)})"

    # 2. Handle YouTube specific logic
    if is_youtube:
        logger.info(f"Detected YouTube URL: {content}")
        try:
            # Analyze video
            analysis = await chat_bridge.analyze_video(content)
            final_content = f"Source: {content}\n\nAnalysis:\n{analysis}"
            node_title = "Video Analysis"
            
            # Extract Video ID for metadata
            import re
            # Match standard, short, and embed URLs
            video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", content)
            if video_id_match:
                 metadata["video_id"] = video_id_match.group(1)
                 metadata["thumbnail"] = f"https://img.youtube.com/vi/{metadata['video_id']}/mqdefault.jpg"
                 
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            final_content = f"Source: {content}\n\n(Analysis Failed: {str(e)})"
    
    # Extract Metadata via AI (Refinement)
    # We send the final content (scraped text or video analysis) to Gemini for deeper structure (tags, module, better summary)
    extracted_meta = await chat_bridge.extract_metadata(final_content)
    
    # --- Two-Way Interaction: Update Registry ---
    if extracted_meta.get("proposed_new_topic"):
        p = extracted_meta["proposed_new_topic"]
        weaver.registry.update_structure(p["name"], description=p.get("description", ""))
        
    if extracted_meta.get("proposed_new_module"):
        p = extracted_meta["proposed_new_module"]
        weaver.registry.update_structure(p["topic"], module_name=p["name"], description=p.get("description", ""))
    
    # Cleanup metadata (remove proposal keys from node data)
    extracted_meta.pop("proposed_new_topic", None)
    extracted_meta.pop("proposed_new_module", None)
    # ---------------------------------------------
    
    # Merge AI metadata but preserve Scraped metadata if it's better (like Title)
    # Actually, AI might generate a better summary than OG:description, so we can overwrite summary.
    # But let's keep Title from OG if available as it's authoritative.
    
    current_title = metadata.get("title")
    metadata.update(extracted_meta)
    
    if current_title and current_title != "Text Note":
        metadata["title"] = current_title
    
    # If title wasn't extracted well, give it a timestamped default
    if not metadata.get("title") or metadata.get("title") == "Unknown Title":
        ts = datetime.now().strftime("%H:%M:%S")
        metadata["title"] = f"{node_title} {ts}"
        
    final_meta = {
        "module": payload.module if payload.module != "General" else metadata.get("module", "General"),
        "main_topic": payload.main_topic if payload.main_topic != "Uncategorized" else metadata.get("main_topic", "Uncategorized"),
        **metadata
    }
    
    # Create Node ID
    # Use title as base for ID if available, else random
    base_id = metadata.get("title", "NOTE").replace(" ", "_").upper()[:20]
    node_id = f"{base_id}_{uuid4().hex[:4]}"
    
    try:
        weaver.add_document_node(node_id, final_content, final_meta)
        
        # --- AUTO-LINKING ---
        try:
            candidates = weaver.get_node_summaries(exclude_id=node_id)
            current_node_summary = {"id": node_id, **final_meta}
            suggestions = await chat_bridge.detect_relationships(current_node_summary, candidates)
            for link in suggestions:
                target = link.get("target_id")
                justification = link.get("justification")
                if target and justification:
                    weaver.add_edge(node_id, target, justification, link.get("confidence", 0.5))
        except Exception as e:
            logger.error(f"Auto-linking failed: {e}")
        # --------------------
        
        return {"status": "success", "node_id": node_id, "message": "Content ingested"}
        
    except Exception as e:
        logger.error(f"Failed to ingest text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/ingest/upload")
async def upload_document(
    file: UploadFile = File(...), 
    module: str = Form("General"),
    main_topic: str = Form("Uncategorized")
):
    """
    Ingests a file (TXT/MD) and creates a node.
    """
    start_time = datetime.now()
    logger.info(f"[{start_time}] Received upload request: {file.filename}")
    
    try:
        filename = file.filename
        # Read content
        logger.info(f"Reading file content...")
        try:
            content = await file.read()
            content_str = content.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            raise HTTPException(status_code=400, detail="Failed to read file. Ensure it is a valid text file.")
            
        logger.info(f"Read {len(content_str)} bytes. Extracting Metadata...")
        
        # AI Metadata Extraction
        metadata = await chat_bridge.extract_metadata(content_str)
        logger.info(f"Extracted Metadata: {metadata}")
        
        # --- Two-Way Interaction: Update Registry ---
        if metadata.get("proposed_new_topic"):
            p = metadata["proposed_new_topic"]
            weaver.registry.update_structure(p["name"], description=p.get("description", ""))
            
        if metadata.get("proposed_new_module"):
            p = metadata["proposed_new_module"]
            weaver.registry.update_structure(p["topic"], module_name=p["name"], description=p.get("description", ""))
        
        # Cleanup metadata (remove proposal keys from node data)
        metadata.pop("proposed_new_topic", None)
        metadata.pop("proposed_new_module", None)
        # ---------------------------------------------
        
        final_meta = {
            "module": module if module != "General" else metadata.get("module", "General"),
            "main_topic": main_topic if main_topic != "Uncategorized" else metadata.get("main_topic", "Uncategorized"),
            **metadata
        }
        
        # Add to graph
        try:
            node_id = weaver.add_document_node(filename, content_str, final_meta)
            
            # --- AUTO-LINKING LOGIC (Ingestion Trigger) ---
            try:
                candidates = weaver.get_node_summaries(exclude_id=node_id)
                current_node_summary = {
                    "id": node_id, 
                    **final_meta
                }
                suggestions = await chat_bridge.detect_relationships(current_node_summary, candidates)
                for link in suggestions:
                    target = link.get("target_id")
                    justification = link.get("justification")
                    if target and justification:
                        weaver.add_edge(node_id, target, justification, link.get("confidence", 0.5))
            except Exception as e:
                logger.error(f"Ingestion auto-linking failed: {e}")
            # ----------------------------------------------
            
        except Exception as e:
             logger.error(f"Weaver failed to add node: {e}")
             raise HTTPException(status_code=500, detail="Database write failed.")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"[{end_time}] Successfully created node: {node_id} (Duration: {duration}s)")
        
        return {"status": "success", "node_id": node_id, "message": f"Ingested {filename}"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected Upload Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/ingest/image")
async def upload_image(
    file: UploadFile = File(...), 
    module: str = Form("General"),
    main_topic: str = Form("Uncategorized")
):
    """
    Ingests an image, analyzes it with AI (OCR + content analysis), and creates a node.
    """
    start_time = datetime.now()
    logger.info(f"[{start_time}] Received image upload request: {file.filename}")
    
    try:
        # Validate image type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image bytes
        image_bytes = await file.read()
        logger.info(f"Read {len(image_bytes)} bytes of image data")
        
        # Analyze image with AI
        logger.info("Analyzing image with Gemini Vision API...")
        analysis_result = await chat_bridge.analyze_image(image_bytes, file.content_type)
        logger.info(f"Image analysis complete: {analysis_result.get('title', 'Unknown')}")
        
        # Extract content and metadata
        content = analysis_result.get("content", "Image content extracted via AI analysis.")
        metadata = {
            "title": analysis_result.get("title", "Analyzed Image"),
            "summary": analysis_result.get("summary", "Image analyzed and processed."),
            "tags": analysis_result.get("tags", []),
            "module": analysis_result.get("module", "General"),
            "main_topic": analysis_result.get("main_topic", "Uncategorized"),
            "type": "Image",
            "thumbnail": None  # Will be set after saving
        }
        
        # Save image to disk and set thumbnail path
        import base64
        from pathlib import Path
        from core.storage_adapter import THUMBNAILS_DIR
        
        # Use storage adapter for thumbnails
        thumbnails_dir = THUMBNAILS_DIR
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
        thumbnail_filename = f"{uuid4().hex}.{file_ext}"
        thumbnail_path = thumbnails_dir / thumbnail_filename
        
        # Save image
        with open(thumbnail_path, 'wb') as f:
            f.write(image_bytes)
        
        # Set thumbnail path (relative to serve from backend)
        metadata["thumbnail"] = f"/api/v2/thumbnails/{thumbnail_filename}"
        
        # --- Two-Way Interaction: Update Registry ---
        if analysis_result.get("proposed_new_topic"):
            p = analysis_result["proposed_new_topic"]
            weaver.registry.update_structure(p["name"], description=p.get("description", ""))
            
        if analysis_result.get("proposed_new_module"):
            p = analysis_result["proposed_new_module"]
            weaver.registry.update_structure(p["topic"], module_name=p["name"], description=p.get("description", ""))
        
        # Cleanup metadata
        analysis_result.pop("proposed_new_topic", None)
        analysis_result.pop("proposed_new_module", None)
        # ---------------------------------------------
        
        # Override with form values if provided
        final_meta = {
            "module": module if module != "General" else metadata.get("module", "General"),
            "main_topic": main_topic if main_topic != "Uncategorized" else metadata.get("main_topic", "Uncategorized"),
            **metadata
        }
        
        # Create Node ID
        base_id = metadata.get("title", "IMAGE").replace(" ", "_").upper()[:20]
        node_id = f"{base_id}_{uuid4().hex[:4]}"
        
        # Add to graph
        try:
            weaver.add_document_node(node_id, content, final_meta)
            
            # --- AUTO-LINKING ---
            try:
                candidates = weaver.get_node_summaries(exclude_id=node_id)
                current_node_summary = {"id": node_id, **final_meta}
                suggestions = await chat_bridge.detect_relationships(current_node_summary, candidates)
                for link in suggestions:
                    target = link.get("target_id")
                    justification = link.get("justification")
                    if target and justification:
                        weaver.add_edge(node_id, target, justification, link.get("confidence", 0.5))
            except Exception as e:
                logger.error(f"Auto-linking failed: {e}")
            # --------------------
            
        except Exception as e:
            logger.error(f"Failed to add image node: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"[{end_time}] Successfully created image node: {node_id} (Duration: {duration}s)")
        
        return {"status": "success", "node_id": node_id, "message": f"Image analyzed and ingested"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected Image Upload Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/thumbnails/{filename}")
async def get_thumbnail(filename: str):
    """
    Serves thumbnail images.
    """
    from fastapi.responses import FileResponse
    from pathlib import Path
    from core.storage_adapter import THUMBNAILS_DIR
    
    thumbnail_path = THUMBNAILS_DIR / filename
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(thumbnail_path)

@app.post("/api/v2/ingest/edge")
def create_edge(payload: EdgeRequest):
    """
    Manually creates a justified edge between nodes.
    """
    success = weaver.add_edge(payload.source, payload.target, payload.justification)
    if not success:
        raise HTTPException(status_code=400, detail="One or both nodes not found, or hierarchy violation.")
    return {"status": "success", "message": "Edge created"}

@app.put("/api/v2/edges")
def update_edge(source: str, target: str, updates: Dict[str, Any]):
    """
    Updates edge attributes (e.g. justification).
    """
    if not weaver.update_edge(source, target, updates):
        raise HTTPException(status_code=404, detail="Edge not found")
    return {"status": "success", "message": "Edge updated"}

@app.delete("/api/v2/edges")
def delete_edge(source: str, target: str):
    if not weaver.delete_edge(source, target):
        raise HTTPException(status_code=404, detail="Edge not found")
    logger.info(f"Deleted edge: {source} -> {target}")
    return {"status": "success", "message": "Edge deleted"}

@app.post("/api/v2/edges/suggest")
async def suggest_edge_justification(payload: EdgeSuggestionRequest):
    """
    Generates an AI justification for a potential edge.
    """
    justification = await chat_bridge.generate_edge_justification(payload.source, payload.target, payload.user_hint)
    return {"status": "success", "justification": justification}

@app.post("/api/v2/nodes/{node_id}/expand")
async def expand_node(node_id: str, payload: ExpansionRequest):
    """
    Expands a node by creating AI-generated sub-nodes (MECE) or abstracting upwards.
    """
    if node_id not in weaver.graph.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
        
    created_nodes = []
    
    if payload.direction == "down":
        # Generate breakdown
        suggestions = await chat_bridge.generate_mece_breakdown(node_id)
        
        for item in suggestions:
            # Create new node
            new_id = f"{item.get('title', 'SUB').replace(' ', '_').upper()[:15]}_{uuid4().hex[:4]}"
            meta = {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "tags": item.get("tags", []),
                "node_type": item.get("node_type", "child"),
                # Inherit module/topic from parent usually, but AI might suggest different
                "module": weaver.graph.nodes[node_id].get("module", "General"),
                "main_topic": weaver.graph.nodes[node_id].get("main_topic", "Uncategorized")
            }
            
            weaver.add_document_node(new_id, item.get("content", ""), meta)
            
            # Create Edge: New Node -> Source Node (Child points to Parent)
            justification = item.get("justification", "Sub-component of parent")
            weaver.add_edge(new_id, node_id, justification)
            
            created_nodes.append(new_id)
            
    elif payload.direction == "up":
        # Generate abstraction
        item = await chat_bridge.generate_abstraction(node_id)
        if item:
            new_id = f"{item.get('title', 'PARENT').replace(' ', '_').upper()[:15]}_{uuid4().hex[:4]}"
            meta = {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "node_type": item.get("node_type", "parent"),
                "module": "General", # Parent might be general
                "main_topic": "Uncategorized"
            }
            
            weaver.add_document_node(new_id, item.get("content", ""), meta)
            
            # Create Edge: Source Node -> New Node (Child points to Parent)
            justification = item.get("justification", " abstracted from child")
            weaver.add_edge(node_id, new_id, justification)
            
            created_nodes.append(new_id)
            
    return {"status": "success", "created_nodes": created_nodes}

@app.post("/api/v2/nodes/{node_id}/rewrite")
async def rewrite_node(node_id: str):
    """
    Rewrites a node's description AND content based on its connections.
    """
    result = await chat_bridge.rewrite_node_context_aware(node_id)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # Automatically apply updates
    updates = {}
    if result.get("summary"):
        updates["summary"] = result["summary"]
    if result.get("content"):
        updates["content"] = result["content"]
    if result.get("suggested_topic"):
        updates["main_topic"] = result["suggested_topic"]
    if result.get("suggested_module"):
        updates["module"] = result["suggested_module"]
        
    weaver.update_node(node_id, updates)
    
    return {"status": "success", "message": "Node rewritten", "updates": updates, "node": weaver.graph.nodes[node_id]}

@app.post("/api/v2/nodes/{node_id}/analyze")
async def analyze_node(node_id: str):
    """
    Manually triggers AI metadata extraction for an existing node.
    """
    logger.info(f"Received analysis request for node: {node_id}")
    
    if node_id not in weaver.graph.nodes:
         logger.error(f"Node not found: {node_id}")
         raise HTTPException(status_code=404, detail="Node not found")

    node = weaver.graph.nodes[node_id]
    
    content = node.get("content", "")
    if not content:
        logger.error(f"Node {node_id} has no content.")
        raise HTTPException(status_code=400, detail="Node has no content to analyze")
    
    logger.info(f"Extracting metadata for content length: {len(content)}")
    
    # Extract Metadata
    metadata = await chat_bridge.extract_metadata(content)
    logger.info(f"AI returned metadata: {metadata}")
    
    # --- Two-Way Interaction: Update Registry ---
    if metadata.get("proposed_new_topic"):
        p = metadata["proposed_new_topic"]
        weaver.registry.update_structure(p["name"], description=p.get("description", ""))
        
    if metadata.get("proposed_new_module"):
        p = metadata["proposed_new_module"]
        weaver.registry.update_structure(p["topic"], module_name=p["name"], description=p.get("description", ""))
    
    # Cleanup metadata
    metadata.pop("proposed_new_topic", None)
    metadata.pop("proposed_new_module", None)
    # ---------------------------------------------
    
    # Update Node
    updates = {**metadata}
    
    # Logic: If current is Default, overwrite. If AI suggests something new, overwrite.
    # Current implementation: Just overwrite with AI's best guess for now.
    
    # Update NetworkX graph
    for key, value in updates.items():
        weaver.graph.nodes[node_id][key] = value
        
    weaver.save_graph()
    logger.info(f"Graph updated and saved for node {node_id}")
    
    # --- AUTO-LINKING LOGIC ---
    try:
        candidates = weaver.get_node_summaries(exclude_id=node_id)
        current_node_summary = {
            "id": node_id,
            "title": updates.get("title", node_id),
            "summary": updates.get("summary", ""),
            "tags": updates.get("tags", []),
            "module": updates.get("module", "General"),
            "main_topic": updates.get("main_topic", "Uncategorized")
        }
        suggestions = await chat_bridge.detect_relationships(current_node_summary, candidates)
        
        edges_created = 0
        for link in suggestions:
            target = link.get("target_id")
            justification = link.get("justification")
            confidence = link.get("confidence", 0.5)
            
            if target and justification and confidence > 0.6: 
                if weaver.add_edge(node_id, target, justification, confidence):
                    edges_created += 1
        
        if edges_created > 0:
            logger.info(f"Auto-linked {node_id} to {edges_created} nodes.")
            
    except Exception as e:
        logger.error(f"Auto-linking failed: {e}", exc_info=True)
    # --------------------------
    
    updated_node = {"id": node_id, **weaver.graph.nodes[node_id]}
    return {
        "status": "success", 
        "message": "Metadata updated", 
        "node": updated_node
    }

@app.delete("/api/v2/nodes/{node_id}")
def delete_node(node_id: str):
    if not weaver.delete_node(node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    logger.info(f"Deleted node: {node_id}")
    return {"status": "success", "message": "Node deleted"}

@app.put("/api/v2/nodes/{node_id}")
async def update_node(
    node_id: str, 
    thumbnail: UploadFile = File(None),
    title: Optional[str] = Form(None),
    summary: Optional[str] = Form(None),
    module: Optional[str] = Form(None),
    main_topic: Optional[str] = Form(None),
    node_type: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    content: Optional[str] = Form(None)
):
    """
    Updates node attributes. Can optionally upload a thumbnail image.
    Accepts form data for all fields including thumbnail file.
    """
    if node_id not in weaver.graph:
        raise HTTPException(status_code=404, detail="Node not found")
    
    updates = {}
    
    # Handle thumbnail upload if provided
    if thumbnail:
        try:
            # Validate image type
            if not thumbnail.content_type or not thumbnail.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Read image bytes
            image_bytes = await thumbnail.read()
            
            # Save thumbnail
            from pathlib import Path
            from core.storage_adapter import THUMBNAILS_DIR
            
            thumbnails_dir = THUMBNAILS_DIR
            thumbnails_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            file_ext = thumbnail.filename.split('.')[-1] if '.' in thumbnail.filename else 'png'
            thumbnail_filename = f"{node_id}_{uuid4().hex[:8]}.{file_ext}"
            thumbnail_path = thumbnails_dir / thumbnail_filename
            
            # Save image
            with open(thumbnail_path, 'wb') as f:
                f.write(image_bytes)
            
            # Update node with thumbnail path
            updates["thumbnail"] = f"/api/v2/thumbnails/{thumbnail_filename}"
            logger.info(f"Thumbnail uploaded for node {node_id}: {thumbnail_filename}")
        except Exception as e:
            logger.error(f"Failed to upload thumbnail: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload thumbnail: {str(e)}")
    
    # Handle other form fields
    if title is not None:
        updates["title"] = title
    if summary is not None:
        updates["summary"] = summary
    if module is not None:
        updates["module"] = module
    if main_topic is not None:
        updates["main_topic"] = main_topic
    if node_type is not None:
        updates["node_type"] = node_type
    if color is not None:
        updates["color"] = color
    if tags is not None:
        # Parse tags from comma-separated string
        updates["tags"] = [t.strip() for t in tags.split(',') if t.strip()]
    if content is not None:
        updates["content"] = content
    
    # Update node
    if updates:
        if not weaver.update_node(node_id, updates):
            raise HTTPException(status_code=500, detail="Failed to update node")
        logger.info(f"Updated node: {node_id}")
        node_data = dict(weaver.graph.nodes[node_id])
        return {"status": "success", "message": "Node updated", "node": node_data}
    else:
        # Return current node data even if no updates
        node_data = dict(weaver.graph.nodes[node_id])
        return {"status": "success", "message": "No updates provided", "node": node_data}

@app.delete("/api/v2/edges")
def delete_edge(source: str, target: str):
    if not weaver.delete_edge(source, target):
        raise HTTPException(status_code=404, detail="Edge not found")
    logger.info(f"Deleted edge: {source} -> {target}")
    return {"status": "success", "message": "Edge deleted"}

@app.post("/api/v2/chat/context")
def calculate_context(payload: ContextRequest):
    depth_map = {"F0": 0, "F1": 1, "F2": 2}
    depth = depth_map.get(payload.depth_mode, 0)
    
    context_data = chat_bridge.calculate_context(payload.selected_nodes, depth)
    
    session_id = str(uuid4())
    
    new_session = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "config": {
            "selected_nodes": payload.selected_nodes,
            "depth_mode": payload.depth_mode,
            "resolved_context": [n["id"] for n in context_data["context_nodes"]]
        },
        "context_data": context_data, 
        "messages": [],
        "dominant_module": context_data["dominant_module"]
    }
    
    sessions_db[session_id] = new_session
    
    return {
        "session_id": session_id,
        "context_nodes": context_data["context_nodes"],
        "context_edges": context_data["context_edges"],
        "dominant_module": context_data["dominant_module"]
    }

@app.post("/api/v2/chat/message")
async def send_message(payload: ChatMessageRequest):
    session = sessions_db.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    user_msg = {
        "id": str(uuid4()),
        "role": "user",
        "content": payload.user_prompt,
        "timestamp": datetime.now().isoformat()
    }
    session["messages"].append(user_msg)
    
    response_text = await chat_bridge.generate_response(
        session["messages"][:-1], 
        session["context_data"],
        payload.user_prompt
    )
    
    assistant_msg = {
        "id": str(uuid4()),
        "role": "assistant",
        "content": response_text,
        "timestamp": datetime.now().isoformat()
    }
    session["messages"].append(assistant_msg)
    
    # Autosave chat history (PERSISTENCE)
    # We update the internal history of Weaver which writes to disk
    weaver.chat_history.append({"session_id": payload.session_id, "messages": session["messages"]})
    weaver.save_chat_history(weaver.chat_history)
    
    return assistant_msg

@app.get("/api/v2/chat/history/{session_id}")
def get_history(session_id: str):
    session = sessions_db.get(session_id)
    if not session:
        # Check if we can hydrate from persistent storage (optional enhancement)
        raise HTTPException(status_code=404, detail="Session not found")
    return session
