<script setup>
/* GraphView component
   This component is the main component that displays the UKG graph.
   It is responsible for rendering the graph, handling the graph's state, and updating the graph when the user interacts with it.
*/

import {
  DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS,
  EdgeCurvedArrowProgram,
  createDrawCurvedEdgeLabel,
  indexParallelEdgesIndex,
} from "@sigma/edge-curve";
import convert from "color-convert";
import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import noverlap from "graphology-layout-noverlap";
import { drawStraightEdgeLabel } from "sigma/rendering";
import Sigma from "sigma";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";


// Define the props for the component (values passed from the parent component)
const props = defineProps({
  graph: {
    type: Object,
    required: true,
  },
  highlight: {
    type: Object,
    default: () => ({ nodeIds: [], edgeIds: [] }),
  },
  detailHighlight: {
    type: Object,
    default: () => ({ nodeIds: [], edgeIds: [] }),
  },
  searchActive: {
    type: Boolean,
    default: false,
  },
  theme: {
    type: String,
    default: "light",
  },
});

// Define the emits for the component (values passed to the parent component)
const emit = defineEmits(["triple-click"]);

// Parse the numeric triple id from an edge id like `triple-42` (vue id) or `42`.
function parseTripleId(edgeId) {
  if (edgeId === null || edgeId === undefined) return null;
  const str = String(edgeId);
  const match = str.match(/^triple-(\d+)$/);
  if (match) return Number(match[1]);
  if (/^\d+$/.test(str)) return Number(str);
  return null;
}

// References to the graph container and the graph element
const graphWrapperEl = ref(null);
const graphEl = ref(null);

// Edge tooltip data
const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  subject: "",
  predicate: "",
  object: "",
  confidence: null,
});

// References to the graph, renderer, and hovered edge id
let graph = null;
let renderer = null;
let hoveredEdgeId = null;

// Reducer state: when non-null the graph is filtered to these sets.
// These are used to filter the graph to avoid rendering unnecessary nodes and edges.
let visibleNodeIds = null;
let visibleEdgeIds = null;
let highlightedEndpoints = new Set();
let selectedNodeIds = new Set();
let selectedEdgeIds = new Set();

// Graph style tokens (resolved from CSS variables at render time so the graph
// honours the active theme).
let nodeBaseColor = "#146173";
let edgeBaseColor = "#146173";
let edgeBaseRgb = null;
let edgeBaseHsl = null;
let nodeLabelColor = "#1f2937";
let labelBgColor = "#ffffffcc";
let hoverBgColor = "#ffffff";
let useConfidenceLuminanceGradient = false;

// Constants for the graph (usually used as fallback values)
const EDGE_BASE_OPACITY = 0.5;                          // The base opacity of the edges
const HIGHLIGHT_COLOR = "#f97316";                      // The highlight color of the nodes/edges
const NODE_SIZE = 3;                                    // The size of the nodes
const CURVED_EDGE_BASE_MAGNITUDE = 0.35;                // The base magnitude of the curved edges
const MAX_EDGE_LABELS = 150;                            // The maximum number of edge labels

// Beyond this edge count, disable curved edges and edge hover events, which
// have a per-edge cost that dominates at scale.
const LARGE_GRAPH_EDGE_THRESHOLD = 3000;
const drawCurvedEdgeLabel = createDrawCurvedEdgeLabel(
  DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS
);

// Gets the visual configuration of the graph based on the number of nodes and edges
function getVisualConfig(nodeCount, edgeCount) {
  if (nodeCount > 6000 || edgeCount > 15000) {
    return {
      nodeSize: 1.75,
      edgeSize: 1.25,
      labelDensity: 0.01,
      labelRenderedSizeThreshold: 14,
    };
  }
  if (nodeCount > 1500 || edgeCount > 4000) {
    return {
      nodeSize: 2.2,
      edgeSize: 1.5,
      labelDensity: 0.03,
      labelRenderedSizeThreshold: 10,
    };
  }
  return {
    nodeSize: NODE_SIZE,
    edgeSize: 2,
    labelDensity: 0.09,
    labelRenderedSizeThreshold: 8,
  };
}

