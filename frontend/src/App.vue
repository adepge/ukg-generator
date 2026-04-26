<script setup>
import { computed, markRaw, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import DocumentModal from "./components/DocumentModal.vue";
import Toolbar from "./components/Toolbar.vue";
import GraphView from "./components/GraphView.vue";
import ProgressBar from "./components/ProgressBar.vue";
import SearchBar from "./components/SearchBar.vue";
import SettingsPanel from "./components/settings/SettingsPanel.vue";
import TripleDetailPanel from "./components/TripleDetailPanel.vue";
import TriplesSidebar from "./components/TriplesSidebar.vue";
import UploadModal from "./components/UploadModal.vue";
import {
  clearAll,
  fetchGraph,
  fetchTripleDetail,
  getSettingsSummary,
  listDocuments,
  searchGraph,
} from "./services/api";

// ---------- Graph data ----------
// The graph holds potentially tens of thousands of nodes/edges
// use shallowRef to prevent Vue from installing reactive getters on every entry
const graph = shallowRef({ nodes: [], edges: [] });            // The graph (filtered or full)
const baseGraph = shallowRef({ nodes: [], edges: [] });        // The base graph (full - before filtering)
const highlight = ref({ nodeIds: [], edgeIds: [] });           // The highlight (selected nodes/edges)
const detailHighlight = ref({ nodeIds: [], edgeIds: [] });     // The detail highlight (selected edge and its endpoints)
const searchMatches = ref([]);                                 // The search matches (triple matches)
const hasSearched = ref(false);                                // Whether the search is active
const documents = ref([]);                                     // The documents
const loading = ref(false);                                    // Whether the graph is loading (while fetching)

// ---------- Graph configuration ----------
// The edge limit options for the graph
const GRAPH_EDGE_LIMIT_OPTIONS = [1000, 5000];
for (let value = 10000; value <= 100000; value += 10000) {
  GRAPH_EDGE_LIMIT_OPTIONS.push(value);
}

// Constants for the graph configuration
const DEFAULT_GRAPH_EDGE_LIMIT = 1000;                       // The default edge limit for the graph
const MIN_CONFIDENCE = 0;                                    // The minimum confidence
const MAX_CONFIDENCE = 1;                                    // The maximum confidence
const CONFIDENCE_STEP = 0.05;                                // The confidence step (for the confidence slider)

// State for the graph configuration
const graphEdgeLimit = ref(DEFAULT_GRAPH_EDGE_LIMIT);                               // The edge limit for the graph
const graphConfidenceThreshold = ref(0);                                            // The confidence threshold for the graph
const graphMeta = ref({ totalEdges: 0, returnedEdges: 0, limited: false });         // The graph metadata (total edges, returned edges, limited)
const baseGraphMeta = ref({ totalEdges: 0, returnedEdges: 0, limited: false });     // The base graph metadata (total edges, returned edges, limited)
const selectedDocumentIds = ref([]);                                                // The selected document IDs (for the document filter)
const activeSearchPayload = ref(null);                                              // The active search payload (for the search bar)
let activeSearchRequestId = 0;                                                      // The active search request ID (incremented for each search request)

// ---------- Progress polling ----------
const PROGRESS_POLL_INTERVAL_MS = 2000;      // The progress poll interval in milliseconds (2 seconds)
let progressPollTimer = null;
let hadActiveProcessing = false;

// Computed property for the progress polling
// Determines if there is active processing (documents are queued or processing)
const isProcessingActive = computed(() =>
  documents.value.some(
    (doc) => doc.status === "queued" || doc.status === "processing"
  )
);

// ---------- UI state ----------
const clearing = ref(false);
const uploadModalOpen = ref(false);
const filterModalOpen = ref(false);
const sidebarOpen = ref(false);
const theme = ref("light");
const settingsPanelOpen = ref(false);
const settingsSummary = ref({
  active_label_list: null,
  enabled_ontology_count: 0,
  enabled_custom_blacklist_count: 0,
});

// Loads the settings summary from the API
async function loadSettingsSummary() {
  try {
    settingsSummary.value = await getSettingsSummary();
  } catch (error) {
    // Ignore errors if the settings summary cannot be loaded
  }
}

// Triple detail panel state.
const detailPanelOpen = ref(false);
const detailLoading = ref(false);
const detailError = ref("");
const detailData = ref(null);
let activeDetailRequestId = 0;

// Gets the current search parameters
function currentSearchParams() {
  return {
    document_ids: selectedDocumentIds.value.join(","),   // The selected document IDs
    limit: graphEdgeLimit.value,                         // The edge limit for the graph
    min_confidence: graphConfidenceThreshold.value,      // The confidence threshold for the graph
  };
}

// Sets the graph from the response
function setGraphFromResponse(response) {
  graph.value = markRaw({
    nodes: response.nodes || [],
    edges: response.edges || [],
  });
  graphMeta.value = response.meta || {
    totalEdges: response.edges?.length || 0,
    returnedEdges: response.edges?.length || 0,
    limited: false,
  };
}

// Builds the detail highlight for the triple detail panel
function buildDetailHighlight(tripleId) {
  const edgeId = `triple-${tripleId}`;
  const edge = (graph.value?.edges || []).find((item) => {
    const itemId = item?.data?.id ?? item?.id;
    return String(itemId) === edgeId;
  });

  if (!edge) {
    return { nodeIds: [], edgeIds: [] };
  }

  // Get the source and target IDs of the edge
  const sourceId = edge?.data?.source ?? edge?.source;
  const targetId = edge?.data?.target ?? edge?.target;
  return {
    nodeIds: [sourceId, targetId].filter((value) => value !== null && value !== undefined),
    edgeIds: [edgeId],
  };
}

// ---------- Theme management ----------
function applyTheme(next) {
  theme.value = next;
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", next);
  }
  try {
    localStorage.setItem("ukg:theme", next);
  } catch (error) {
    /* noop */
  }
}

