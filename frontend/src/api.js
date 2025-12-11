import axios from 'axios';

// Use relative URL for Vercel deployment, fallback to localhost for development
const API_BASE_URL = import.meta.env.DEV 
  ? 'http://localhost:8000/api/v2'
  : '/api/v2';

// --- Canvas Management ---
export const getCanvases = async () => {
    const response = await axios.get(`${API_BASE_URL}/canvases`);
    return response.data;
};

export const createCanvas = async (name) => {
    const response = await axios.post(`${API_BASE_URL}/canvases`, { name });
    return response.data;
};

export const activateCanvas = async (canvasId) => {
    const response = await axios.post(`${API_BASE_URL}/canvases/${canvasId}/activate`);
    return response.data;
};

export const deleteCanvas = async (canvasId) => {
    const response = await axios.delete(`${API_BASE_URL}/canvases/${canvasId}`);
    return response.data;
};
// -------------------------

export const getGraph = async () => {
    const response = await axios.get(`${API_BASE_URL}/graph`);
    return response.data;
};

export const getContext = async () => {
    const response = await axios.get(`${API_BASE_URL}/context`);
    return response.data;
};

export const getSettings = async () => {
    const response = await axios.get(`${API_BASE_URL}/settings`);
    return response.data;
};

export const updateSettings = async (updates) => {
    const response = await axios.post(`${API_BASE_URL}/settings`, updates);
    return response.data;
};

export const ingestText = async (content, module = "General", mainTopic = "Uncategorized") => {
    const response = await axios.post(`${API_BASE_URL}/ingest/text`, { 
        content, 
        module,
        main_topic: mainTopic 
    });
    return response.data;
};

export const uploadDocument = async (file, module = "General", mainTopic = "Uncategorized") => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('module', module);
    formData.append('main_topic', mainTopic);
    
    const response = await axios.post(`${API_BASE_URL}/ingest/upload`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const uploadImage = async (file, module = "General", mainTopic = "Uncategorized") => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('module', module);
    formData.append('main_topic', mainTopic);
    
    const response = await axios.post(`${API_BASE_URL}/ingest/image`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const createEdge = async (source, target, justification) => {
    const response = await axios.post(`${API_BASE_URL}/ingest/edge`, {
        source,
        target,
        justification
    });
    return response.data;
};

export const updateEdge = async (source, target, updates) => {
    const response = await axios.put(`${API_BASE_URL}/edges`, updates, {
        params: { source, target }
    });
    return response.data;
};

export const deleteEdge = async (source, target) => {
    const response = await axios.delete(`${API_BASE_URL}/edges`, {
        params: { source, target }
    });
    return response.data;
};

export const suggestEdgeJustification = async (source, target, userHint = null) => {
    const response = await axios.post(`${API_BASE_URL}/edges/suggest`, {
        source,
        target,
        user_hint: userHint
    });
    return response.data;
};

export const analyzeNode = async (nodeId) => {
    const response = await axios.post(`${API_BASE_URL}/nodes/${nodeId}/analyze`);
    return response.data;
};

export const rewriteNode = async (nodeId) => {
    const response = await axios.post(`${API_BASE_URL}/nodes/${nodeId}/rewrite`);
    return response.data;
};

export const expandNode = async (nodeId, direction) => {
    const response = await axios.post(`${API_BASE_URL}/nodes/${nodeId}/expand`, {
        direction
    });
    return response.data;
};

export const deleteNode = async (nodeId) => {
    const response = await axios.delete(`${API_BASE_URL}/nodes/${nodeId}`);
    return response.data;
};

export const updateNode = async (nodeId, updates, thumbnailFile = null) => {
    const formData = new FormData();
    
    // Always use FormData to support both file and regular updates
    if (thumbnailFile) {
        formData.append('thumbnail', thumbnailFile);
    }
    
    // Append all other updates
    if (updates) {
        Object.keys(updates).forEach(key => {
            if (key !== 'thumbnail' && key !== 'thumbnailFile' && key !== 'thumbnailPreview') {
                const value = updates[key];
                if (value !== null && value !== undefined) {
                    // Handle arrays (like tags)
                    if (Array.isArray(value)) {
                        formData.append(key, value.join(','));
                    } else {
                        formData.append(key, value);
                    }
                }
            }
        });
    }
    
    const response = await axios.put(`${API_BASE_URL}/nodes/${nodeId}`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const calculateContext = async (selectedNodes, depthMode) => {
    const response = await axios.post(`${API_BASE_URL}/chat/context`, {
        selected_nodes: selectedNodes,
        depth_mode: depthMode
    });
    return response.data;
};

export const sendMessage = async (sessionId, userPrompt) => {
    const response = await axios.post(`${API_BASE_URL}/chat/message`, {
        session_id: sessionId,
        user_prompt: userPrompt
    });
    return response.data;
};

export const manualSave = async () => {
    const response = await axios.post(`${API_BASE_URL}/save`);
    return response.data;
};

export const exportCanvas = async () => {
    const response = await axios.get(`${API_BASE_URL}/export`, {
        responseType: 'blob'
    });
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    
    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'nexus_backup.zip';
    if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (filenameMatch) {
            filename = filenameMatch[1];
        }
    }
    
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    
    return { status: 'success', message: 'Export downloaded' };
};

export const updateNodePositions = async (positions) => {
    const response = await axios.post(`${API_BASE_URL}/nodes/positions`, positions);
    return response.data;
};
