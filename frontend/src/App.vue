<script setup>
import { onMounted, ref } from "vue";
import GraphView from "./components/GraphView.vue";
import SearchBar from "./components/SearchBar.vue";
import UploadPanel from "./components/UploadPanel.vue";
import { fetchGraph, listDocuments, searchGraph } from "./services/api";

const graph = ref({ nodes: [], edges: [] });
const highlight = ref({ nodeIds: [], edgeIds: [] });
const documents = ref([]);
const loading = ref(false);
let activeSearchRequestId = 0;

async function refreshGraph() {
  loading.value = true;
  try {
    graph.value = await fetchGraph();
  } finally {
    loading.value = false;
  }
}

async function refreshDocuments() {
  documents.value = await listDocuments();
}

async function handleSearch(payload) {
  const requestId = ++activeSearchRequestId;
  if (!payload.q) {
    highlight.value = { nodeIds: [], edgeIds: [] };
    return;
  }
  const result = await searchGraph(payload.q, payload.type);
  // Ignore stale responses so an older request cannot clear newer highlights.
  if (requestId !== activeSearchRequestId) {
    return;
  }
  highlight.value = result.highlight || { nodeIds: [], edgeIds: [] };
}

async function handleUploaded() {
  await refreshDocuments();
  setTimeout(refreshGraph, 2000);
}

onMounted(async () => {
  await Promise.all([refreshDocuments(), refreshGraph()]);
});
</script>

<template>
  <main class="app">
    <UploadPanel @uploaded="handleUploaded" />
    <SearchBar @search="handleSearch" />
    <p v-if="loading">Loading graph...</p>
    <GraphView :graph="graph" :highlight="highlight" />

    <section class="panel">
      <h2>Documents</h2>
      <ul>
        <li v-for="doc in documents" :key="doc.id">
          #{{ doc.id }} - {{ doc.title || doc.file }} ({{ doc.status }})
        </li>
      </ul>
    </section>
  </main>
</template>
