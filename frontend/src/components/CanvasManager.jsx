import React, { useState, useEffect } from 'react';
import { getCanvases, createCanvas, activateCanvas, deleteCanvas } from '../api';
import { LayoutGrid, Plus, Trash2, CheckCircle, X } from 'lucide-react';

const CanvasManager = ({ isOpen, onClose, onSwitch }) => {
    const [canvases, setCanvases] = useState([]);
    const [activeId, setActiveId] = useState('default');
    const [newCanvasName, setNewCanvasName] = useState('');
    const [isCreating, setIsCreating] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchCanvases();
        }
    }, [isOpen]);

    const fetchCanvases = async () => {
        try {
            const list = await getCanvases();
            console.log("Fetched canvases:", list);
            setCanvases(list || []);
            
            // Backend now flags the active canvas
            const current = list?.find(c => c.is_active);
            if (current) {
                setActiveId(current.id);
            }
        } catch (error) {
            console.error("Failed to fetch canvases", error);
            alert("Failed to load canvases: " + (error.message || "Unknown error"));
        }
    };

    const handleCreate = async () => {
        if (!newCanvasName.trim()) {
            alert("Please enter a canvas name");
            return;
        }
        
        setIsLoading(true);
        try {
            console.log("Creating canvas with name:", newCanvasName.trim());
            const response = await createCanvas(newCanvasName.trim());
            console.log("Canvas created successfully:", response);
            
            // Clear form and close dialog
            setNewCanvasName('');
            setIsCreating(false);
            setIsLoading(false);
            
            // Refresh canvas list to show the new canvas
            await fetchCanvases();
            
            // Notify App to refresh graph/settings
            if (onSwitch) {
                onSwitch(); 
            }
            
            // Close the modal so user sees the new canvas
            if (onClose) {
                onClose();
            }
        } catch (error) {
            console.error("Failed to create canvas", error);
            setIsLoading(false);
            const errorMessage = error.response?.data?.detail || error.message || "Failed to create canvas";
            alert(`Error creating canvas: ${errorMessage}`);
        }
    };

    const handleSwitch = async (id) => {
        try {
            await activateCanvas(id);
            setActiveId(id);
            onSwitch(); // Refresh main app
            onClose(); // Close the modal
        } catch (error) {
            console.error("Failed to switch canvas", error);
        }
    };

    const handleDelete = async (id, e) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure? This will delete the canvas and all its nodes permanently.")) return;
        try {
            await deleteCanvas(id);
            fetchCanvases();
        } catch (error) {
            console.error("Failed to delete canvas", error);
            alert("Could not delete canvas. Default canvas cannot be deleted.");
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-[#1C1C1E] w-[600px] h-[500px] rounded-2xl shadow-2xl border border-white/10 flex flex-col overflow-hidden">
                {/* Header */}
                <div className="p-6 border-b border-white/10 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <LayoutGrid className="w-6 h-6 text-blue-500" />
                        <h2 className="text-xl font-semibold text-white">Canvas Manager</h2>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    <div className="grid grid-cols-2 gap-4">
                        {/* New Canvas Card */}
                        <div 
                            onClick={() => setIsCreating(true)}
                            className="aspect-video bg-gray-900/50 border border-dashed border-gray-700 rounded-xl flex flex-col items-center justify-center text-gray-400 hover:text-white hover:border-blue-500 hover:bg-gray-800/50 cursor-pointer transition-all group"
                        >
                            <Plus className="w-8 h-8 mb-2 group-hover:scale-110 transition-transform" />
                            <span className="text-sm font-medium">Create New Canvas</span>
                        </div>

                        {/* Existing Canvases */}
                        {canvases.map((canvas) => (
                            <div 
                                key={canvas.id}
                                onClick={() => handleSwitch(canvas.id)}
                                className={`aspect-video relative rounded-xl border p-4 flex flex-col justify-between cursor-pointer transition-all group
                                    ${canvas.id === activeId ? 'bg-blue-900/20 border-blue-500' : 'bg-gray-900/50 border-white/5 hover:border-white/20 hover:bg-gray-800'}`}
                            >
                                <div>
                                    <h3 className="font-semibold text-white truncate">{canvas.name}</h3>
                                    <p className="text-xs text-gray-500 mt-1">
                                        Last modified: {new Date(canvas.last_modified).toLocaleDateString()}
                                    </p>
                                </div>
                                
                                <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    {canvas.id !== 'default' && (
                                        <button 
                                            onClick={(e) => handleDelete(canvas.id, e)}
                                            className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500 hover:text-white transition-colors"
                                            title="Delete"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    )}
                                </div>

                                {canvas.id === activeId && (
                                    <div className="absolute top-3 right-3 text-blue-500">
                                        <CheckCircle className="w-5 h-5" />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Create Dialog Overlay */}
                {isCreating && (
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6">
                        <div className="bg-[#2C2C2E] w-full max-w-sm rounded-xl p-6 shadow-2xl border border-white/10">
                            <h3 className="text-lg font-semibold text-white mb-4">Name your new canvas</h3>
                            <input 
                                type="text"
                                value={newCanvasName}
                                onChange={(e) => setNewCanvasName(e.target.value)}
                                placeholder="Project X..."
                                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 mb-4"
                                autoFocus
                                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                            />
                            <div className="flex justify-end gap-3">
                                <button 
                                    onClick={() => setIsCreating(false)}
                                    className="px-4 py-2 rounded-lg text-gray-300 hover:text-white hover:bg-white/5"
                                >
                                    Cancel
                                </button>
                                <button 
                                    onClick={handleCreate}
                                    disabled={!newCanvasName.trim() || isLoading}
                                    className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                >
                                    {isLoading ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            Creating...
                                        </>
                                    ) : (
                                        'Create Canvas'
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CanvasManager;