// Resolves the theme colors for the graph (based on dark and light mode)
function resolveThemeColors() {
  if (typeof window === "undefined") return;
  const root = document.documentElement;
  const styles = window.getComputedStyle(root);

  // Get the theme colors from the CSS variables
  const node = styles.getPropertyValue("--graph-node-color").trim();
  const edge = styles.getPropertyValue("--graph-edge-color").trim();
  const label = styles.getPropertyValue("--graph-label-color").trim();
  const surface = styles.getPropertyValue("--color-surface").trim();
  if (node) nodeBaseColor = node;
  if (edge) edgeBaseColor = edge;
  if (label) nodeLabelColor = label;

  // Determine if luminosity or opacity is used for the edge color (depending on the theme)
  useConfidenceLuminanceGradient = props.theme === "dark";
  const normalizedEdgeHex = edgeBaseColor.replace("#", "");
  const resolvedEdgeRgb = convert.hex.rgb.raw(normalizedEdgeHex);

  // Convert the edge color to RGB values
  edgeBaseRgb =
    Array.isArray(resolvedEdgeRgb) &&
    resolvedEdgeRgb.length === 3 &&
    resolvedEdgeRgb.every((channel) => Number.isFinite(channel))
      ? resolvedEdgeRgb.map((channel) => Math.round(channel))
      : null;
  edgeBaseHsl = edgeBaseRgb ? convert.rgb.hsl.raw(edgeBaseRgb) : null;
  if (surface) {
    hoverBgColor = surface;
    labelBgColor = surface + "cc";
  }
}

// Draws a rounded rectangle (for the node label background)
function drawRoundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

// Draws the label for a node
function customDrawLabel(context, data, settings) {
  if (!data.label) return;
  const size = settings.labelSize;
  const font = settings.labelFont;
  const weight = settings.labelWeight;

  context.font = `${weight} ${size}px ${font}`;
  const width = context.measureText(data.label).width + 8;

  context.fillStyle = labelBgColor;
  context.fillRect(data.x + data.size, data.y + size / 3 - 15, width, 20);

  context.fillStyle = nodeLabelColor;
  context.fillText(data.label, data.x + data.size + 3, data.y + size / 3);
}

// Draws the hover background for the node label (when the mouse is over the node)
function customDrawHover(context, data, settings) {
  const size = settings.labelSize;
  const font = settings.labelFont;
  const weight = settings.labelWeight;

  const label = data.label;
  if (!label) return;

  context.font = `${weight} ${size}px ${font}`;
  const labelWidth = context.measureText(label).width;

  // Calculate the position and size of the node label background
  const x = Math.round(data.x);
  const y = Math.round(data.y);
  const w = Math.round(labelWidth + size / 2 + data.size + 3);
  const h = Math.round(size + 10);

  // Draw the node label background
  context.beginPath();
  context.fillStyle = hoverBgColor;
  context.shadowOffsetX = 0;
  context.shadowOffsetY = 2;
  context.shadowBlur = 8;
  context.shadowColor = "rgba(0,0,0,0.3)";
  drawRoundRect(context, x, y - h / 2, w, h, 5);
  context.fill();
  context.closePath();

  context.shadowOffsetX = 0;
  context.shadowOffsetY = 0;
  context.shadowBlur = 0;

  // Draw the node label text
  context.fillStyle = nodeLabelColor;
  context.font = `${weight} ${size}px ${font}`;
  context.fillText(label, data.x + data.size + 3, data.y + size / 3);
}


// Helper function to get the value of a field from an item (the data object or the item itself)
function getField(item, key, fallback) {
  fallback = typeof fallback === "undefined" ? undefined : fallback;
  if (item && item.data && typeof item.data === "object" && item.data !== null && key in item.data) {
    return item.data[key];
  }
  if (item && key in item) {
    return item[key];
  }
  return fallback;
}