function toggleTheme() {
  applyTheme(theme.value === "dark" ? "light" : "dark");
}

// ---------- Sidebar content ----------
// Used to display the triples in the sidebar (list of triples to display)
const displayedTriples = computed(() => {

  // If there is a search active, return the search matches (limit the triples displayed to the search matches)
  if (hasSearched.value) {
    return searchMatches.value;
  }

  const nodes = graph.value?.nodes || [];
  const edges = graph.value?.edges || [];
  const nodeLabels = new Map();

  // Build the node labels map
  nodes.forEach((node) => {
    const id = node?.data?.id ?? node?.id;
    if (id === null || id === undefined) return;
    const label = node?.data?.label ?? node?.label ?? String(id); // The label for the node
    nodeLabels.set(String(id), label);
  });

  // Build the triples map
  return edges.map((edge, index) => {
    const sourceId = String(edge?.data?.source ?? edge?.source ?? "");
    const targetId = String(edge?.data?.target ?? edge?.target ?? "");
    const edgeId = String(edge?.data?.id ?? edge?.id ?? `edge-${index}`);
    return {
      id: edgeId,
      subject: nodeLabels.get(sourceId) ?? sourceId,
      predicate: edge?.data?.label ?? edge?.label ?? "",
      object: nodeLabels.get(targetId) ?? targetId,
      confidence: Number(edge?.data?.confidence ?? edge?.confidence),
    };
  });
});

// ---------- Graph actions ----------
async function refreshGraph() {
  loading.value = true;
  try {
    const response = await fetchGraph({
      document_ids: selectedDocumentIds.value.join(","),
      limit: graphEdgeLimit.value,
      min_confidence: graphConfidenceThreshold.value,
    });
    const nextGraph = markRaw({
      nodes: response.nodes || [],
      edges: response.edges || [],
    });
    const nextMeta = response.meta || {
      totalEdges: response.edges?.length || 0,
      returnedEdges: response.edges?.length || 0,
      limited: false,
    };
    baseGraph.value = nextGraph;
    baseGraphMeta.value = nextMeta;
    if (!hasSearched.value) {
      graph.value = nextGraph;
      graphMeta.value = nextMeta;
    }
  } finally {
    loading.value = false;
  }
}

// Refreshes the documents from the API
async function refreshDocuments() {
  const nextDocuments = await listDocuments();
  const previousIds = new Set(selectedDocumentIds.value);
  documents.value = nextDocuments;
  const nextIds = nextDocuments.map((doc) => doc.id);

  // This handles the checkbox state for the documents
  // If there are no previous IDs, set the selected document IDs to the new IDs
  if (!previousIds.size) {
    selectedDocumentIds.value = nextIds;
    return;
  }

  // If there are previous IDs, filter the selected document IDs to the new IDs
  selectedDocumentIds.value = nextIds.filter((id) => previousIds.has(id));
  nextIds.forEach((id) => {
    if (!previousIds.has(id)) {
      selectedDocumentIds.value.push(id);
    }
  });
}

