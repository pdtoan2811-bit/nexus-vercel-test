import axios from 'axios';

const API_BASE = '/api/v2';

export const getGraph = async () => {
  const response = await axios.get(`${API_BASE}/graph`);
  return response.data;
};

export const uploadDocument = async (file, moduleName, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('module', moduleName);
  
  // Remove explicit Content-Type header to let browser set boundary
  const response = await axios.post(`${API_BASE}/ingest/upload`, formData, {
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percentCompleted);
      }
    }
  });
  return response.data;
};

export const ingestText = async (content, moduleName) => {
  const response = await axios.post(`${API_BASE}/ingest/text`, {
    content,
    module: moduleName
  });
  return response.data;
};

export const createEdge = async (source, target, justification) => {
  const response = await axios.post(`${API_BASE}/ingest/edge`, {
    source,
    target,
    justification
  });
  return response.data;
};

export const analyzeNode = async (nodeId) => {
  const safeId = encodeURIComponent(nodeId);
  const response = await axios.post(`${API_BASE}/nodes/${safeId}/analyze`);
  return response.data;
};

export const deleteNode = async (nodeId) => {
    const safeId = encodeURIComponent(nodeId);
    const response = await axios.delete(`${API_BASE}/nodes/${safeId}`);
    return response.data;
};

export const updateNode = async (nodeId, updates) => {
    const safeId = encodeURIComponent(nodeId);
    const response = await axios.put(`${API_BASE}/nodes/${safeId}`, updates);
    return response.data;
};

export const deleteEdge = async (source, target) => {
    const response = await axios.delete(`${API_BASE}/edges`, {
        params: { source, target }
    });
    return response.data;
};

export const calculateContext = async (selectedNodes, depthMode) => {
  const response = await axios.post(`${API_BASE}/chat/context`, {
    selected_nodes: selectedNodes,
    depth_mode: depthMode
  });
  return response.data;
};

export const sendMessage = async (sessionId, userPrompt) => {
  const response = await axios.post(`${API_BASE}/chat/message`, {
    session_id: sessionId,
    user_prompt: userPrompt
  });
  return response.data;
};
