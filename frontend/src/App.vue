<script setup>
import { computed, onMounted, ref } from "vue";
import GraphView from "./components/GraphView.vue";
import SearchBar from "./components/SearchBar.vue";
import UploadPanel from "./components/UploadPanel.vue";
import { fetchGraph, listDocuments, searchGraph } from "./services/api";

const graph = ref({ nodes: [], edges: [] });
const highlight = ref({ nodeIds: [], edgeIds: [] });
const searchMatches = ref([]);
const hasSearched = ref(false);
const documents = ref([]);
const loading = ref(false);
const GRAPH_EDGE_LIMIT_OPTIONS = [1000, 5000];
for (let value = 10000; value <= 100000; value += 10000) {
  GRAPH_EDGE_LIMIT_OPTIONS.push(value);
}
const DEFAULT_GRAPH_EDGE_LIMIT = 1000;
const MIN_CONFIDENCE = 0;
const MAX_CONFIDENCE = 1;
const CONFIDENCE_STEP = 0.05;
const graphEdgeLimit = ref(DEFAULT_GRAPH_EDGE_LIMIT);
const graphConfidenceThreshold = ref(0);
const graphMeta = ref({ totalEdges: 0, returnedEdges: 0, limited: false });
const selectedDocumentIds = ref([]);
let activeSearchRequestId = 0;

const allDocumentsSelected = computed({
  get() {
    return documents.value.length > 0 && selectedDocumentIds.value.length === documents.value.length;
  },
  set(checked) {
    selectedDocumentIds.value = checked ? documents.value.map((doc) => doc.id) : [];
  },
});

async function refreshGraph() {
  loading.value = true;
  try {
    const response = await fetchGraph({
      document_ids: selectedDocumentIds.value.join(","),
      limit: graphEdgeLimit.value,
      min_confidence: graphConfidenceThreshold.value,
    });
    graph.value = {
      nodes: response.nodes || [],
      edges: response.edges || [],
    };
    graphMeta.value = response.meta || {
      totalEdges: response.edges?.length || 0,
      returnedEdges: response.edges?.length || 0,
      limited: false,
    };
  } finally {
    loading.value = false;
  }
}

async function refreshDocuments() {
  const nextDocuments = await listDocuments();
  const previousIds = new Set(selectedDocumentIds.value);
  documents.value = nextDocuments;
  const nextIds = nextDocuments.map((doc) => doc.id);

  if (!previousIds.size) {
    selectedDocumentIds.value = nextIds;
    return;
  }

  selectedDocumentIds.value = nextIds.filter((id) => previousIds.has(id));
  nextIds.forEach((id) => {
    if (!previousIds.has(id)) {
      selectedDocumentIds.value.push(id);
    }
  });
}

async function handleSearch(payload) {
  const requestId = ++activeSearchRequestId;
  hasSearched.value = Boolean(payload.q);
  if (!payload.q) {
    highlight.value = { nodeIds: [], edgeIds: [] };
    searchMatches.value = [];
    return;
  }
  const result = await searchGraph(payload.q, payload.type);
  // Ignore stale responses so an older request cannot clear newer highlights.
  if (requestId !== activeSearchRequestId) {
    return;
  }
  highlight.value = result.highlight || { nodeIds: [], edgeIds: [] };
  searchMatches.value = result.matches || [];
}

function formatTriple(match) {
  return `(${match.subject}, ${match.predicate}, ${match.object})`;
}

function formatConfidence(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return value.toFixed(2);
}

async function handleUploaded() {
  await refreshDocuments();
  setTimeout(refreshGraph, 2000);
}

onMounted(async () => {
  await refreshDocuments();
  await refreshGraph();
});
</script>

<template>
  <main class="app">
    <UploadPanel @uploaded="handleUploaded" />
    <SearchBar @search="handleSearch" />
    <section class="panel">
      <div class="graph-controls">
        <label class="graph-control-field" for="graph-limit">
          <span>Graph edge limit</span>
          <select id="graph-limit" v-model.number="graphEdgeLimit">
            <option v-for="option in GRAPH_EDGE_LIMIT_OPTIONS" :key="option" :value="option">
              {{ option.toLocaleString() }}
            </option>
          </select>
        </label>
        <label class="graph-control-field graph-confidence-control" for="graph-confidence">
          <span>Minimum confidence: {{ formatConfidence(graphConfidenceThreshold) }}</span>
          <input
            id="graph-confidence"
            v-model.number="graphConfidenceThreshold"
            type="range"
            :min="MIN_CONFIDENCE"
            :max="MAX_CONFIDENCE"
            :step="CONFIDENCE_STEP"
          />
        </label>
        <button :disabled="loading" @click="refreshGraph">
          {{ loading ? "Refreshing..." : "Refresh graph" }}
        </button>
      </div>
      <p class="graph-meta">
        Showing {{ graphMeta.returnedEdges }} of {{ graphMeta.totalEdges }} edges
        <span v-if="graphMeta.limited">(limited)</span>
        above confidence {{ formatConfidence(graphConfidenceThreshold) }}
      </p>
    </section>
    <p v-if="loading">Loading graph...</p>
    <GraphView :graph="graph" :highlight="highlight" :search-active="hasSearched" />

    <section class="panel">
      <h2>Documents</h2>
      <label class="document-check-all">
        <input v-model="allDocumentsSelected" type="checkbox" />
        <span>Check all</span>
      </label>
      <ul class="document-checklist">
        <li v-for="doc in documents" :key="doc.id">
          <label class="document-check-item">
            <input v-model="selectedDocumentIds" type="checkbox" :value="doc.id" />
            <span>#{{ doc.id }} - {{ doc.title || doc.file }} ({{ doc.status }})</span>
          </label>
        </li>
      </ul>
    </section>
    <section v-if="hasSearched" class="panel">
      <h2>Search Results</h2>
      <p v-if="!searchMatches.length">No matching triples found.</p>
      <table v-else class="results-table">
        <thead>
          <tr>
            <th>Triple</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="match in searchMatches" :key="match.id">
            <td>{{ formatTriple(match) }}</td>
            <td>{{ formatConfidence(match.confidence) }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>