// Helper function to convert a value to a string key
function toKey(value) {
  if (value === null || value === undefined) return null;
  return String(value);
}

// Computes the color of an edge based on the confidence value in dark mode (changes the luminosity of the edge color)
function confidenceToDarkModeColor(confidence) {
  if (!Array.isArray(edgeBaseHsl) || edgeBaseHsl.length !== 3) return edgeBaseColor;

  // Normalize the confidence value to be between 0 and 1
  const normalizedConfidence = Number.isFinite(confidence)
    ? Math.min(Math.max(confidence, 0), 1)
    : 0.5;
  const [hue, saturation] = edgeBaseHsl;

  // The gradient range is from 22 to 52 (22 is the base lightness, 52 is the maximum lightness)
  const lightness = 22 + normalizedConfidence * 30;
  const nextSaturation = Math.min(
    Math.max(saturation * 0.9 + normalizedConfidence * 8, 0),
    100
  );

  // Convert the HSL values to RGB values
  const rgb = convert.hsl.rgb.raw(hue, nextSaturation, lightness);
  if (!Array.isArray(rgb) || rgb.length !== 3) return edgeBaseColor;
  const [r, g, b] = rgb.map((channel) => Math.round(channel));

  return `rgb(${r}, ${g}, ${b})`;
}

// Computes the curvature of an edge based on the parallel index and the source and target nodes
function getEdgeCurvature(edgeId) {
  const parallelIndex = graph.getEdgeAttribute(edgeId, "parallelIndex");
  const parallelMinIndex = graph.getEdgeAttribute(edgeId, "parallelMinIndex");
  const parallelMaxIndex = graph.getEdgeAttribute(edgeId, "parallelMaxIndex");

  if (parallelIndex === null || parallelIndex === undefined) {
    return 0;
  }

  // If the edge is parallel to other edges, the curvature is determined by the parallel index
  if (parallelMinIndex !== null && parallelMinIndex !== undefined) {
    return parallelIndex * CURVED_EDGE_BASE_MAGNITUDE;
  }

  // Sign of the curvature is determined by the direction of the edge (so that opposite edges do not have the same curvature)
  const source = graph.source(edgeId);
  const target = graph.target(edgeId);
  const directionSign =
    String(source).localeCompare(String(target)) <= 0 ? 1 : -1;
  const scale = Math.max(Number(parallelMaxIndex) || 1, 1);

  return directionSign * (parallelIndex / scale) * CURVED_EDGE_BASE_MAGNITUDE;
}

// Destroys the renderer and resets the graph state
function destroyRenderer() {
  if (renderer) {
    renderer.kill();
    renderer = null;
  }
  tooltip.value.visible = false;
  graph = null;
  visibleNodeIds = null;
  visibleEdgeIds = null;
  highlightedEndpoints = new Set();
  selectedNodeIds = new Set();
  selectedEdgeIds = new Set();
  hoveredEdgeId = null;
}

// Formats the confidence value to a string (2 decimal places)
function formatConfidence(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  return value.toFixed(2);
}

// Shows the tooltip for an edge (when the mouse is over the edge)
function showEdgeTooltip(edgeId, event) {
  if (!graph || !graph.hasEdge(edgeId) || !graphWrapperEl.value) return;

  // Get the source and target nodes and edge attributes
  const sourceId = graph.source(edgeId);
  const targetId = graph.target(edgeId);
  const edgeAttrs = graph.getEdgeAttributes(edgeId);
  const sourceLabel = graph.hasNode(sourceId)
    ? graph.getNodeAttribute(sourceId, "label")
    : sourceId;
  const targetLabel = graph.hasNode(targetId)
    ? graph.getNodeAttribute(targetId, "label")
    : targetId;

  // Set the tooltip data
  tooltip.value = {
    visible: true,
    x: event.event.x + 12,
    y: event.event.y + 12,
    subject: sourceLabel || sourceId || "",
    predicate: edgeAttrs.label || "",
    object: targetLabel || targetId || "",
    confidence:
      typeof edgeAttrs.confidence === "number" ? edgeAttrs.confidence : null,
  };
}

