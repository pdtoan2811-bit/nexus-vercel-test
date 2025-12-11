import os
import json
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .graph_logic import Weaver

logger = logging.getLogger(__name__)

if not PIL_AVAILABLE:
    logger.warning("PIL/Pillow not available. Image analysis will be limited.")

class ChatBridge:
    """
    The Chat Bridge
    Handles context hydration, blast radius calculation, and LLM interaction.
    """
    def __init__(self, weaver: Weaver):
        self.weaver = weaver
        # Try multiple ways to get the API key
        self.api_key = (
            os.getenv("GEMINI_API_KEY") or 
            os.environ.get("GEMINI_API_KEY", "").strip()
        )
        self.model = None
        
        logger.info(f"GEMINI_API_KEY present: {bool(self.api_key)}")
        logger.info(f"GEMINI_API_KEY length: {len(self.api_key) if self.api_key else 0}")
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Using gemini-2.5-flash as requested
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                logger.info("ChatBridge initialized successfully with model: gemini-2.5-flash")
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}", exc_info=True)
                self.model = None
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables. LLM features will be limited.")
            logger.warning("Set GEMINI_API_KEY in Vercel project settings → Environment Variables")
            # Log available env vars for debugging
            gemini_vars = [k for k in os.environ.keys() if "GEMINI" in k.upper() or "API" in k.upper()]
            if gemini_vars:
                logger.info(f"Found related env vars: {', '.join(gemini_vars)}")
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
        Consults the ContextRegistry for two-way interaction.
        """
        if not self.model:
            return {
                "title": "Unknown Title", 
                "summary": "LLM Unavailable", 
                "tags": [],
                "module": "General",
                "main_topic": "Uncategorized"
            }

        # Get Registry Context
        registry_summary = self.weaver.registry.get_structure_summary()

        prompt = f"""
        You are Nexus, an AI Knowledge Weaver. Analyze the following document and extract structured metadata.
        
        You have access to the Current Context Registry (Topics & Modules). 
        Your goal is to fit this content into the existing structure OR propose new structure if it genuinely doesn't fit.

        {registry_summary}

        Input Text:
        {content[:4000]}... (truncated)

        Requirements:
        1. Title: Concise and descriptive.
        2. Summary: One sentence explaining the core value/issue.
        3. Module: Must be an existing Module from Registry, OR a proposed new one.
        4. Main Topic: Must be an existing Topic from Registry, OR a proposed new one.
        5. Tags: List of specific keywords.

        Output JSON:
        {{
            "title": "String",
            "summary": "String",
            "module": "String (Existing or New)",
            "main_topic": "String (Existing or New)",
            "tags": ["String"],
            "proposed_new_topic": {{ "name": "New Topic Name", "description": "Why needed" }} (Optional, null if using existing),
            "proposed_new_module": {{ "topic": "Topic Name", "name": "New Module Name", "description": "Why needed" }} (Optional, null if using existing)
        }}
        """
        
        if not self.model:
            logger.warning("Gemini model not available. Returning default metadata.")
            return {
                "title": "Untitled Document",
                "summary": "Content ingested without AI analysis (GEMINI_API_KEY not configured)",
                "tags": [],
                "module": "General",
                "main_topic": "Uncategorized"
            }
        
        try:
            logger.info("Sending metadata extraction request to Gemini...")
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(text)
            logger.info("Metadata extraction successful.")
            return data
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}", exc_info=True)
            # Return fallback metadata instead of empty dict
            return {
                "title": "Untitled Document",
                "summary": f"Content ingested (AI analysis failed: {str(e)})",
                "tags": [],
                "module": "General",
                "main_topic": "Uncategorized"
            }

    async def analyze_image(self, image_bytes: bytes, image_format: str = "PNG") -> Dict[str, Any]:
        """
        Analyzes an image using Gemini Vision API to extract content and metadata.
        Treats the image as an article/document.
        Uses Gemini Vision API (gemini-2.5-flash) for OCR and content analysis.
        """
        if not self.model:
            return {
                "title": "Image Analysis Unavailable",
                "summary": "LLM Unavailable",
                "content": "Image analysis requires LLM access.",
                "tags": [],
                "module": "General",
                "main_topic": "Uncategorized"
            }

        try:
            # Try to import PIL at runtime if not available at import time
            try:
                from PIL import Image
                import io
                pil_available = True
            except ImportError:
                pil_available = False
                logger.error("PIL/Pillow import failed. Attempting to install...")
                raise ImportError("PIL/Pillow is required for image analysis. Please install it with: pip install Pillow")
            
            if not pil_available:
                raise ImportError("PIL/Pillow is required for image analysis")
            
            # Determine MIME type from image bytes or format
            # Try to detect format from bytes
            mime_type = "image/png"  # default
            if image_bytes.startswith(b'\xff\xd8\xff'):
                mime_type = "image/jpeg"
            elif image_bytes.startswith(b'\x89PNG'):
                mime_type = "image/png"
            elif image_bytes.startswith(b'GIF'):
                mime_type = "image/gif"
            elif image_bytes.startswith(b'WEBP', 8):
                mime_type = "image/webp"
            
            # Convert bytes to PIL Image to validate and normalize
            pil_image = Image.open(io.BytesIO(image_bytes))
            logger.info(f"Image loaded successfully. Size: {pil_image.size}, Format: {pil_image.format}, Mode: {pil_image.mode}")
            
            # Convert to RGB and save as bytes in PNG format (universally supported by Gemini)
            if pil_image.mode != 'RGB':
                if pil_image.mode in ('RGBA', 'LA'):
                    # Create white background for transparency
                    rgb_image = Image.new('RGB', pil_image.size, (255, 255, 255))
                    if pil_image.mode == 'RGBA':
                        rgb_image.paste(pil_image, mask=pil_image.split()[3])  # Use alpha channel as mask
                    else:
                        rgb_image.paste(pil_image, mask=pil_image.split()[1])  # Use alpha channel as mask
                    pil_image = rgb_image
                else:
                    # Convert other modes to RGB
                    pil_image = pil_image.convert('RGB')
            
            # Save as PNG bytes for Gemini
            image_buffer = io.BytesIO()
            pil_image.save(image_buffer, format='PNG')
            image_bytes_final = image_buffer.getvalue()
            mime_type = "image/png"  # Always use PNG for Gemini
            
            logger.info(f"Image prepared for Gemini. Size: {len(image_bytes_final)} bytes, MIME: {mime_type}")
            
            # Get Registry Context
            registry_summary = self.weaver.registry.get_structure_summary()
            
            prompt = f"""
            You are Nexus, an AI Knowledge Weaver. Analyze this image as if it were an article or document.
            
            You have access to the Current Context Registry (Topics & Modules).
            Your goal is to extract all meaningful content from this image and fit it into the existing structure OR propose new structure if needed.
            
            {registry_summary}
            
            Instructions:
            1. Extract ALL text visible in the image (OCR).
            2. Analyze the visual content (diagrams, charts, screenshots, photos, etc.).
            3. Understand the context and meaning of the content.
            4. Extract structured metadata:
               - Title: What is this image/article about?
               - Summary: One sentence explaining the core value/issue.
               - Content: Full text content extracted from the image, formatted as a readable article.
               - Module: Must be an existing Module from Registry, OR a proposed new one.
               - Main Topic: Must be an existing Topic from Registry, OR a proposed new one.
               - Tags: List of specific keywords from the content.
            
            Output JSON:
            {{
                "title": "String (descriptive title of the image content)",
                "summary": "String (one sentence summary)",
                "content": "String (full extracted text content, formatted as article)",
                "module": "String (Existing or New)",
                "main_topic": "String (Existing or New)",
                "tags": ["String"],
                "proposed_new_topic": {{ "name": "New Topic Name", "description": "Why needed" }} (Optional, null if using existing),
                "proposed_new_module": {{ "topic": "Topic Name", "name": "New Module Name", "description": "Why needed" }} (Optional, null if using existing)
            }}
            """
            
            logger.info("Sending image analysis request to Gemini Vision API (gemini-2.5-flash)...")
            # Use Gemini Vision API - pass image as dict with mime_type and data
            # This is the format that Gemini Vision API expects according to the error message
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes_final
            }
            
            # Use Gemini Vision API - pass image part and prompt as list
            # The library will handle the image analysis using Gemini's multimodal capabilities
            response = await self.model.generate_content_async([image_part, prompt])
            text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(text)
            logger.info(f"Image analysis successful. Extracted title: {data.get('title', 'Unknown')}")
            return data
        except Exception as e:
            logger.error(f"Image analysis failed: {e}", exc_info=True)
            return {
                "title": "Image Analysis Failed",
                "summary": f"Failed to analyze image: {str(e)}",
                "content": "Image analysis encountered an error.",
                "tags": [],
                "module": "General",
                "main_topic": "Uncategorized"
            }

    async def detect_relationships(self, new_node: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes a new node against existing nodes to find logical connections.
        Respects SettingsRegistry for automation control.
        """
        # Check Settings
        settings = self.weaver.settings.get("auto_linking")
        if not settings or not settings.get("enabled", True):
            logger.info("Auto-linking is disabled in settings.")
            return []

        limit = settings.get("max_connections", 3)
        threshold = settings.get("threshold", 0.6)

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
        3. Limit to top {limit} strongest connections.
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

        if not self.model:
            logger.warning("Gemini model not available. Skipping relationship detection.")
            return []
        
        try:
            logger.info(f"Detecting relationships for {new_node.get('id')} against {len(candidates)} candidates...")
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            links = json.loads(text)
            
            # Filter by threshold
            filtered_links = [l for l in links if l.get("confidence", 0) >= threshold]
            
            logger.info(f"AI suggested {len(links)} links. {len(filtered_links)} passed threshold {threshold}.")
            return filtered_links
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
            "The LLM output MUST follow a strict citation format: [NODE-ID] whenever you reference a specific piece of information.\n"
            "FORMATTING RULES:\n"
            "1. Use Markdown for all responses.\n"
            "2. Use H1 (#) for main titles, H2 (##) for sections.\n"
            "3. Use **Bold** for key concepts.\n"
            "4. Use tables for comparisons or structured data.\n"
            "5. Use > Blockquotes for key insights.\n"
            "6. Use lists and bullet points for readability.\n\n"
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
    
    async def rewrite_node_context_aware(self, node_id: str) -> Dict[str, Any]:
        """
        Rewrites a node's summary/description AND content based on its neighbors (connected nodes).
        """
        if not self.model:
            return {"error": "LLM Unavailable"}
        
        # 1. Get Node Data
        node = self.weaver.graph.nodes[node_id]
        if not node:
            return {"error": "Node not found"}
            
        # 2. Get Neighbors (Inbound and Outbound)
        # We need the full context: what points to it, what it points to.
        subgraph = self.weaver.get_subgraph([node_id], depth=1)
        
        # 3. Prepare Context
        neighbor_context = []
        for n in subgraph["nodes"]:
            if n["id"] == node_id: continue
            
            # Find edge justification
            rel = "Related"
            for e in subgraph["edges"]:
                if e["source"] == n["id"] and e["target"] == node_id:
                    rel = f"Influenced by {n['id']} ({e.get('justification', '')})"
                elif e["source"] == node_id and e["target"] == n["id"]:
                    rel = f"Influences {n['id']} ({e.get('justification', '')})"
            
            neighbor_context.append(f"- [{n['id']}] ({n.get('type')}, {n.get('main_topic')}): {n.get('summary')} | Relation: {rel}")
            
        neighbor_text = "\n".join(neighbor_context)
        
        # Get Settings
        content_settings = self.weaver.settings.get("content_generation", {})
        tone = content_settings.get("tone", "Technical")
        detail = content_settings.get("detail_level", "High")

        prompt = f"""
        You are Nexus. Rewrite the content and summary of the following node to better reflect its role within the graph.
        
        Target Node:
        ID: {node_id}
        Current Summary: {node.get('summary', '')}
        Topic: {node.get('main_topic', 'Uncategorized')}
        Module: {node.get('module', 'General')}
        Original Content: {node.get('content', '')[:2000]}...
        
        Connected Context (Neighbors):
        {neighbor_text}
        
        Instructions:
        1. Synthesize the connected context.
        2. Rewrite the "summary" to explicitly mention how this node relates to its neighbors.
        3. Rewrite the "content" to integrate the context naturally, while preserving the original core information.
        4. Tone: {tone}. Detail Level: {detail}.
        5. If the context suggests a better "main_topic" or "module", suggest it too.
        
        Output JSON:
        {{
            "summary": "New context-aware summary...",
            "content": "New context-enriched content...",
            "suggested_topic": "Current or New Topic",
            "suggested_module": "Current or New Module"
        }}
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(text)
            return result
        except Exception as e:
            logger.error(f"Rewrite failed: {e}", exc_info=True)
            return {"error": str(e)}

    async def generate_edge_justification(self, source_id: str, target_id: str, user_hint: Optional[str] = None) -> str:
        """
        Generates a justification for a link between two nodes.
        Used for manual connection assistance.
        """
        if not self.model:
            return "Linked manually (LLM Unavailable)"

        source = self.weaver.graph.nodes.get(source_id)
        target = self.weaver.graph.nodes.get(target_id)
        
        if not source or not target:
            return "Linked manually (Node not found)"

        prompt = f"""
        You are Nexus. A user is manually linking two nodes. Generate a concise justification for this connection.
        
        Source Node:
        Title: {source.get('title', source_id)}
        Summary: {source.get('summary', '')}
        Content Snippet: {source.get('content', '')[:500]}
        
        Target Node:
        Title: {target.get('title', target_id)}
        Summary: {target.get('summary', '')}
        Content Snippet: {target.get('content', '')[:500]}
        
        User Hint (Optional): {user_hint if user_hint else "None"}
        
        Instructions:
        1. Determine the logical relationship (e.g., "Supports", "Contradicts", "Elaborates on", "Sub-task of").
        2. If a User Hint is provided, use it as the core meaning but refine the phrasing.
        3. Output ONLY the justification string (max 15 words).
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Edge justification generation failed: {e}")
            return user_hint if user_hint else "Linked manually"

    async def generate_mece_breakdown(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Breaks down a node into MECE sub-components.
        """
        if not self.model:
            return []
            
        node = self.weaver.graph.nodes.get(node_id)
        if not node:
            return []
            
        # Get Settings
        exp_settings = self.weaver.settings.get("expansion", {})
        limit = exp_settings.get("max_subnodes", 5)
        
        content_settings = self.weaver.settings.get("content_generation", {})
        tone = content_settings.get("tone", "Technical")

        prompt = f"""
        You are Nexus. Apply the MECE (Mutually Exclusive, Collectively Exhaustive) principle to break down the following node into sub-components.
        
        Parent Node:
        Title: {node.get('title', node_id)}
        Type: {node.get('node_type', 'unknown')}
        Topic: {node.get('main_topic', 'Uncategorized')}
        Content: {node.get('content', '')[:1000]}...
        
        Instructions:
        1. Determine the optimal number of sub-components to cover the parent concept completely without overlap.
        2. Create AT MOST {limit} sub-components.
        3. Use a {tone} tone for content generation.
        4. If the parent is a 'topic', create 'module' level nodes.
        5. If the parent is a 'module', create 'parent' level nodes.
        6. If the parent is a 'parent', create 'child' level nodes.
        7. For each new node, generate rich content and metadata.
        
        Output JSON List:
        [
            {{
                "title": "Sub-component Title",
                "summary": "Concise summary",
                "content": "Detailed content block...",
                "tags": ["tag1", "tag2"],
                "node_type": "target_level (module/parent/child)",
                "justification": "Why this is a sub-component of the parent"
            }}
        ]
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"MECE breakdown failed: {e}")
            return []

    async def generate_abstraction(self, node_id: str) -> Dict[str, Any]:
        """
        Abstracts a node into a higher-level concept.
        """
        if not self.model:
            return {}
            
        node = self.weaver.graph.nodes.get(node_id)
        if not node:
            return {}
            
        # Get Settings
        content_settings = self.weaver.settings.get("content_generation", {})
        tone = content_settings.get("tone", "Technical")

        prompt = f"""
        You are Nexus. Abstract the following node into a higher-level parent concept.
        
        Child Node:
        Title: {node.get('title', node_id)}
        Type: {node.get('node_type', 'unknown')}
        Content: {node.get('content', '')[:1000]}...
        
        Instructions:
        1. Identify the broader category or system this node belongs to.
        2. Use a {tone} tone.
        3. If the child is a 'module', create a 'topic'.
        4. If the child is a 'parent', create a 'module'.
        5. If the child is a 'child', create a 'parent'.
        
        Output JSON:
        {{
            "title": "Parent Concept Title",
            "summary": "High-level summary",
            "content": "Description of the broader system...",
            "node_type": "target_level (topic/module/parent)",
            "justification": "Why the child belongs to this parent"
        }}
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Abstraction failed: {e}")
            return {}
