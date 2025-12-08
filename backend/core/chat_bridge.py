import os
import json
import logging
from typing import List, Dict, Any
import google.generativeai as genai
from .graph_logic import Weaver

logger = logging.getLogger(__name__)

class ChatBridge:
    """
    The Chat Bridge
    Handles context hydration, blast radius calculation, and LLM interaction.
    """
    def __init__(self, weaver: Weaver):
        self.weaver = weaver
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Using gemini-2.5-flash as requested
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                logger.info("ChatBridge initialized successfully with model: gemini-2.5-flash")
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")
                self.model = None
        else:
            logger.warning("GEMINI_API_KEY not found environment variable. LLM features will be mocked.")
            self.model = None

    def calculate_context(self, selected_nodes: List[str], depth: int) -> Dict[str, Any]:
        """
        Calculates the blast radius and prepares context for the UI and LLM.
        """
        subgraph = self.weaver.get_subgraph(selected_nodes, depth)
        
        # Calculate Dominant Module (REQ-LOG-03)
        module_counts = {}
        total_nodes = len(subgraph["nodes"])
        
        for node in subgraph["nodes"]:
            mod = node.get("module", "Unknown")
            module_counts[mod] = module_counts.get(mod, 0) + 1
            
        dominant_module = "Cross-Module"
        if total_nodes > 0:
            for mod, count in module_counts.items():
                if count / total_nodes > 0.5:
                    dominant_module = mod
                    break
                    
        return {
            "context_nodes": subgraph["nodes"],
            "context_edges": subgraph["edges"],
            "dominant_module": dominant_module,
            "stats": {
                "node_count": total_nodes,
                "edge_count": len(subgraph["edges"])
            }
        }

    def _hydrate_context(self, context_data: Dict[str, Any]) -> str:
        """
        Converts graph data into a text block for the System Prompt.
        REQ-LOG-02 & REQ-CHAT-01
        """
        lines = []
        lines.append("### CONTEXT NODES ###")
        for node in context_data["context_nodes"]:
            # Strip unnecessary keys (REQ-NFR-03 - simplistic implementation)
            content = node.get("content", "")
            lines.append(f"ID: [{node['id']}] | Type: {node['type']} | Content: {content}")
            
        lines.append("\n### JUSTIFIED EDGES (RELATIONSHIPS) ###")
        for edge in context_data["context_edges"]:
            lines.append(f"From [{edge['source']}] -> To [{edge['target']}] | Justification: {edge.get('justification', 'Linked')}")
            
        return "\n".join(lines)

    async def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Uses Gemini to extract title, summary, module, and topics.
        """
        if not self.model:
            return {
                "title": "Unknown Title", 
                "summary": "LLM Unavailable", 
                "tags": [],
                "suggested_module": "General",
                "topic_cluster": "Unclassified"
            }

        prompt = f"""
        You are Nexus, an AI Knowledge Weaver. Analyze the following document and extract structured metadata.
        
        Input Text:
        {content[:4000]}... (truncated)

        Requirements:
        1. Title: Concise and descriptive.
        2. Summary: One sentence explaining the core value/issue.
        3. Module: Suggest a functional module name (e.g., "Payments", "Auth", "Logistics", "UI").
        4. Topic Cluster: A high-level grouping (e.g., "Error Handling", "Performance", "Feature Spec").
        5. Tags: List of specific keywords.

        Output JSON:
        {{
            "title": "String",
            "summary": "String",
            "suggested_module": "String",
            "topic_cluster": "String",
            "tags": ["String"]
        }}
        """
        
        try:
            logger.info("Sending metadata extraction request to Gemini...")
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(text)
            logger.info("Metadata extraction successful.")
            return data
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}", exc_info=True)
            return {}

    async def detect_relationships(self, new_node: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes a new node against existing nodes to find logical connections.
        """
        if not self.model or not candidates:
            return []

        # Prepare Candidate List as Text
        candidates_text = json.dumps([{
            "id": c["id"], 
            "title": c.get("title", ""), 
            "summary": c.get("summary", ""),
            "tags": c.get("tags", [])
        } for c in candidates], indent=2)

        prompt = f"""
        You are Nexus. A new document node has been added to the graph. 
        Your task is to identify logical connections (edges) between this new node and existing nodes.

        New Node:
        ID: {new_node.get('id')}
        Title: {new_node.get('title')}
        Summary: {new_node.get('summary')}
        Tags: {new_node.get('tags')}
        Module: {new_node.get('module')}

        Existing Nodes (Candidates):
        {candidates_text}

        Instructions:
        1. Analyze semantic relationships (e.g., shared topics, dependency, conflict, elaboration).
        2. Create edges ONLY if there is a strong justification.
        3. Limit to top 3 strongest connections.
        4. "confidence" should be between 0.0 and 1.0.

        Output JSON List:
        [
            {{
                "target_id": "Existing Node ID",
                "justification": "Why they are linked (max 10 words)",
                "confidence": 0.85
            }}
        ]
        If no connections, return [].
        """

        try:
            logger.info(f"Detecting relationships for {new_node.get('id')} against {len(candidates)} candidates...")
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            links = json.loads(text)
            logger.info(f"AI suggested {len(links)} links.")
            return links
        except Exception as e:
            logger.error(f"Relationship detection failed: {e}", exc_info=True)
            return []

    async def generate_response(self, session_history: List[Dict], context_data: Dict[str, Any], user_prompt: str) -> str:
        """
        Generates a response using Gemini 1.5 Flash.
        """
        hydrated_context = self._hydrate_context(context_data)
        
        system_instruction = (
            "You are Nexus, an evidence-based reasoning engine.\n"
            "You must only answer based on the provided Context Nodes. Do not use outside knowledge.\n"
            "The LLM output MUST follow a strict citation format: [NODE-ID] whenever you reference a specific piece of information.\n\n"
            f"{hydrated_context}"
        )
        
        if not self.model:
            return "Simulated Response: [TICKET-101] and [SRS-PAY-02] suggest a timing issue. (LLM Key Missing)"

        # Construct chat history for Gemini
        # Gemini history format: [{'role': 'user', 'parts': ['...']}, {'role': 'model', 'parts': ['...']}]
        gemini_history = []
        for msg in session_history:
            role = 'user' if msg['role'] == 'user' else 'model'
            gemini_history.append({'role': role, 'parts': [msg['content']]})
            
        # Create chat session
        chat = self.model.start_chat(history=gemini_history)
        
        # Add system instruction as part of the prompt or context since 1.5 Flash API varies slightly in python lib versions
        # Ideally system instruction is passed to GenerativeModel creation or handled via prompt engineering in the first message.
        # For this prototype, we'll prepend context to the latest prompt to ensure it's fresh.
        
        full_prompt = f"{system_instruction}\n\nUser Query: {user_prompt}"
        
        try:
            response = await chat.send_message_async(full_prompt)
            return response.text
        except Exception as e:
            return f"Error communicating with Gemini: {str(e)}"

    async def analyze_video(self, video_url: str) -> str:
        """
        Analyzes a YouTube video URL and extracts technical details.
        """
        if not self.model:
            return "LLM Unavailable"

        prompt = "Summarize this video and extract the key technical details."
        
        try:
            logger.info(f"Analyzing video: {video_url}")
            # Method 1: Direct YouTube URL (using file_uri)
            # This follows the user's specific request pattern but fixed for structure
            part = {
                "file_data": {
                    "mime_type": "video/mp4",
                    "file_uri": video_url
                }
            }
            response = await self.model.generate_content_async([prompt, part])
            logger.info("Video analysis successful.")
            return response.text
        except Exception as e:
            logger.error(f"Video analysis failed: {e}", exc_info=True)
            return f"Failed to analyze video. Ensure it is public. Error: {str(e)}"