// Hides the tooltip
function hideTooltip() {
  tooltip.value.visible = false;
}

// Gets the layout configuration for the graph based on the number of nodes and edges
// Uses the ForceAtlas2 layout algorithm and the noverlap layout algorithm
// The ForceAtlas2 algorithm also uses the Barnes-Hut approximation to speed up the layout process
// The ForceAtlast 2 layout is used to simulate the physical forces between nodes and edges
// The noverlap layout algorithm is used to avoid node overlap
function getLayoutConfig(nodeCount, edgeCount) {
  if (nodeCount > 12000 || edgeCount > 30000) {
    return {
      forceAtlasIterations: 40,
      forceAtlasSettings: {
        barnesHutOptimize: true,
        barnesHutTheta: 0.6,
        gravity: 0.015,
        scalingRatio: 40,
        strongGravityMode: false,
        slowDown: 8,
      },
      noverlapIterations: 12,
      noverlapSettings: { margin: 4, ratio: 1.4, speed: 3 },
    };
  }
  if (nodeCount > 3000 || edgeCount > 6000) {
    return {
      forceAtlasIterations: 60,
      forceAtlasSettings: {
        barnesHutOptimize: true,
        barnesHutTheta: 0.6,
        gravity: 0.02,
        scalingRatio: 22,
        strongGravityMode: false,
        slowDown: 6,
      },
      noverlapIterations: 20,
      noverlapSettings: { margin: 6, ratio: 1.35, speed: 3 },
    };
  }
  if (nodeCount > 800 || edgeCount > 1600) {
    return {
      forceAtlasIterations: 70,
      forceAtlasSettings: {
        barnesHutOptimize: true,
        barnesHutTheta: 0.7,
        gravity: 0.03,
        scalingRatio: 12,
        strongGravityMode: false,
        slowDown: 4,
      },
      noverlapIterations: 35,
      noverlapSettings: { margin: 8, ratio: 1.25, speed: 3 },
    };
  }
  if (nodeCount > 400 || edgeCount > 600) {
    return {
      forceAtlasIterations: 80,
      forceAtlasSettings: {
        barnesHutOptimize: true,
        gravity: 0.04,
        scalingRatio: 8,
        slowDown: 3,
      },
      noverlapIterations: 60,
      noverlapSettings: { margin: 8, ratio: 1.2, speed: 3 },
    };
  }
  return {
    forceAtlasIterations: 100,
    forceAtlasSettings: {
      barnesHutOptimize: false,
      gravity: 0.05,
      scalingRatio: 6,
      slowDown: 2,
    },
    noverlapIterations: 100,
    noverlapSettings: { margin: 8, ratio: 1.2, speed: 3 },
  };
}

// Builds the graph from the nodes and edges
function buildGraph(nodes, edges, visualConfig) {
  const g = new Graph({ type: "directed", multi: true });
  const nodeCount = Math.max(nodes.length, 1);

  // Add the nodes to the graph
  nodes.forEach((node, index) => {
    // Get the node id (default to the index of the node if not provided)
    const id = toKey(getField(node, "id"));

    // If the node id does not exist or the node already exists, return
    if (!id || g.hasNode(id)) return;

    // Calculate the angle of the node (based on the index of the node)
    const angle = (2 * Math.PI * index) / nodeCount;
    g.addNode(id, {
      label: getField(node, "label", id),
      x: Math.cos(angle),
      y: Math.sin(angle),
      size: visualConfig.nodeSize,
      type: "circle",
    });
  });

  // Add the edges to the graph
  edges.forEach((edge, index) => {
    // Get the source and target nodes of the edge
    const source = toKey(getField(edge, "source"));
    const target = toKey(getField(edge, "target"));

    // If the source or target nodes do not exist, return
    if (!source || !target || !g.hasNode(source) || !g.hasNode(target)) {
      return;
    }

    // Get the edge id (default to `edge-${index}` if not provided)
    const id = toKey(getField(edge, "id", `edge-${index}`));
    if (g.hasEdge(id)) return;

    // Add the edge to the graph
    // Get the edge opacity (default to EDGE_BASE_OPACITY if not provided)
    const edgeOpacity = Number(getField(edge, "opacity", EDGE_BASE_OPACITY));
    g.addEdgeWithKey(id, source, target, {
      label: getField(edge, "label", ""),
      size: visualConfig.edgeSize,
      type: "arrow",
      confidence: Number(getField(edge, "confidence")),
      _baseOpacity: edgeOpacity,
      _baseSize: visualConfig.edgeSize,
    });
  });

  return g;
}

