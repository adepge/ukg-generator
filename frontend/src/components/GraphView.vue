<script setup>
import {
  DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS,
  EdgeCurvedArrowProgram,
  createDrawCurvedEdgeLabel,
  indexParallelEdgesIndex,
} from "@sigma/edge-curve";
import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import noverlap from "graphology-layout-noverlap";
import { drawStraightEdgeLabel } from "sigma/rendering";
import Sigma from "sigma";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  graph: {
    type: Object,
    required: true,
  },
  highlight: {
    type: Object,
    default: () => ({ nodeIds: [], edgeIds: [] }),
  },
  searchActive: {
    type: Boolean,
    default: false,
  },
});

const graphWrapperEl = ref(null);
const graphEl = ref(null);
const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  subject: "",
  predicate: "",
  object: "",
  confidence: null,
});
let graph = null;
let renderer = null;
let hoveredEdgeId = null;

const NODE_BASE_COLOR = "#146173";
const NODE_TEXT_COLOR = "#1f2937";
const EDGE_BASE_OPACITY = 1;
const EDGE_BASE_COLOR = "#146173";
const HIGHLIGHT_COLOR = "#f97316";
const NODE_SIZE = 3;
const CURVED_EDGE_BASE_MAGNITUDE = 0.35;
const MAX_EDGE_LABELS = 150;
const drawCurvedEdgeLabel = createDrawCurvedEdgeLabel(DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS);

function getField(item, key, fallback = undefined) {
  return item?.data?.[key] ?? item?.[key] ?? fallback;
}

function toKey(value) {
  if (value === null || value === undefined) {
    return null;
  }
  return String(value);
}

