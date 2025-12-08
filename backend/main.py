from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging
import shutil
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from core.graph_logic import Weaver
from core.chat_bridge import ChatBridge

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NexusAPI")

app = FastAPI(title="Nexus Core API", version="2.0.2")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Components
weaver = Weaver()
chat_bridge = ChatBridge(weaver)

# In-Memory Session Storage (Could be moved to file as well for persistence)
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

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Nexus Core Operational", "version": "2.0.2"}

@app.get("/api/v2/graph")
def get_full_graph():
    """Returns the full graph for initial rendering."""
    nodes = [{"id": n, **weaver.graph.nodes[n]} for n in weaver.graph.nodes()]
    edges = [{"source": u, "target": v, **weaver.graph.edges[u, v]} for u, v in weaver.graph.edges()]
    return {"nodes": nodes, "edges": edges}

@app.post("/api/v2/ingest/upload")
async def upload_document(
    file: UploadFile = File(...), 
    module: str = Form("General")
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
        
        final_meta = {"module": module, **metadata}
        
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

@app.post("/api/v2/ingest/edge")
def create_edge(payload: EdgeRequest):
    """
    Manually creates a justified edge between nodes.
    """
    success = weaver.add_edge(payload.source, payload.target, payload.justification)
    if not success:
        raise HTTPException(status_code=400, detail="One or both nodes not found")
    return {"status": "success", "message": "Edge created"}

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
    
    # Update Node
    updates = {**metadata}
    
    current_module = node.get("module", "General")
    if current_module == "General" and "suggested_module" in metadata:
        updates["module"] = metadata["suggested_module"]
        
    updates.pop("suggested_module", None)
    
        # Update NetworkX graph
    for key, value in updates.items():
        weaver.graph.nodes[node_id][key] = value
        
    weaver.save_graph()
    logger.info(f"Graph updated and saved for node {node_id}")
    
    # --- AUTO-LINKING LOGIC ---
    # After successful metadata update, check for relationships
    try:
        # Get Candidates (All other nodes)
        candidates = weaver.get_node_summaries(exclude_id=node_id)
        
        # Prepare current node data
        current_node_summary = {
            "id": node_id,
            "title": updates.get("title", node_id),
            "summary": updates.get("summary", ""),
            "tags": updates.get("tags", []),
            "module": updates.get("module", "General")
        }
        
        # Ask AI
        suggestions = await chat_bridge.detect_relationships(current_node_summary, candidates)
        
        # Apply Edges
        edges_created = 0
        for link in suggestions:
            target = link.get("target_id")
            justification = link.get("justification")
            confidence = link.get("confidence", 0.5)
            
            if target and justification and confidence > 0.6: # Threshold
                if weaver.add_edge(node_id, target, justification, confidence):
                    edges_created += 1
        
        if edges_created > 0:
            logger.info(f"Auto-linked {node_id} to {edges_created} nodes.")
            
    except Exception as e:
        logger.error(f"Auto-linking failed: {e}", exc_info=True)
    # --------------------------
    
    # Return the FULL updated node data
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
def update_node(node_id: str, updates: Dict[str, Any]):
    if not weaver.update_node(node_id, updates):
        raise HTTPException(status_code=404, detail="Node not found")
    logger.info(f"Updated node: {node_id}")
    return {"status": "success", "message": "Node updated"}

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
    
    return assistant_msg

@app.get("/api/v2/chat/history/{session_id}")
def get_history(session_id: str):
    session = sessions_db.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
