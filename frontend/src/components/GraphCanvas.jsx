import React, { useCallback, useEffect, useMemo } from 'react';
import ReactFlow, { 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState, 
  SelectionMode,
  MarkerType,
  addEdge,
  ReactFlowProvider,
  useReactFlow
} from 'reactflow';
import 'reactflow/dist/style.css';
import { createEdge, ingestText } from '../api';
import { getLayoutedElements } from '../utils/layout';
import { Layout } from 'lucide-react';
import CustomNode from './CustomNode';
import CustomEdge from './CustomEdge';

// Node/Edge Types Registry
const nodeTypes = {
  default: CustomNode,
  document: CustomNode
};

const edgeTypes = {
  default: CustomEdge
};

const GraphCanvasContent = ({ 
  nodes: initialNodes, 
  edges: initialEdges, 
  selectedNodeIds, 
  onSelectionChange, 
  contextNodes, 
  depthMode,
  onDepthChange,
  onTriggerContext,
  onRefresh 
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const reactFlowInstance = useReactFlow();

  // Handle Global Paste (YouTube or Generic URL)
  useEffect(() => {
    const handlePaste = async (e) => {
        // Only trigger if no input/textarea is focused
        if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

        const text = e.clipboardData.getData('text');
        if (!text) return;

        // Detect URL
        // Matches http:// or https:// followed by any non-whitespace characters
        const urlRegex = /^(https?:\/\/[^\s]+)$/;
        const match = text.match(urlRegex);
        
        if (match) {
            e.preventDefault();
            const url = match[0];
            
            // Determine Type for UI Feedback
            const isYouTube = url.match(/^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/);
            const label = isYouTube ? 'Analyzing Video...' : 'Processing Link...';
            
            // Skeleton Node
            const loadingId = 'ingesting-' + Date.now();
            const loadingNode = {
                id: 'processing...',
                type: 'document',
                data: { label: label, module: 'Ingestion', status: 'loading' },
                position: reactFlowInstance.project({ x: window.innerWidth / 2, y: window.innerHeight / 2 }),
                style: { opacity: 0.8 }
            };
            
            // Optimistic update
            setNodes((nds) => nds.concat(loadingNode));

            try {
                await ingestText(url, "General");
                if (onRefresh) onRefresh();
            } catch (err) {
                console.error("Paste ingestion failed:", err);
                alert(`Failed to ingest content: ${err.message}`);
                setNodes((nds) => nds.filter(n => n.id !== 'processing...'));
            }
        }
    };

    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [onRefresh, reactFlowInstance, setNodes]);

  // Initialize Graph with Auto-Layout
  useEffect(() => {
    if (initialNodes) { 
        // Create raw nodes first
        const rawNodes = initialNodes.map((n) => ({
            id: n.id,
            data: { label: n.id, ...n },
            type: 'document', // Use our custom type
            position: n.position || { x: 0, y: 0 }
        }));

        const rawEdges = initialEdges.map(e => ({
            id: `${e.source}-${e.target}`,
            source: e.source,
            target: e.target,
            label: e.justification,
            type: 'default', // Use our custom edge
            markerEnd: { type: MarkerType.ArrowClosed },
            animated: false
        }));

        // Apply Layout if it's a fresh load (or force it)
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rawNodes, rawEdges);

        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
    }
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // Handle Styling based on Selection and Context
  useEffect(() => {
    setNodes((nds) => 
      nds.map((node) => {
        const isSelected = selectedNodeIds.includes(node.id);
        const isContext = contextNodes.some(cn => cn.id === node.id) && !isSelected;
        
        // Pass context state to data so CustomNode can use it if needed
        // or just use style for opacity
        return {
            ...node,
            selected: isSelected, // Force update
            style: {
                opacity: (selectedNodeIds.length === 0 || isSelected || isContext) ? 1 : 0.2,
                transition: 'opacity 0.3s ease'
            }
        };
      })
    );
  }, [selectedNodeIds, contextNodes, setNodes]);

  const onSelectionChangeCallback = useCallback(({ nodes: selectedNodes }) => {
    const ids = selectedNodes.map(n => n.id);
    onSelectionChange(ids);
  }, [onSelectionChange]);

  const onConnect = useCallback(async (params) => {
    const justification = window.prompt("Why are these nodes related? (Edge Justification)");
    if (!justification) return; 

    const newEdge = { 
        ...params, 
        id: `${params.source}-${params.target}`, 
        label: justification,
        type: 'default',
        markerEnd: { type: MarkerType.ArrowClosed }
    };
    setEdges((eds) => addEdge(newEdge, eds));

    try {
        await createEdge(params.source, params.target, justification);
        if (onRefresh) onRefresh(); 
    } catch (error) {
        console.error("Failed to create edge:", error);
        alert("Failed to save edge to server.");
    }
  }, [setEdges, onRefresh]);

  const handleLayout = useCallback(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      edges
    );
    setNodes([...layoutedNodes]);
    setEdges([...layoutedEdges]);
    setTimeout(() => reactFlowInstance.fitView(), 10);
  }, [nodes, edges, setNodes, setEdges, reactFlowInstance]);

  return (
    <div className="w-full h-full bg-black relative font-sans">
      <div className="absolute top-4 left-4 z-10 flex gap-2 items-center">
         {/* Layout Toolbar */}
         <div className="bg-gray-900/80 backdrop-blur border border-white/10 p-1.5 rounded-xl shadow-xl flex gap-2 items-center">
             <button 
                onClick={handleLayout}
                className="p-2 hover:bg-white/10 rounded-lg text-gray-300 hover:text-white transition-colors"
                title="Auto Layout"
             >
                <Layout className="w-4 h-4" />
             </button>
         </div>

         {/* Context Toolbar */}
         <div className="bg-gray-900/80 backdrop-blur border border-white/10 p-1.5 rounded-xl shadow-xl flex gap-1 items-center">
            {['F0', 'F1', 'F2'].map((mode) => (
            <button
                key={mode}
                onClick={() => onDepthChange(mode)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                depthMode === mode 
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' 
                    : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`}
            >
                {mode}
            </button>
            ))}
            <div className="w-px h-4 bg-white/10 mx-1" />
            <button 
                onClick={onTriggerContext}
                className="px-3 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-lg shadow-lg transition-all"
            >
                Chat
            </button>
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onSelectionChange={onSelectionChangeCallback}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        selectionMode={SelectionMode.Partial}
        multiSelectionKeyCode="Control"
        fitView
        className="bg-black"
      >
        <Background color="#222" gap={20} size={1} />
        <Controls className="bg-gray-900 border-white/10 text-gray-400" />
      </ReactFlow>
    </div>
  );
};

// Wrap in Provider to support internal hooks
const GraphCanvas = (props) => (
  <ReactFlowProvider>
    <GraphCanvasContent {...props} />
  </ReactFlowProvider>
);

export default GraphCanvas;