// Rebuilds the highlight state of the graph
function rebuildHighlightState() {
  if (!graph) return;

  // Get the node and edge ids from the highlight and detail highlight props
  const nodeIds = (props.highlight?.nodeIds || []).map(toKey).filter(Boolean);
  const edgeIds = (props.highlight?.edgeIds || []).map(toKey).filter(Boolean);
  const detailNodeIds = (props.detailHighlight?.nodeIds || []).map(toKey).filter(Boolean);
  const detailEdgeIds = (props.detailHighlight?.edgeIds || []).map(toKey).filter(Boolean);

  // Set the selected node and edge ids to the detail highlight node and edge ids
  selectedNodeIds = new Set();
  selectedEdgeIds = new Set();
  detailNodeIds.forEach((id) => {
    // If the node exists, add it to the selected node ids
    if (graph.hasNode(id)) selectedNodeIds.add(id);
  });

  // Add the detail edge ids to the selected edge ids
  detailEdgeIds.forEach((id) => {
    if (!graph.hasEdge(id)) return;
    selectedEdgeIds.add(id);
    const src = graph.source(id);
    const tgt = graph.target(id);
    if (src) selectedNodeIds.add(src);
    if (tgt) selectedNodeIds.add(tgt);
  });

  // If the search is not active, set the visible node and edge ids to null
  // This removes the filtering of the graph to show all nodes and edges
  if (!props.searchActive) {
    visibleNodeIds = null;
    visibleEdgeIds = null;
    return;
  }

  // Set the visible node and edge ids to the node and edge ids from the highlight and detail highlight props
  const nodeSet = new Set();
  const edgeSet = new Set();

  nodeIds.forEach((id) => {
    if (graph.hasNode(id)) nodeSet.add(id);
  });
  edgeIds.forEach((id) => {
    if (!graph.hasEdge(id)) return;
    edgeSet.add(id);
    const src = graph.source(id);
    const tgt = graph.target(id);
    if (src) nodeSet.add(src);
    if (tgt) nodeSet.add(tgt);
  });

  visibleNodeIds = nodeSet;
  visibleEdgeIds = edgeSet;

  if (hoveredEdgeId && !edgeSet.has(hoveredEdgeId)) {
    hoveredEdgeId = null;
    highlightedEndpoints = new Set();
    hideTooltip();
  }
}

// Updates the hovered endpoints of the graph
function updateHoveredEndpoints() {
  if (!hoveredEdgeId || !graph || !graph.hasEdge(hoveredEdgeId)) {
    highlightedEndpoints = new Set();
    return;
  }

  // Get the source and target nodes of the hovered edge
  const endpoints = new Set();
  const src = graph.source(hoveredEdgeId);
  const tgt = graph.target(hoveredEdgeId);
  if (src) endpoints.add(src);
  if (tgt) endpoints.add(tgt);
  highlightedEndpoints = endpoints;
}

// Reduces the node data to the visible nodes
function nodeReducer(node, data) {
  const res = { ...data };

  // If the node is not visible, set the hidden attribute to true
  if (visibleNodeIds && !visibleNodeIds.has(node)) {
    res.hidden = true;
    return res;
  }

  // Set the color of the node to the highlight color if it is highlighted or selected
  res.color =
    highlightedEndpoints.has(node) || selectedNodeIds.has(node)
      ? HIGHLIGHT_COLOR
      : nodeBaseColor;
  res.labelColor = nodeLabelColor;
  return res;
}