// ---------- Search ----------
async function handleSearch(payload) {
  const requestId = ++activeSearchRequestId;
  hasSearched.value = Boolean(payload.q);
  activeSearchPayload.value = payload.q ? { ...payload } : null;

  // If there is no search query, reset the graph and highlight
  if (!payload.q) {
    highlight.value = { nodeIds: [], edgeIds: [] };
    searchMatches.value = [];
    graph.value = baseGraph.value;
    graphMeta.value = baseGraphMeta.value;
    return;
  }

  // Search the graph for the query
  const result = await searchGraph(payload.q, payload.type, payload.match_mode, currentSearchParams());
  if (requestId !== activeSearchRequestId) return;
  setGraphFromResponse(result);
  highlight.value = result.highlight || { nodeIds: [], edgeIds: [] };
  searchMatches.value = result.matches || [];
}

// Clears the search
function handleClearSearch() {
  hasSearched.value = false;
  activeSearchPayload.value = null;
  graph.value = baseGraph.value;
  graphMeta.value = baseGraphMeta.value;
  highlight.value = { nodeIds: [], edgeIds: [] };
  searchMatches.value = [];
}

// Handles the refresh button
async function handleRefresh() {
  await refreshGraph();
  if (hasSearched.value && activeSearchPayload.value?.q) {
    await handleSearch(activeSearchPayload.value);
  }
}

// ---------- Uploads ----------
async function handleUploaded() {
  await refreshDocuments();
  ensureProgressPolling();
  setTimeout(refreshGraph, 2000);
}

// ---------- Progress polling ----------
function ensureProgressPolling() {
  if (progressPollTimer !== null) return;
  if (!isProcessingActive.value) return;
  hadActiveProcessing = true;
  progressPollTimer = window.setInterval(
    pollProgress,
    PROGRESS_POLL_INTERVAL_MS
  );
}

function stopProgressPolling() {
  if (progressPollTimer !== null) {
    window.clearInterval(progressPollTimer);
    progressPollTimer = null;
  }
}

// Polls the progress of the documents (queued or processing)
async function pollProgress() {
  try {
    await refreshDocuments();
  } catch (error) {
    return;
  }

  if (isProcessingActive.value) {
    hadActiveProcessing = true;
    return;
  }

  stopProgressPolling();

  if (hadActiveProcessing) {
    hadActiveProcessing = false;
    try {
      await refreshGraph();
    } catch (error) {
      /* noop */
    }
  }
}

// ---------- Document management ----------
// Handles the clear all button (deletes all documents, triples, and graph data)
async function handleClearAll() {
  if (
    !window.confirm(
      "This will permanently delete all documents, triples, and graph data. Continue?"
    )
  ) {
    return;
  }
  clearing.value = true;

  // Clear all documents, triples, and graph data
  try {
    await clearAll();
    documents.value = [];
    selectedDocumentIds.value = [];
    const emptyGraph = markRaw({ nodes: [], edges: [] });
    const emptyMeta = { totalEdges: 0, returnedEdges: 0, limited: false };
    graph.value = emptyGraph;
    baseGraph.value = emptyGraph;
    graphMeta.value = emptyMeta;
    baseGraphMeta.value = emptyMeta;
    highlight.value = { nodeIds: [], edgeIds: [] };
    detailHighlight.value = { nodeIds: [], edgeIds: [] };
    searchMatches.value = [];
    hasSearched.value = false;
    filterModalOpen.value = false;
  } finally {
    clearing.value = false;
  }
}

// Applies the filter (applies the selected document IDs to the graph)
function applyFilter() {
  filterModalOpen.value = false;
  refreshGraph(); // Refresh the graph with the new document IDs
}

// Handles the document deleted event (removal of one document)
async function handleDocumentDeleted(docId) {
  // Remove the deleted document from local state immediately.
  selectedDocumentIds.value = selectedDocumentIds.value.filter((id) => id !== docId);
  await refreshDocuments();
  await refreshGraph();
}

// Updates the selected document IDs (in the document filter modal)
function updateSelectedDocuments(ids) {
  selectedDocumentIds.value = ids;
}

// ---------- Triple detail ----------
// This handles the opening of the triple detail panel
async function openTripleDetail(tripleId) {
  if (tripleId === null || tripleId === undefined) return;

  const requestId = ++activeDetailRequestId;
  detailHighlight.value = buildDetailHighlight(tripleId);
  detailPanelOpen.value = true;
  detailLoading.value = true;
  detailError.value = "";
  detailData.value = null;

  try {
    const response = await fetchTripleDetail(tripleId);
    if (requestId !== activeDetailRequestId) return;
    detailData.value = response;
  } catch (error) {
    if (requestId !== activeDetailRequestId) return;
    detailHighlight.value = { nodeIds: [], edgeIds: [] };
    detailError.value =
      error?.response?.data?.detail ||
      "Could not load triple details. Please try again.";
  } finally {
    if (requestId === activeDetailRequestId) {
      detailLoading.value = false;
    }
  }
}

