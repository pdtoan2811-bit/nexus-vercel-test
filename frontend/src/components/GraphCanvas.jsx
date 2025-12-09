import React, { useCallback, useEffect, useState, useRef } from 'react';
import ReactFlow, { 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState, 
  SelectionMode,
  MarkerType,
  addEdge,
  ReactFlowProvider,
  useReactFlow,
  ConnectionMode,
  ConnectionLineType
} from 'reactflow';
import 'reactflow/dist/style.css';
import { createEdge, ingestText, getContext, uploadImage, updateNodePositions } from '../api';
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
  onRefresh,
  onEdgeClick,
  onConnectRequest // New prop for handling manual connections via App
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [contextRegistry, setContextRegistry] = useState(null);
  const reactFlowInstance = useReactFlow();
  
  // Ref to track if we need to update styles
  const prevSelectionRef = useRef(selectedNodeIds);
  const prevContextRef = useRef(contextNodes);
  
  // Debounced position save
  const positionSaveTimeoutRef = useRef(null);
  const hasInitialLayoutRef = useRef(false);

  // Fetch context registry for colors
  useEffect(() => {
    const fetchContext = async () => {
        try {
            const data = await getContext();
            setContextRegistry(data);
        } catch (e) {
            console.error("Failed to fetch context for colors", e);
        }
    };
    fetchContext();
  }, []);

  // Handle Global Paste (Images, YouTube, or Generic URL)
  useEffect(() => {
    const handlePaste = async (e) => {
        // Only trigger if no input/textarea is focused
        if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

        // Check for image first
        const items = Array.from(e.clipboardData.items);
        const imageItem = items.find(item => item.type.startsWith('image/'));
        
        if (imageItem) {
            e.preventDefault();
            const file = imageItem.getAsFile();
            
            if (!file) return;
            
            // Skeleton Node for image
            const loadingNode = {
                id: 'processing-image-' + Date.now(),
                type: 'document',
                data: { label: 'Analyzing Image...', module: 'Ingestion', status: 'loading' },
                position: reactFlowInstance.project({ x: window.innerWidth / 2, y: window.innerHeight / 2 }),
                style: { opacity: 0.8 }
            };
            
            // Optimistic update
            setNodes((nds) => nds.concat(loadingNode));
            
            try {
                // Upload and analyze image
                const result = await uploadImage(file, 'General', 'Uncategorized');
                
                // Remove loading node
                setNodes((nds) => nds.filter(n => n.id !== loadingNode.id));
                
                // Refresh graph to show new node
                if (onRefresh) {
                    await onRefresh();
                }
            } catch (error) {
                console.error('Image paste failed:', error);
                // Remove loading node and show error
                setNodes((nds) => nds.filter(n => n.id !== loadingNode.id));
                
                const errorNode = {
                    id: 'error-image-' + Date.now(),
                    type: 'document',
                    data: { 
                        label: 'Image Analysis Failed', 
                        module: 'Error', 
                        status: 'error',
                        error: error.message || 'Failed to analyze image'
                    },
                    position: reactFlowInstance.project({ x: window.innerWidth / 2, y: window.innerHeight / 2 }),
                    style: { opacity: 0.8 }
                };
                setNodes((nds) => nds.concat(errorNode));
                
                // Remove error node after 5 seconds
                setTimeout(() => {
                    setNodes((nds) => nds.filter(n => n.id !== errorNode.id));
                }, 5000);
            }
            return;
        }

        // Check for text/URL
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

  // Initialize Graph - Only apply layout to nodes without saved positions
  useEffect(() => {
    if (initialNodes && initialNodes.length > 0) { 
        // Create raw nodes first
        const rawNodes = initialNodes.map((n) => {
            // Determine Color: Manual override > Topic color > Default
            let nodeColor = n.color; // Check for manual override first
            if (!nodeColor) {
                // Fall back to topic color
                if (contextRegistry && contextRegistry.topics) {
                    const topicData = contextRegistry.topics[n.main_topic];
                    if (topicData && topicData.color) {
                        nodeColor = topicData.color;
                    }
                }
                // Final fallback
                if (!nodeColor) {
                    nodeColor = '#3B82F6'; // Default Blue
                }
            }

            return {
                id: n.id,
                data: { label: n.id, ...n, color: nodeColor },
                type: 'document', // Use our custom type
                position: n.position || null // Keep saved position if exists
            };
        });

        const rawEdges = initialEdges.map(e => ({
            id: `${e.source}-${e.target}`,
            source: e.source,
            target: e.target,
            label: e.justification,
            type: 'default', // Use our custom edge
            markerEnd: { type: MarkerType.ArrowClosed },
            animated: false
        }));

        // Separate nodes with and without positions
        const nodesWithPositions = rawNodes.filter(n => n.position && n.position.x !== 0 && n.position.y !== 0);
        const nodesWithoutPositions = rawNodes.filter(n => !n.position || (n.position.x === 0 && n.position.y === 0));

        // Only apply layout to nodes without positions
        let finalNodes = [...nodesWithPositions];
        if (nodesWithoutPositions.length > 0) {
            const { nodes: layoutedNodes } = getLayoutedElements(nodesWithoutPositions, rawEdges);
            finalNodes = [...finalNodes, ...layoutedNodes];
        }

        setNodes(finalNodes);
        setEdges(rawEdges);
        prevNodesRef.current = finalNodes;
        hasInitialLayoutRef.current = true;
        
        // Fit view only on initial load if there are new nodes without positions
        if (nodesWithoutPositions.length > 0) {
          setTimeout(() => {
            reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
          }, 100);
        }
    }
  }, [initialNodes, initialEdges, setNodes, setEdges, contextRegistry]);

  // Handle Styling based on Selection and Context
  useEffect(() => {
    // Avoid redundant updates
    const selectionChanged = JSON.stringify(selectedNodeIds) !== JSON.stringify(prevSelectionRef.current);
    const contextChanged = JSON.stringify(contextNodes) !== JSON.stringify(prevContextRef.current);

    if (!selectionChanged && !contextChanged) return;

    prevSelectionRef.current = selectedNodeIds;
    prevContextRef.current = contextNodes;

    setNodes((nds) => 
      nds.map((node) => {
        const isSelected = selectedNodeIds.includes(node.id);
        const isContext = contextNodes.some(cn => cn.id === node.id) && !isSelected;
        
        // Pass context state to data so CustomNode can use it if needed
        // or just use style for opacity
        return {
            ...node,
            // Removed: selected: isSelected (Let React Flow handle this internally)
            style: {
                ...node.style,
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
    // OLD: Prompt
    // NEW: Delegate to App via onConnectRequest
    if (onConnectRequest) {
        onConnectRequest(params);
    }
  }, [onConnectRequest]);

  // Save positions when nodes are moved (debounced)
  const savePositions = useCallback(async (nodesToSave) => {
    if (!hasInitialLayoutRef.current) return; // Don't save during initial load
    
    // Clear previous timeout
    if (positionSaveTimeoutRef.current) {
      clearTimeout(positionSaveTimeoutRef.current);
    }
    
    // Debounce: Save after 1 second of no movement
    positionSaveTimeoutRef.current = setTimeout(async () => {
      try {
        const positions = {};
        nodesToSave.forEach(node => {
          if (node.position && typeof node.position.x === 'number' && typeof node.position.y === 'number') {
            positions[node.id] = {
              x: node.position.x,
              y: node.position.y
            };
          }
        });
        
        if (Object.keys(positions).length > 0) {
          await updateNodePositions(positions);
          console.log(`Saved positions for ${Object.keys(positions).length} nodes`);
        }
      } catch (error) {
        console.error("Failed to save positions:", error);
      }
    }, 1000);
  }, []);

  // Track previous nodes for position comparison
  const prevNodesRef = useRef([]);

  // Handle node changes (including position changes)
  const handleNodesChange = useCallback((changes) => {
    onNodesChange(changes);
    
    // Check if any change is a position change
    const hasPositionChange = changes.some(change => change.type === 'position');
    
    if (hasPositionChange && hasInitialLayoutRef.current) {
      // Use a small delay to let React Flow update the nodes state
      setTimeout(() => {
        setNodes((currentNodes) => {
          // Save positions for all nodes that have valid positions
          savePositions(currentNodes);
          prevNodesRef.current = currentNodes;
          return currentNodes;
        });
      }, 100);
    }
  }, [onNodesChange, savePositions, setNodes]);

  const handleLayout = useCallback(() => {
    // Apply layout to all nodes
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      edges
    );
    setNodes([...layoutedNodes]);
    setEdges([...layoutedEdges]);
    
    // Save the new positions
    setTimeout(() => {
      savePositions(layoutedNodes);
      reactFlowInstance.fitView({ padding: 0.1, duration: 400 });
    }, 100);
  }, [nodes, edges, setNodes, setEdges, reactFlowInstance, savePositions]);

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
                onClick={handleLayout}
                className="px-3 py-1.5 bg-gray-700/80 hover:bg-gray-600 text-white text-xs font-semibold rounded-lg shadow-lg transition-all flex items-center gap-1.5"
                title="Auto-arrange all nodes"
            >
                <Layout className="w-3.5 h-3.5" />
                Layout
            </button>
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
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onSelectionChange={onSelectionChangeCallback}
        onEdgeClick={onEdgeClick}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        selectionMode={SelectionMode.Partial}
        multiSelectionKeyCode="Control"
        fitView={false}
        className="bg-black"
        connectionMode={ConnectionMode.Loose}
        connectionLineType={ConnectionLineType.SmoothStep}
        connectionLineStyle={{
            stroke: '#60a5fa',
            strokeWidth: 3,
            strokeDasharray: '5,5',
        }}
        nodesDraggable={true}
        nodesConnectable={true}
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