// Reduces the edge data to the visible edges
function edgeReducer(edge, data) {
  const res = { ...data };

  // If the edge is not visible, set the hidden attribute to true
  if (visibleEdgeIds && !visibleEdgeIds.has(edge)) {
    res.hidden = true;
    return res;
  }

  // Set the size and color of the edge based on the hovered edge id or selected edge ids
  const baseSize = Number(data._baseSize ?? data.size ?? 2);
  if (edge === hoveredEdgeId || selectedEdgeIds.has(edge)) {
    res.color = HIGHLIGHT_COLOR;
    res.size = Math.max(baseSize + 0.5, baseSize * 1.25);
  } else {
    if (useConfidenceLuminanceGradient) {
      // If the confidence luminance gradient is used, set the color of the edge to the confidence to dark mode color
      res.color = confidenceToDarkModeColor(Number(data.confidence));
    } else {
      // If the confidence luminance gradient is not used, set the color of the edge to the edge base color
      // and use the opacity of the edge
      const baseOpacity = Number(data._baseOpacity ?? EDGE_BASE_OPACITY);
      res.color = edgeBaseRgb
        ? `rgba(${edgeBaseRgb[0]}, ${edgeBaseRgb[1]}, ${edgeBaseRgb[2]}, ${baseOpacity})`
        : edgeBaseColor;
    }
    res.size = baseSize;
  }
  return res;
}

// Refreshes the renderer of the graph
function refreshRenderer() {
  if (renderer) renderer.refresh();
}

// Renders the graph
function renderGraph() {
  if (!graphEl.value) return;

  resolveThemeColors(); // Resolve the theme colors for the graph
  destroyRenderer();    // Destroy the renderer of the graph

  const nodes = props.graph?.nodes || [];
  const edges = props.graph?.edges || [];
  const isLargeGraph = edges.length > LARGE_GRAPH_EDGE_THRESHOLD;
  const visualConfig = getVisualConfig(nodes.length, edges.length);

  // Build the graph from the nodes and edges
  graph = buildGraph(nodes, edges, visualConfig);


  // Get the layout configuration for the graph
  const layoutConfig = getLayoutConfig(nodes.length, edges.length);

  // If the force atlas iterations are greater than 0, assign the force atlas settings to the graph
  if (layoutConfig.forceAtlasIterations > 0) {
    const inferredSettings = forceAtlas2.inferSettings(graph);
    forceAtlas2.assign(graph, {
      iterations: layoutConfig.forceAtlasIterations,
      settings: {
        ...inferredSettings,
        ...layoutConfig.forceAtlasSettings,
      },
    });
  }

  // If the noverlap iterations are greater than 0, assign the noverlap settings to the graph
  if (layoutConfig.noverlapIterations > 0) {
    noverlap.assign(graph, {
      maxIterations: layoutConfig.noverlapIterations,
      settings: layoutConfig.noverlapSettings,
    });
  }

  // If the graph is not large, index the parallel edges and set the curvature of the edges
  if (!isLargeGraph) {
    indexParallelEdgesIndex(graph);
    graph.forEachEdge((edgeId) => {
      const maxIndex = graph.getEdgeAttribute(edgeId, "parallelMaxIndex") ?? 0;
      if (maxIndex > 0) {
        graph.setEdgeAttribute(edgeId, "curvature", getEdgeCurvature(edgeId));
        graph.setEdgeAttribute(edgeId, "type", "curvedArrow");
      }
    });
  }
  
  rebuildHighlightState();  // Rebuild the highlight state of the graph
  updateHoveredEndpoints(); // Update the hovered endpoints of the graph

  // Create a new renderer for the graph
  renderer = new Sigma(graph, graphEl.value, {
    allowInvalidContainer: true,
    enableEdgeEvents: true,
    enableEdgeHoverEvents: !isLargeGraph,
    hideEdgesOnMove: isLargeGraph,
    hideLabelsOnMove: isLargeGraph,
    minCameraRatio: 0.05,
    maxCameraRatio: 10,
    labelDensity: visualConfig.labelDensity,
    labelRenderedSizeThreshold: visualConfig.labelRenderedSizeThreshold,
    labelColor: { color: nodeLabelColor },
    defaultDrawNodeLabel: customDrawLabel,
    defaultDrawNodeHover: customDrawHover,
    renderEdgeLabels: edges.length <= MAX_EDGE_LABELS,
    defaultEdgeType: "arrow",
    defaultDrawEdgeLabel: (context, edgeData, sourceData, targetData, settings) => {
      if (edgeData.type === "curvedArrow") {
        return drawCurvedEdgeLabel(context, edgeData, sourceData, targetData, settings);
      }
      return drawStraightEdgeLabel(context, edgeData, sourceData, targetData, settings);
    },
    edgeProgramClasses: {
      curvedArrow: EdgeCurvedArrowProgram,
    },
    nodeReducer,
    edgeReducer,
  });

  // On enter edge, set the hovered edge id to the edge id and update the hovered endpoints
  renderer.on("enterEdge", (event) => {
    hoveredEdgeId = event.edge;
    updateHoveredEndpoints();
    showEdgeTooltip(event.edge, event);
    refreshRenderer();
  });

  // On leave edge, set the hovered edge id to null and update the hovered endpoints
  renderer.on("leaveEdge", () => {
    hoveredEdgeId = null;
    updateHoveredEndpoints();
    hideTooltip();
    refreshRenderer();
  });

  // On click edge, parse the triple id and emit the triple click event
  renderer.on("clickEdge", (event) => {
    const tripleId = parseTripleId(event.edge);
    if (tripleId !== null) {
      emit("triple-click", tripleId);
    }
  });

  // On kill, set the hovered edge id to null and hide the tooltip
  renderer.on("kill", () => {
    hoveredEdgeId = null;
    hideTooltip();
  });
}