// Handles the closing of the triple detail panel
function closeTripleDetail() {
  activeDetailRequestId += 1; // Increment the active detail request ID
  detailPanelOpen.value = false;
  detailLoading.value = false;
  detailError.value = "";
  detailData.value = null;
  detailHighlight.value = { nodeIds: [], edgeIds: [] };
}

// ---------- Lifecycle ----------
onMounted(async () => {
  // Restore persisted theme preference or default to the OS preference.
  let initial = "light";
  try {
    const stored = localStorage.getItem("ukg:theme");
    if (stored === "light" || stored === "dark") {
      initial = stored;
    } else if (
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    ) {
      initial = "dark";
    }
  } catch (error) {
    /* noop */
  }
  applyTheme(initial);

  // Kick off the settings summary fetch in parallel with graph/document loads
  // so a transient error in one doesn't prevent the others from completing.
  loadSettingsSummary();

  // Refresh the documents and graph
  try {
    await refreshDocuments();
    await refreshGraph();
  } finally {
    ensureProgressPolling(); // Start the progress polling
  }
});

// On before unmount, stop the progress polling
onBeforeUnmount(() => {
  stopProgressPolling();
});

// Automatically stop polling when nothing is processing.
watch(isProcessingActive, (active) => {
  if (active) ensureProgressPolling();
});

// Refresh the settings summary whenever the panel is opened so the toolbar displays the correct settings summary
watch(settingsPanelOpen, (open) => {
  if (open) loadSettingsSummary();
});
</script>

<template>
  <main class="app">
    <div class="app-graph-layer">
      <GraphView
        :graph="graph"
        :highlight="highlight"
        :detail-highlight="detailHighlight"
        :search-active="hasSearched"
        :theme="theme"
        @triple-click="openTripleDetail"
      />
    </div>

    <div class="app-top-bar">
      <SearchBar
        :theme="theme"
        :sidebar-open="sidebarOpen"
        :settings-open="settingsPanelOpen"
        @search="handleSearch"
        @clear="handleClearSearch"
        @open-upload="uploadModalOpen = true"
        @toggle-sidebar="sidebarOpen = !sidebarOpen"
        @toggle-settings="settingsPanelOpen = !settingsPanelOpen"
        @toggle-theme="toggleTheme"
      />
      <Toolbar
        :edge-limit="graphEdgeLimit"
        :edge-limit-options="GRAPH_EDGE_LIMIT_OPTIONS"
        :min-confidence="graphConfidenceThreshold"
        :confidence-min="MIN_CONFIDENCE"
        :confidence-max="MAX_CONFIDENCE"
        :confidence-step="CONFIDENCE_STEP"
        :meta="graphMeta"
        :search-active="hasSearched"
        :loading="loading"
        :document-count="documents.length"
        :selected-document-count="selectedDocumentIds.length"
        :settings-summary="settingsSummary"
        @update:edge-limit="graphEdgeLimit = $event"
        @update:min-confidence="graphConfidenceThreshold = $event"
        @refresh="handleRefresh"
        @open-filter="filterModalOpen = true"
      />
    </div>

    <div class="app-progress-layer">
      <ProgressBar v-if="documents.length" :documents="documents" />
    </div>

    <TriplesSidebar
      :open="sidebarOpen"
      :triples="displayedTriples"
      :has-searched="hasSearched"
      @close="sidebarOpen = false"
      @triple-click="openTripleDetail"
    />

    <TripleDetailPanel
      :open="detailPanelOpen"
      :loading="detailLoading"
      :error="detailError"
      :detail="detailData"
      @close="closeTripleDetail"
    />

    <UploadModal
      :open="uploadModalOpen"
      @close="uploadModalOpen = false"
      @uploaded="handleUploaded"
    />

    <DocumentModal
      :open="filterModalOpen"
      :documents="documents"
      :selected-ids="selectedDocumentIds"
      :clearing="clearing"
      @close="filterModalOpen = false"
      @update:selected-ids="updateSelectedDocuments"
      @clear-all="handleClearAll"
      @apply="applyFilter"
      @deleted="handleDocumentDeleted"
    />

    <SettingsPanel
      :open="settingsPanelOpen"
      @close="settingsPanelOpen = false"
      @changed="loadSettingsSummary"
    />
  </main>
</template>
