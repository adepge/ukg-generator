<script setup>
import { computed } from "vue";

// Define the props for the toolbar component (values passed from the parent component)
const props = defineProps({
  edgeLimit: {
    type: Number,
    required: true,
  },
  edgeLimitOptions: {
    type: Array,
    required: true,
  },
  minConfidence: {
    type: Number,
    required: true,
  },
  confidenceMin: {
    type: Number,
    default: 0,
  },
  confidenceMax: {
    type: Number,
    default: 1,
  },
  confidenceStep: {
    type: Number,
    default: 0.05,
  },
  meta: {
    type: Object,
    default: () => ({ totalEdges: 0, returnedEdges: 0, limited: false }),
  },
  searchActive: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  documentCount: {
    type: Number,
    default: 0,
  },
  selectedDocumentCount: {
    type: Number,
    default: 0,
  },
  settingsSummary: {
    type: Object,
    default: () => ({
      active_label_list: null,
      enabled_ontology_count: 0,
      enabled_custom_blacklist_count: 0,
    }),
  },
});

// Define the emits for the toolbar component (values passed to the parent component)
const emit = defineEmits([
  "update:edgeLimit",
  "update:minConfidence",
  "refresh",
  "open-filter",
]);

// Model for the edge limit
const edgeLimitModel = computed({
  get: () => props.edgeLimit,
  set: (value) => emit("update:edgeLimit", Number(value)),
});

// Model for the minimum confidence threshold
const minConfidenceModel = computed({
  get: () => props.minConfidence,
  set: (value) => emit("update:minConfidence", Number(value)),
});

// Formats the confidence value to a string (2 decimal places)
function formatConfidence(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  return value.toFixed(2);
}
</script>

<template>
  <div class="floating-toolbar" role="toolbar" aria-label="Graph controls">
    <div class="toolbar-field">
      <label for="tb-edge-limit">Edges</label>
      <select id="tb-edge-limit" v-model.number="edgeLimitModel">
        <option v-for="option in edgeLimitOptions" :key="option" :value="option">
          {{ option.toLocaleString() }}
        </option>
      </select>
    </div>

    <div class="toolbar-divider" aria-hidden="true"></div>

    <div class="toolbar-field">
      <label for="tb-confidence">Min conf.</label>
      <input
        id="tb-confidence"
        v-model.number="minConfidenceModel"
        type="range"
        :min="confidenceMin"
        :max="confidenceMax"
        :step="confidenceStep"
      />
      <span class="toolbar-value">{{ formatConfidence(minConfidence) }}</span>
    </div>

    <div class="toolbar-divider" aria-hidden="true"></div>

    <button
      type="button"
      class="btn btn-primary"
      :disabled="loading"
      @click="emit('refresh')"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        style="width: 16px; height: 16px;"
      >
        <path d="M3 12a9 9 0 0 1 15.5-6.36L21 8" />
        <path d="M21 3v5h-5" />
        <path d="M21 12a9 9 0 0 1-15.5 6.36L3 16" />
        <path d="M3 21v-5h5" />
      </svg>
      {{ loading ? "Refreshing..." : "Refresh" }}
    </button>

    <button
      type="button"
      class="btn"
      title="Filter documents"
      @click="emit('open-filter')"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        style="width: 16px; height: 16px;"
      >
        <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
      </svg>
      Filter
      <span
        v-if="documentCount > 0"
        class="status-chip"
        style="margin-left: 4px;"
      >
        {{ selectedDocumentCount }}/{{ documentCount }}
      </span>
    </button>

    <div class="toolbar-divider" aria-hidden="true"></div>

    <span class="toolbar-meta">
      {{ meta.returnedEdges }}/{{ meta.totalEdges }}
      {{ searchActive ? "search edges" : "edges" }}
      <span v-if="meta.limited">(limited)</span>
    </span>

    <div class="toolbar-divider" aria-hidden="true"></div>

    <div class="toolbar-settings-summary" aria-label="Active settings">
      <span class="status-chip" title="Active label list">
        Labels: {{ settingsSummary?.active_label_list?.name || "none" }}
      </span>
      <span class="status-chip" title="Enabled ontologies">
        {{ settingsSummary?.enabled_ontology_count ?? 0 }} ontologies
      </span>
      <span class="status-chip" title="Enabled custom blacklists">
        {{ settingsSummary?.enabled_custom_blacklist_count ?? 0 }} custom blacklists
      </span>
    </div>
  </div>
</template>