function rgbaFromHex(hex, alpha) {
  const normalized = hex.replace("#", "");
  const chunk =
    normalized.length === 3
      ? normalized
          .split("")
          .map((c) => c + c)
          .join("")
      : normalized;
  const r = parseInt(chunk.slice(0, 2), 16);
  const g = parseInt(chunk.slice(2, 4), 16);
  const b = parseInt(chunk.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function getEdgeCurvature(edgeId) {
  const parallelIndex = graph.getEdgeAttribute(edgeId, "parallelIndex");
  const parallelMinIndex = graph.getEdgeAttribute(edgeId, "parallelMinIndex");
  const parallelMaxIndex = graph.getEdgeAttribute(edgeId, "parallelMaxIndex");

  if (parallelIndex === null || parallelIndex === undefined) {
    return 0;
  }

  // Same-direction parallel edges receive symmetric indices like -1, 0, 1.
  if (parallelMinIndex !== null && parallelMinIndex !== undefined) {
    return parallelIndex * CURVED_EDGE_BASE_MAGNITUDE;
  }

  // Opposite-direction edges both get a positive index, so use edge direction
  // to place one arc on each side of the segment.
  const source = graph.source(edgeId);
  const target = graph.target(edgeId);
  const directionSign = String(source).localeCompare(String(target)) <= 0 ? 1 : -1;
  const scale = Math.max(Number(parallelMaxIndex) || 1, 1);

  return directionSign * (parallelIndex / scale) * CURVED_EDGE_BASE_MAGNITUDE;
}

function destroyRenderer() {
  if (renderer) {
    renderer.kill();
    renderer = null;
  }
  tooltip.value.visible = false;
  graph = null;
}

function formatConfidence(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return value.toFixed(2);
}

function applyBaseStyles() {
  graph.forEachNode((nodeId) => {
    graph.mergeNodeAttributes(nodeId, {
      color: NODE_BASE_COLOR,
      hidden: false,
    });
  });
  graph.forEachEdge((edgeId) => {
    const baseOpacity = Number(graph.getEdgeAttribute(edgeId, "_baseOpacity") ?? EDGE_BASE_OPACITY);
    graph.mergeEdgeAttributes(edgeId, {
      color: rgbaFromHex(EDGE_BASE_COLOR, baseOpacity),
      hidden: false,
      size: 2,
    });
  });
}

function applyHoveredEdgeStyles() {
  if (!hoveredEdgeId || !graph.hasEdge(hoveredEdgeId)) {
    return;
  }

  graph.mergeEdgeAttributes(hoveredEdgeId, {
    color: HIGHLIGHT_COLOR,
    size: 2.5,
  });

  const source = graph.source(hoveredEdgeId);
  const target = graph.target(hoveredEdgeId);

  if (source && graph.hasNode(source)) {
    graph.mergeNodeAttributes(source, { color: HIGHLIGHT_COLOR });
  }
  if (target && graph.hasNode(target)) {
    graph.mergeNodeAttributes(target, { color: HIGHLIGHT_COLOR });
  }
}

function showEdgeTooltip(edgeId, event) {
  if (!graph || !graph.hasEdge(edgeId) || !graphWrapperEl.value) {
    return;
  }

  const sourceId = graph.source(edgeId);
  const targetId = graph.target(edgeId);
  const edgeAttrs = graph.getEdgeAttributes(edgeId);
  const sourceLabel = graph.hasNode(sourceId) ? graph.getNodeAttribute(sourceId, "label") : sourceId;
  const targetLabel = graph.hasNode(targetId) ? graph.getNodeAttribute(targetId, "label") : targetId;

  tooltip.value = {
    visible: true,
    x: event.event.x + 12,
    y: event.event.y + 12,
    subject: sourceLabel || sourceId || "",
    predicate: edgeAttrs.label || "",
    object: targetLabel || targetId || "",
    confidence: typeof edgeAttrs.confidence === "number" ? edgeAttrs.confidence : null,
  };
}

function hideTooltip() {
  tooltip.value.visible = false;
}

function getLayoutConfig(nodeCount, edgeCount) {
  if (nodeCount > 400 || edgeCount > 800) {
    return {
      forceAtlasIterations: 20,
      noverlapIterations: 0,
    };
  }

  if (nodeCount > 200 || edgeCount > 300) {
    return {
      forceAtlasIterations: 50,
      noverlapIterations: 60,
    };
  }

  return {
    forceAtlasIterations: 100,
    noverlapIterations: 100,
  };
}

function renderGraph() {
  if (!graphEl.value) {
    return;
  }

  destroyRenderer();

  const nodes = props.graph?.nodes || [];
  const edges = props.graph?.edges || [];
  graph = new Graph({ type: "directed", multi: true});

  const nodeCount = Math.max(nodes.length, 1);
  nodes.forEach((node, index) => {
    const id = toKey(getField(node, "id"));
    if (!id || graph.hasNode(id)) {
      return;
    }
    const angle = (2 * Math.PI * index) / nodeCount;
    graph.addNode(id, {
      label: getField(node, "label", id),
      x: Math.cos(angle),
      y: Math.sin(angle),
      size: NODE_SIZE,
      color: NODE_BASE_COLOR,
      labelColor: NODE_TEXT_COLOR,
      type: "circle",
    });
  });

  edges.forEach((edge, index) => {
    const source = toKey(getField(edge, "source"));
    const target = toKey(getField(edge, "target"));
    if (!source || !target || !graph.hasNode(source) || !graph.hasNode(target)) {
      return;
    }

    const id = toKey(getField(edge, "id", `edge-${index}`));
    if (graph.hasEdge(id)) {
      return;
    }

    const edgeOpacity = Number(getField(edge, "opacity", EDGE_BASE_OPACITY));
    graph.addEdgeWithKey(id, source, target, {
      label: getField(edge, "label", ""),
      size: 2,
      color: rgbaFromHex(EDGE_BASE_COLOR, edgeOpacity),
      type: "arrow",
      confidence: Number(getField(edge, "confidence")),
      _baseOpacity: edgeOpacity,
    });
  });

  const layoutConfig = getLayoutConfig(nodes.length, edges.length);
  if (layoutConfig.forceAtlasIterations > 0) {
    forceAtlas2.assign(graph, {
      iterations: layoutConfig.forceAtlasIterations,
      settings: forceAtlas2.inferSettings(graph),
    });
  }

  if (layoutConfig.noverlapIterations > 0) {
    noverlap.assign(graph, {
      maxIterations: layoutConfig.noverlapIterations,
      settings: {
        margin: 8,
        ratio: 1.2,
      },
    });
  }

  indexParallelEdgesIndex(graph);
  graph.forEachEdge((edgeId) => {
    const maxIndex = graph.getEdgeAttribute(edgeId, "parallelMaxIndex") ?? 0;
    const curvature = getEdgeCurvature(edgeId);

    graph.setEdgeAttribute(edgeId, "curvature", curvature);
    graph.setEdgeAttribute(edgeId, "type", maxIndex > 0 ? "curvedArrow" : "arrow");
  });

  renderer = new Sigma(graph, graphEl.value, {
    enableEdgeEvents: true,
    enableEdgeHoverEvents: true,
    minCameraRatio: 0.05,
    maxCameraRatio: 10,
    labelDensity: 0.09,
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
  });

  renderer.on("enterEdge", (event) => {
    hoveredEdgeId = event.edge;
    showEdgeTooltip(event.edge, event);
    applyHighlight();
  });
  renderer.on("leaveEdge", () => {
    hoveredEdgeId = null;
    hideTooltip();
    applyHighlight();
  });
  renderer.on("kill", () => {
    hoveredEdgeId = null;
    hideTooltip();
  });
}

function applyHighlight() {
  if (!graph || !renderer) {
    return;
  }

  const nodeIds = new Set((props.highlight?.nodeIds || []).map(toKey).filter(Boolean));
  const edgeIds = new Set((props.highlight?.edgeIds || []).map(toKey).filter(Boolean));

  applyBaseStyles();

  const existingNodeIds = [...nodeIds].filter((id) => graph.hasNode(id));
  const existingEdgeIds = [...edgeIds].filter((id) => graph.hasEdge(id));

  if (!props.searchActive) {
    applyHoveredEdgeStyles();
    renderer.refresh();
    return;
  }

  const visibleNodeIds = new Set(existingNodeIds);
  const visibleEdgeIds = new Set(existingEdgeIds);
  existingEdgeIds.forEach((id) => {
    if (graph.hasEdge(id)) {
      const source = graph.source(id);
      const target = graph.target(id);
      if (source) {
        visibleNodeIds.add(source);
      }
      if (target) {
        visibleNodeIds.add(target);
      }
    }
  });

  graph.forEachNode((nodeId) => {
    graph.mergeNodeAttributes(nodeId, {
      hidden: !visibleNodeIds.has(nodeId),
    });
  });
  graph.forEachEdge((edgeId) => {
    graph.mergeEdgeAttributes(edgeId, {
      hidden: !visibleEdgeIds.has(edgeId),
      size: 2,
    });
  });

  if (hoveredEdgeId && !visibleEdgeIds.has(hoveredEdgeId)) {
    hoveredEdgeId = null;
    hideTooltip();
  }

  applyHoveredEdgeStyles();
  renderer.refresh();
}

onMounted(renderGraph);
onBeforeUnmount(() => {
  destroyRenderer();
});

watch(
  () => props.graph,
  () => {
    renderGraph();
    applyHighlight();
  },
  { deep: true }
);

watch(
  () => props.highlight,
  () => applyHighlight(),
  { deep: true }
);

watch(
  () => props.searchActive,
  () => applyHighlight()
);
</script>

<template>
  <section class="panel">
    <h2>Knowledge Graph</h2>
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
        <div><strong>Confidence:</strong> {{ formatConfidence(tooltip.confidence) }}</div>
      </div>
    </div>
  </section>
</template>
