<script setup>

// Define the props for the triples sidebar component (values passed from the parent component)
const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  triples: {
    type: Array,
    default: () => [],
  },
  hasSearched: {
    type: Boolean,
    default: false,
  },
});

// Define the emits for the triples sidebar component (values passed to the parent component)
const emit = defineEmits(["close", "triple-click"]);

// Parses the triple id from the string like "triple-42" or "42"
function parseTripleId(raw) {
  if (raw === null || raw === undefined) return null;
  const str = String(raw);
  const match = str.match(/^triple-(\d+)$/);
  if (match) return Number(match[1]);
  if (/^\d+$/.test(str)) return Number(str);
  return null;
}

// On triple row click, parse the triple id and emit the triple click event
function onTripleRowClick(match) {
  const id = parseTripleId(match?.id);
  if (id !== null) {
    emit("triple-click", id);
  }
}

// Formats the triple to a string (subject, predicate, object)
function formatTriple(match) {
  return `(${match.subject}, ${match.predicate}, ${match.object})`;
}

// Formats the confidence value to a string (2 decimal places)
function formatConfidence(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";
  return n.toFixed(2);
}
</script>

<template>
  <aside v-if="open" class="sidebar" aria-label="Triples list">
    <div class="sidebar-header">
      <div>
        <h2>{{ hasSearched ? "Search results" : "Triples" }}</h2>
        <div class="sidebar-meta">
          {{ triples.length }}
          {{ triples.length === 1 ? "entry" : "entries" }}
        </div>
      </div>
      <button
        type="button"
        class="modal-close"
        aria-label="Close sidebar"
        @click="emit('close')"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M18 6 6 18" />
          <path d="m6 6 12 12" />
        </svg>
      </button>
    </div>

    <div class="sidebar-body">
      <div v-if="!triples.length" class="sidebar-empty">
        {{ hasSearched ? "No matching triples found." : "No triples to display." }}
      </div>
      <table v-else class="results-table">
        <thead>
          <tr>
            <th>Triple</th>
            <th>Conf.</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="match in triples"
            :key="match.id"
            class="triple-row"
            @click="onTripleRowClick(match)"
          >
            <td>{{ formatTriple(match) }}</td>
            <td>{{ formatConfidence(match.confidence) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </aside>
</template>