// Applies the highlight state to the graph
function applyHighlight() {
  if (!graph || !renderer) return;
  rebuildHighlightState();
  updateHoveredEndpoints();
  refreshRenderer();
}

// Applies the theme to the graph
function applyTheme() {
  if (!renderer) return;
  resolveThemeColors();
  renderer.setSetting("labelColor", { color: nodeLabelColor });
  refreshRenderer();
}

// On mount, render the graph
onMounted(renderGraph);

// On before unmount, destroy the renderer and set the hovered edge id to null and hide the tooltip
onBeforeUnmount(() => {
  destroyRenderer();
});

// Re-render the graph when the graph prop changes
watch(
  () => props.graph,
  () => {
    renderGraph();
  }
);

// Re-apply the highlight state when the highlight prop changes
// This is used to highlight the selected triple when the triple is hovered or clicked
watch(
  () => props.highlight,
  () => applyHighlight(),
  { deep: true }
);

// Re-apply the highlight state when the detail highlight prop changes
// This is used to highlight the detail of the triple when the triple detail panel is open
watch(
  () => props.detailHighlight,
  () => applyHighlight(),
  { deep: true }
);

// Re-apply the highlight state when the search active prop changes
watch(
  () => props.searchActive,
  () => applyHighlight()
);

// Theme changes only need to update colors; no need to rebuild the graph or
// re-run the layout.
watch(
  () => props.theme,
  () => applyTheme()
);
</script>

<template>
  <div ref="graphWrapperEl" class="graph-container">
    <div ref="graphEl" class="graph"></div>
    <div
      v-if="tooltip.visible"
      class="graph-tooltip"
      :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
    >
      <div><strong>Subject:</strong> {{ tooltip.subject }}</div>
      <div><strong>Predicate:</strong> {{ tooltip.predicate }}</div>
      <div><strong>Object:</strong> {{ tooltip.object }}</div>
      <div>
        <strong>Confidence:</strong> {{ formatConfidence(tooltip.confidence) }}
      </div>
    </div>
  </div>
</template>
