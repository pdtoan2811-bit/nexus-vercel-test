import React, { useState, useEffect } from 'react';
import { X, Calendar, Tag, FileText, Sparkles, BrainCircuit, Edit2, Trash2, Save, RotateCcw, PlayCircle, ExternalLink } from 'lucide-react';
import { analyzeNode, updateNode, deleteNode } from '../api';

const NodeInspector = ({ node, onClose, onRefresh }) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    if (node) {
        setEditForm({
            title: node.title || node.label || node.id,
            summary: node.summary || '',
            module: node.module || 'General',
            tags: (node.tags || []).join(', '),
            content: node.content || ''
        });
        setIsEditing(false);
    }
  }, [node]);

  if (!node) return null;

  const isVideo = !!node.video_id;
  const hasThumbnail = !!node.thumbnail;

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
        await analyzeNode(node.id);
        if (onRefresh) onRefresh();
    } catch (error) {
        console.error("Analysis failed:", error);
    } finally {
        setIsAnalyzing(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete node "${node.id}"? This action cannot be undone.`)) {
        try {
            await deleteNode(node.id);
            if (onRefresh) onRefresh();
            onClose();
        } catch (error) {
            console.error("Delete failed:", error);
            alert("Failed to delete node.");
        }
    }
  };

  const handleSave = async () => {
    try {
        const updates = {
            ...editForm,
            tags: editForm.tags.split(',').map(t => t.trim()).filter(t => t)
        };
        await updateNode(node.id, updates);
        setIsEditing(false);
        if (onRefresh) onRefresh();
    } catch (error) {
        console.error("Update failed:", error);
        alert("Failed to update node.");
    }
  };

  return (
    <div className="absolute top-4 right-4 z-40 w-96 max-h-[90vh] bg-gray-800 border border-gray-600 rounded-lg shadow-2xl flex flex-col overflow-hidden backdrop-blur-md bg-opacity-95">
      {/* Header */}
      {(isVideo || hasThumbnail) && !isEditing ? (
          <div className="relative h-48 w-full shrink-0 group/video">
              <img 
                  src={node.thumbnail || `https://img.youtube.com/vi/${node.video_id}/mqdefault.jpg`} 
                  alt="Thumbnail" 
                  className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-black/20 to-transparent" />
              
              {isVideo && (
                <div className="absolute inset-0 flex items-center justify-center">
                    <a 
                        href={`https://www.youtube.com/watch?v=${node.video_id}`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="transform transition-transform hover:scale-110 group-hover/video:scale-110"
                    >
                        <PlayCircle className="w-16 h-16 text-white/90 drop-shadow-lg hover:text-blue-400 transition-colors" />
                    </a>
                </div>
              )}
              
              {/* Overlay Actions */}
              <div className="absolute top-2 right-2 flex gap-1">
                  <button 
                    onClick={() => setIsEditing(true)}
                    className="p-1.5 bg-black/60 hover:bg-black/80 rounded-full text-white/80 hover:text-white transition-colors"
                    title="Edit"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={onClose}
                    className="p-1.5 bg-black/60 hover:bg-black/80 rounded-full text-white/80 hover:text-white transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
              </div>
              
              <div className="absolute bottom-0 left-0 right-0 p-4">
                  <h2 className="text-lg font-bold text-white leading-tight line-clamp-2 drop-shadow-md">
                      {node.title || node.label || node.id}
                  </h2>
                  <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-blue-300 font-mono uppercase px-1 bg-blue-900/40 rounded border border-blue-500/30">
                          {isVideo ? 'VIDEO' : (node.type || 'WEB')}
                      </span>
                      {node.module && (
                          <span className="text-xs text-gray-300 font-medium px-1.5 py-0.5 rounded bg-gray-800/60 border border-gray-600/50">
                              {node.module}
                          </span>
                      )}
                  </div>
              </div>
          </div>
      ) : (
          <div className="bg-gray-900 p-4 border-b border-gray-700 flex justify-between items-start shrink-0">
            <div className="flex-1 min-w-0 mr-4">
              <h2 className="text-lg font-bold text-white break-words truncate" title={node.id}>
                 {isEditing ? 'Editing Node' : (node.title || node.label || node.id)}
              </h2>
              <span className="text-xs text-blue-400 font-mono uppercase px-1 bg-blue-900/30 rounded border border-blue-800 mt-1 inline-block">
                {node.type || 'Node'}
              </span>
            </div>
            <div className="flex items-center gap-1">
              {!isEditing && (
                  <>
                    <button 
                      onClick={() => setIsEditing(true)}
                      className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-blue-400 transition-colors"
                      title="Edit"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={handleDelete}
                      className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-red-400 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <div className="w-px h-4 bg-gray-700 mx-1" />
                  </>
              )}
              <button 
                onClick={onClose}
                className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
      )}

      {/* Content */}
      <div className="p-4 overflow-y-auto custom-scrollbar flex-1 space-y-6">
        
        {isEditing ? (
            /* EDIT FORM */
            <div className="space-y-4">
                <div>
                    <label className="text-xs text-gray-500 uppercase font-bold block mb-1">Title</label>
                    <input 
                        type="text" 
                        value={editForm.title}
                        onChange={(e) => setEditForm({...editForm, title: e.target.value})}
                        className="w-full bg-black/30 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:border-blue-500 outline-none"
                    />
                </div>
                <div>
                    <label className="text-xs text-gray-500 uppercase font-bold block mb-1">Module</label>
                    <input 
                        type="text" 
                        value={editForm.module}
                        onChange={(e) => setEditForm({...editForm, module: e.target.value})}
                        className="w-full bg-black/30 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:border-blue-500 outline-none"
                    />
                </div>
                <div>
                    <label className="text-xs text-gray-500 uppercase font-bold block mb-1">Tags (comma separated)</label>
                    <input 
                        type="text" 
                        value={editForm.tags}
                        onChange={(e) => setEditForm({...editForm, tags: e.target.value})}
                        className="w-full bg-black/30 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:border-blue-500 outline-none"
                    />
                </div>
                <div>
                    <label className="text-xs text-gray-500 uppercase font-bold block mb-1">Summary</label>
                    <textarea 
                        value={editForm.summary}
                        onChange={(e) => setEditForm({...editForm, summary: e.target.value})}
                        className="w-full h-24 bg-black/30 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:border-blue-500 outline-none resize-none"
                    />
                </div>
                <div>
                    <label className="text-xs text-gray-500 uppercase font-bold block mb-1">Content</label>
                    <textarea 
                        value={editForm.content}
                        onChange={(e) => setEditForm({...editForm, content: e.target.value})}
                        className="w-full h-48 bg-black/30 border border-gray-600 rounded px-2 py-1.5 text-xs font-mono text-gray-300 focus:border-blue-500 outline-none"
                    />
                </div>
                
                <div className="flex gap-2 pt-2">
                    <button 
                        onClick={handleSave}
                        className="flex-1 bg-green-600 hover:bg-green-500 text-white py-2 rounded text-sm font-semibold flex items-center justify-center gap-2"
                    >
                        <Save className="w-4 h-4" /> Save
                    </button>
                    <button 
                        onClick={() => setIsEditing(false)}
                        className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded text-sm font-semibold flex items-center justify-center gap-2"
                    >
                        <RotateCcw className="w-4 h-4" /> Cancel
                    </button>
                </div>
            </div>
        ) : (
            /* VIEW MODE */
            <>
                {/* AI Analysis Section */}
                <div className="space-y-3">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2 text-purple-400 text-sm font-semibold">
                            <Sparkles className="w-4 h-4" />
                            AI Metadata
                        </div>
                        <button 
                            onClick={handleAnalyze}
                            disabled={isAnalyzing}
                            className="text-xs bg-purple-600 hover:bg-purple-500 text-white px-2 py-1 rounded flex items-center gap-1 disabled:opacity-50"
                        >
                            {isAnalyzing ? (
                                <BrainCircuit className="w-3 h-3 animate-pulse" />
                            ) : (
                                <Sparkles className="w-3 h-3" />
                            )}
                            {isAnalyzing ? 'Analyzing...' : 'Regenerate'}
                        </button>
                    </div>

                    {/* Summary Card */}
                    <div className="bg-purple-900/20 border border-purple-500/30 p-3 rounded text-sm text-gray-300 italic">
                        "{node.summary || "No summary available. Click regenerate."}"
                    </div>

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2">
                        {node.tags && node.tags.length > 0 ? (
                            node.tags.map((tag, i) => (
                                <span key={i} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full border border-gray-600">
                                    #{tag}
                                </span>
                            ))
                        ) : (
                            <span className="text-xs text-gray-500">No tags</span>
                        )}
                    </div>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-black/30 p-3 rounded border border-gray-700">
                        <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
                        <Tag className="w-3 h-3" /> Module
                        </div>
                        <div className="font-semibold text-sm text-gray-200">
                        {node.module || 'General'}
                        </div>
                    </div>
                    <div className="bg-black/30 p-3 rounded border border-gray-700">
                        {/* Topic Cluster (New from PRD) */}
                        <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
                        <BrainCircuit className="w-3 h-3" /> Topic
                        </div>
                        <div className="font-semibold text-sm text-gray-200">
                        {node.topic_cluster || 'Unclassified'}
                        </div>
                    </div>
                </div>

                {/* File Content */}
                <div>
                    <div className="flex items-center gap-2 text-gray-400 text-sm font-semibold mb-2 border-b border-gray-700 pb-1">
                        <FileText className="w-4 h-4" />
                        Original Content
                    </div>
                    <div className="bg-gray-900 p-3 rounded border border-gray-700 font-mono text-sm text-gray-300 whitespace-pre-wrap max-h-96 overflow-y-auto custom-scrollbar">
                        {node.content || "No content available."}
                    </div>
                </div>
            </>
        )}
      </div>
    </div>
  );
};

export default NodeInspector;

