import networkx as nx
from typing import List, Dict, Set, Any, Optional
import logging
import json
import os
import shutil
import random
from datetime import datetime

logger = logging.getLogger(__name__)

# FIX: Use Absolute Path to prevent ambiguity
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Points to backend/
ROOT_DIR = os.path.dirname(BASE_DIR) # Points to project root/
DATA_DIR = os.path.join(ROOT_DIR, "data")
CANVASES_DIR = os.path.join(DATA_DIR, "canvases")
CANVAS_INDEX_FILE = os.path.join(DATA_DIR, "canvases.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "nexus_settings.json")

class SettingsRegistry:
    """
    Manages global application settings.
    """
    def __init__(self):
        self._ensure_data_dir()
        self.settings = self._load_settings()

    def _ensure_data_dir(self):
        if not os.path.exists(DATA_DIR):
            try:
                os.makedirs(DATA_DIR)
            except OSError as e:
                logger.error(f"Failed to create data directory: {e}")

    def _load_settings(self) -> Dict[str, Any]:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        
        # Default Settings
        default_settings = {
            "auto_linking": {
                "enabled": True,
                "max_connections": 3,
                "threshold": 0.6
            },
            "manual_connection_ai_assist": False, # Default off
            "expansion": {
                "max_subnodes": 5
            },
            "content_generation": {
                "tone": "Technical", # Technical, Concise, Creative
                "detail_level": "High"
            }
        }
        self._save_settings(default_settings)
        return default_settings

    def _save_settings(self, data: Dict[str, Any]):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Settings saved.")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def update_settings(self, updates: Dict[str, Any]):
        self.settings.update(updates)
        self._save_settings(self.settings)

    def get(self, key: str, default=None):
        return self.settings.get(key, default)

class CanvasRegistry:
    """Manages the index of available canvases."""
    def __init__(self):
        self._ensure_dirs()
        self.index = self._load_index()

    def _ensure_dirs(self):
        if not os.path.exists(CANVASES_DIR):
            os.makedirs(CANVASES_DIR)

    def _load_index(self) -> Dict[str, Any]:
        if os.path.exists(CANVAS_INDEX_FILE):
            try:
                with open(CANVAS_INDEX_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load canvas index: {e}")
        
        default_index = {
            "active_id": "default",
            "canvases": {
                "default": {
                    "id": "default",
                    "name": "Main Canvas",
                    "created_at": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat()
                }
            }
        }
        self._save_index(default_index)
        return default_index

    def _save_index(self, data: Dict[str, Any]):
        with open(CANVAS_INDEX_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def list_canvases(self) -> List[Dict[str, Any]]:
        # Add is_active flag to each canvas for frontend convenience
        canvases = []
        active_id = self.get_active_id()
        for c in self.index["canvases"].values():
             c_copy = c.copy()
             c_copy["is_active"] = (c["id"] == active_id)
             canvases.append(c_copy)
        return canvases
        return canvases

    def get_active_id(self) -> str:
        return self.index.get("active_id", "default")

    def set_active_id(self, canvas_id: str):
        if canvas_id in self.index["canvases"]:
            self.index["active_id"] = canvas_id
            self._save_index(self.index)
            return True
        return False

    def create_canvas(self, name: str) -> str:
        canvas_id = name.lower().replace(" ", "_") + "_" + datetime.now().strftime("%H%M%S")
        self.index["canvases"][canvas_id] = {
            "id": canvas_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
        self.index["active_id"] = canvas_id 
        self._save_index(self.index)
        return canvas_id

    def delete_canvas(self, canvas_id: str) -> bool:
        if canvas_id == "default": return False 
        
        if canvas_id in self.index["canvases"]:
            del self.index["canvases"][canvas_id]
            if self.index["active_id"] == canvas_id:
                self.index["active_id"] = "default"
            self._save_index(self.index)
            path = os.path.join(CANVASES_DIR, canvas_id)
            if os.path.exists(path):
                shutil.rmtree(path)
            return True
        return False

class ContextRegistry:
    """Manages the persistent hierarchy of Topics and Modules PER CANVAS."""
    def __init__(self, canvas_id: str):
        self.canvas_id = canvas_id
        self.file_path = os.path.join(CANVASES_DIR, canvas_id, "context.json")
        self._ensure_dir()
        self.colors = [
            "#0A84FF", # System Blue
            "#30D158", # System Green
            "#BF5AF2", # System Purple
            "#FF9F0A", # System Orange
            "#FF375F", # System Red
            "#FFD60A", # System Yellow
            "#64D2FF", # System Teal
            "#5E5CE6", # System Indigo
            "#FF453A", # System Pink
        ]
        self.context = self._load_context()

    def _ensure_dir(self):
        dirname = os.path.dirname(self.file_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    def _get_random_color(self):
        return random.choice(self.colors)

    def _load_context(self) -> Dict[str, Any]:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load context: {e}")
        
        # Check for legacy global context to migrate
        legacy_path = os.path.join(DATA_DIR, "nexus_context.json")
        if self.canvas_id == "default" and os.path.exists(legacy_path):
             logger.info("Migrating legacy context to default canvas...")
             try:
                 with open(legacy_path, 'r') as f:
                     data = json.load(f)
                 self._save_context(data)
                 return data
             except Exception as e:
                 logger.error(f"Context migration failed: {e}")

        # Default Structure
        default_context = {
            "topics": {
                "Uncategorized": {
                    "description": "Default container for new nodes",
                    "color": "#6B7280", # Gray
                    "modules": {
                        "General": "General notes and documents"
                    }
                }
            }
        }
        self._save_context(default_context)
        return default_context

    def _save_context(self, data: Dict[str, Any]):
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Context registry saved.")
        except Exception as e:
            logger.error(f"Failed to save context: {e}")

    def update_structure(self, topic: str, module_name: str = None, description: str = ""):
        """
        Updates or creates a Topic/Module.
        """
        if topic not in self.context["topics"]:
            self.context["topics"][topic] = {
                "description": description if not module_name else "Auto-generated topic",
                "color": self._get_random_color(),
                "modules": {}
            }
            logger.info(f"Created new Topic: {topic}")

        if module_name:
            if module_name not in self.context["topics"][topic]["modules"]:
                self.context["topics"][topic]["modules"][module_name] = description
                logger.info(f"Created new Module: {module_name} in {topic}")
        
        self._save_context(self.context)

    def get_structure_summary(self) -> str:
        """
        Returns a text summary for the AI Prompt.
        """
        lines = ["### CURRENT CONTEXT REGISTRY ###"]
        for topic, data in self.context["topics"].items():
            lines.append(f"- Topic: {topic} ({data.get('description', '')})")
            for mod, desc in data.get("modules", {}).items():
                lines.append(f"  - Module: {mod} ({desc})")
        return "\n".join(lines)

class Weaver:
    """
    The Weaver (Logic Engine)
    Manages Graph, Context, and Chat History for the Active Canvas.
    Enforces Strict Hierarchy: Topic > Module > Parent > Child.
    """
    def __init__(self):
        self.settings = SettingsRegistry()
        self.canvas_registry = CanvasRegistry()
        self.active_canvas_id = self.canvas_registry.get_active_id()
        
        self.hierarchy_levels = {
            "topic": 0, "module": 1, "parent": 2, "child": 3
        }
        
        # Initialize Graph and Context for active canvas
        self.load_active_canvas()

    def load_active_canvas(self):
        self.active_canvas_id = self.canvas_registry.get_active_id()
        self.graph_file = os.path.join(CANVASES_DIR, self.active_canvas_id, "graph.json")
        self.chat_file = os.path.join(CANVASES_DIR, self.active_canvas_id, "chat.json")
        
        # Ensure dir
        os.makedirs(os.path.dirname(self.graph_file), exist_ok=True)
        
        self.graph = self._load_graph_file()
        self.registry = ContextRegistry(self.active_canvas_id)
        self.chat_history = self._load_chat_history()
        
        logger.info(f"Weaver loaded canvas: {self.active_canvas_id}")

    def switch_canvas(self, canvas_id: str):
        if self.canvas_registry.set_active_id(canvas_id):
            self.load_active_canvas()
            return True
        return False

    def create_canvas(self, name: str):
        new_id = self.canvas_registry.create_canvas(name)
        self.switch_canvas(new_id)
        return new_id
        
    def delete_canvas(self, canvas_id: str):
        return self.canvas_registry.delete_canvas(canvas_id)

    def _load_graph_file(self):
        if os.path.exists(self.graph_file):
            try:
                with open(self.graph_file, 'r') as f:
                    data = json.load(f)
                return nx.node_link_graph(data)
            except Exception as e:
                logger.error(f"Failed to load graph: {e}")
                return nx.DiGraph()
        
        # Migration: Check root
        legacy_path = os.path.join(DATA_DIR, "nexus_graph.json")
        if self.active_canvas_id == "default" and os.path.exists(legacy_path):
             logger.info("Migrating legacy graph to default canvas...")
             try:
                 with open(legacy_path, 'r') as f:
                     data = json.load(f)
                 g = nx.node_link_graph(data)
                 data_export = nx.node_link_data(g)
                 with open(self.graph_file, 'w') as f:
                     json.dump(data_export, f, indent=2)
                 return g
             except Exception as e:
                 logger.error(f"Migration failed: {e}")

        return nx.DiGraph()

    def save_graph(self):
        """Persists the current graph state to disk."""
        data = nx.node_link_data(self.graph)
        try:
            with open(self.graph_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Graph saved to {self.graph_file}")
            # Update canvas last_modified timestamp
            if self.active_canvas_id in self.canvas_registry.index["canvases"]:
                self.canvas_registry.index["canvases"][self.active_canvas_id]["last_modified"] = datetime.now().isoformat()
                self.canvas_registry._save_index(self.canvas_registry.index)
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")
    
    def save_all(self) -> Dict[str, Any]:
        """
        Manually saves all canvas data: graph, context, chat history, and settings.
        Returns save status information.
        """
        save_status = {
            "timestamp": datetime.now().isoformat(),
            "canvas_id": self.active_canvas_id,
            "saved": [],
            "errors": []
        }
        
        try:
            # Save graph
            self.save_graph()
            save_status["saved"].append("graph")
        except Exception as e:
            save_status["errors"].append(f"graph: {str(e)}")
        
        try:
            # Save context
            self.registry._save_context(self.registry.context)
            save_status["saved"].append("context")
        except Exception as e:
            save_status["errors"].append(f"context: {str(e)}")
        
        try:
            # Save chat history (if it exists)
            if hasattr(self, 'chat_history'):
                self.save_chat_history(self.chat_history)
                save_status["saved"].append("chat_history")
        except Exception as e:
            save_status["errors"].append(f"chat_history: {str(e)}")
        
        try:
            # Save settings
            self.settings._save_settings(self.settings.settings)
            save_status["saved"].append("settings")
        except Exception as e:
            save_status["errors"].append(f"settings: {str(e)}")
        
        logger.info(f"Manual save completed: {save_status}")
        return save_status

    def _load_chat_history(self) -> List[Dict]:
        """Loads chat history from disk."""
        if os.path.exists(self.chat_file):
            try:
                with open(self.chat_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load chat history: {e}")
        return []

    def save_chat_history(self, history: List[Dict]):
        """Saves chat history to disk."""
        try:
            with open(self.chat_file, 'w') as f:
                json.dump(history, f, indent=2)
            # logger.info("Chat history saved.") 
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")

    def get_node_summaries(self, exclude_id: str = None) -> List[Dict[str, Any]]:
        """
        Returns a lightweight list of nodes for LLM analysis (ID, Title, Summary, Tags).
        Used for auto-linking context.
        """
        summaries = []
        for node_id, data in self.graph.nodes(data=True):
            if exclude_id and node_id == exclude_id:
                continue
            
            summaries.append({
                "id": node_id,
                "title": data.get("title", node_id),
                "summary": data.get("summary", ""),
                "tags": data.get("tags", []),
                "module": data.get("module", "General"),
                "main_topic": data.get("main_topic", "Uncategorized"),
                "node_type": data.get("node_type", "child") # Default to child
            })
        return summaries

    def add_document_node(self, filename: str, content: str, meta: Dict[str, Any] = None):
        """
        Ingests a document as a Node.
        """
        node_id = filename 
        
        base_name = os.path.splitext(filename)[0]
        if "-" in base_name:
             node_id = base_name.upper()

        attributes = {
            "type": "document",
            "content": content,
            "created_at": datetime.now().isoformat(),
            "module": "General",
            "main_topic": "Uncategorized",
            "node_type": "child" # Default type
        }
        if meta:
            attributes.update(meta)
            
        self.graph.add_node(node_id, **attributes)
        self.save_graph()
        return node_id

    def add_edge(self, source: str, target: str, justification: str, confidence: float = 1.0):
        """
        Adds a justified edge between nodes.
        Enforces strict hierarchy: Source must be LOWER level than Target (pointing upwards).
        e.g. Child -> Parent, Parent -> Module, Module -> Topic.
        """
        if self.graph.has_node(source) and self.graph.has_node(target):
            # Strict Hierarchy Check
            source_type = self.graph.nodes[source].get("node_type", "child")
            target_type = self.graph.nodes[target].get("node_type", "child")
            
            source_level = self.hierarchy_levels.get(source_type, 3)
            target_level = self.hierarchy_levels.get(target_type, 3)
            
            # Allow pointing to same level (siblings) or upper level
            if source_level < target_level:
                 logger.warning(f"Hierarchy Violation: {source} ({source_type}) cannot point down to {target} ({target_type})")
                 # We can either block it or just log it. 
                 # User asked: "it can only be pointed to the upper level"
                 # Interpreting strictly: Child -> Parent is allowed. Parent -> Child is BLOCKED.
                 return False

            self.graph.add_edge(source, target, justification=justification, confidence=confidence)
            self.save_graph()
            return True
        return False

    def delete_node(self, node_id: str) -> bool:
        """Deletes a node and its edges."""
        if self.graph.has_node(node_id):
            self.graph.remove_node(node_id)
            self.save_graph()
            return True
        return False

    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """Updates node attributes."""
        if self.graph.has_node(node_id):
            for key, value in updates.items():
                self.graph.nodes[node_id][key] = value
            self.save_graph()
            return True
        return False
    
    def update_node_positions(self, positions: Dict[str, Dict[str, float]]) -> bool:
        """
        Updates positions for multiple nodes at once.
        positions: { node_id: { x: float, y: float }, ... }
        """
        updated = False
        for node_id, pos in positions.items():
            if self.graph.has_node(node_id):
                self.graph.nodes[node_id]["position"] = pos
                updated = True
        if updated:
            self.save_graph()
        return updated

    def delete_edge(self, source: str, target: str) -> bool:
        """Deletes an edge."""
        if self.graph.has_edge(source, target):
            self.graph.remove_edge(source, target)
            self.save_graph()
            return True
        return False

    def update_edge(self, source: str, target: str, updates: Dict[str, Any]) -> bool:
        """Updates edge attributes."""
        if self.graph.has_edge(source, target):
            nx.set_edge_attributes(self.graph, {(source, target): updates})
            self.save_graph()
            return True
        return False

    def get_subgraph(self, selected_node_ids: List[str], depth: int) -> Dict[str, Any]:
        """
        Calculates the subgraph based on depth setting (F0, F1, F2).
        REQ-LOG-01: Graph Topology Traversal
        """
        if not selected_node_ids:
            return {"nodes": [], "edges": []}

        valid_seeds = [n for n in selected_node_ids if self.graph.has_node(n)]
        
        context_nodes: Set[str] = set(valid_seeds)

        if depth == 0:
            pass
        elif depth == 1:
            for node in valid_seeds:
                neighbors = set(self.graph.neighbors(node)) | set(self.graph.predecessors(node))
                context_nodes.update(neighbors)
        elif depth == 2:
            f1_nodes = set(valid_seeds)
            for node in valid_seeds:
                neighbors = set(self.graph.neighbors(node)) | set(self.graph.predecessors(node))
                f1_nodes.update(neighbors)
            
            context_nodes.update(f1_nodes)
            for node in list(f1_nodes):
                if self.graph.has_node(node):
                    neighbors = set(self.graph.neighbors(node)) | set(self.graph.predecessors(node))
                    context_nodes.update(neighbors)
        
        subgraph = self.graph.subgraph(context_nodes)
        
        return {
            "nodes": [{"id": n, **subgraph.nodes[n]} for n in subgraph.nodes()],
            "edges": [{"source": u, "target": v, **subgraph.edges[u, v]} for u, v in subgraph.edges()]
        }
