import dagre from 'dagre';

export const getLayoutedElements = (nodes, edges, config = {}) => {
  const {
    rankSep = 250, // Increased for better level separation (was 180)
    nodeSep = 180, // Horizontal spacing (was 120)
    rankDir = 'LR' // Left-to-Right flow
  } = config;

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({ 
    rankdir: rankDir,
    ranksep: rankSep,
    nodesep: nodeSep,
    edgesep: 50, // Minimum edge length
    align: 'DL', // Align nodes to top-left of their rank
    acyclicer: 'greedy', // Handle cycles better
    ranker: 'network-simplex' // Better ranking algorithm
  });

  // Set Node Dimensions based on Type (with padding to prevent overlap)
  nodes.forEach((node) => {
    const type = node.data?.node_type || 'child';
    let width = 280;
    let height = 120;

    if (type === 'topic') {
        width = 380; // Increased from 350
        height = 180; // Increased from 150
    } else if (type === 'module') {
        width = 320; // Increased from 300
        height = 150; // Increased from 130
    } else if (type === 'child') {
        width = 280; // Increased from 260
        height = 120; // Increased from 100
    }

    // Add padding to prevent overlap
    dagreGraph.setNode(node.id, { 
      width: width + 40, // Add padding
      height: height + 40 
    });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: rankDir === 'LR' ? 'left' : 'top',
      sourcePosition: rankDir === 'LR' ? 'right' : 'bottom',
      position: {
        x: nodeWithPosition.x - (nodeWithPosition.width || 280) / 2,
        y: nodeWithPosition.y - (nodeWithPosition.height || 120) / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};
