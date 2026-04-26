<script setup>
/* SearchBar component
   This component is the search bar at the top of the page.
   It allows the user to search for entities or relations in the UKG graph.
   It additionally provides buttons for uploading documents, toggling the triples list, and toggling the theme.
*/

import { computed, ref, watch } from "vue";

// Define the props for the component (values passed from the parent component)
const props = defineProps({
  theme: {
    type: String,
    default: "light",
  },
  sidebarOpen: {
    type: Boolean,
    default: false,
  },
  settingsOpen: {
    type: Boolean,
    default: false,
  },
});

// Define the emits for the component (values passed to the parent component)
const emit = defineEmits([
  "search",
  "clear",
  "open-upload",
  "toggle-sidebar",
  "toggle-settings",
  "toggle-theme",
]);

const query = ref("");             // The query string to search for
const type = ref("entity");        // The type of the query (entity or relation)
const matchMode = ref("contains"); // The mode of the query (contains, word, exact)

const hasQuery = computed(() => query.value.trim().length > 0); // Whether the query is not empty

// Normalizes the query by replacing spaces with underscores
function normalizeQuery(value) {
  return value.trim().replace(/\s+/g, "_");
}

// Triggers the search
function trigger() {
  const normalizedQuery = normalizeQuery(query.value);
  query.value = normalizedQuery;
  emit("search", { q: normalizedQuery, type: type.value, match_mode: matchMode.value });
}

// Clears the search input
function clear() {
  query.value = "";
  emit("clear");
  emit("search", { q: "", type: type.value });
}

// If the user clears the input manually, also notify the parent.
watch(query, (value) => {
  if (!value.trim()) {
    emit("clear");
  }
});
</script>

<template>
  <div class="search-bar">
    <div class="search-input-wrapper">
      <svg
        class="search-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
      <input
        v-model="query"
        class="search-input"
        type="text"
        placeholder="Search entities or relations..."
        @keyup.enter="trigger"
      />
      <select v-model="matchMode" class="search-type" @change="trigger">
        <option value="contains">Contains</option>
        <option value="word">Match word</option>
        <option value="exact">Exact match</option>
      </select>
      <select v-model="type" class="search-type" @change="trigger">
        <option value="entity">Entity</option>
        <option value="relation">Relation</option>
      </select>
    </div>

    <div class="search-actions">
      <button
        type="button"
        class="btn-icon"
        :class="{ active: hasQuery }"
        title="Search"
        aria-label="Search"
        @click="trigger"
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
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      </button>

      <button
        v-if="hasQuery"
        type="button"
        class="btn-icon"
        title="Clear search"
        aria-label="Clear search"
        @click="clear"
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

      <button
        type="button"
        class="btn-icon"
        title="Upload documents"
        aria-label="Upload documents"
        @click="emit('open-upload')"
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
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </button>

      <button
        type="button"
        class="btn-icon"
        :class="{ active: sidebarOpen }"
        title="Toggle triples list"
        aria-label="Toggle triples list"
        @click="emit('toggle-sidebar')"
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
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <line x1="3" y1="9" x2="21" y2="9" />
          <line x1="3" y1="14" x2="21" y2="14" />
          <line x1="14" y1="4" x2="14" y2="20" />
        </svg>
      </button>

      <button
        type="button"
        class="btn-icon"
        :class="{ active: settingsOpen }"
        title="Settings"
        aria-label="Open settings"
        @click="emit('toggle-settings')"
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
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>

      <button
        type="button"
        class="btn-icon"
        :title="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
        :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="emit('toggle-theme')"
      >
        <svg
          v-if="theme === 'dark'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2" />
          <path d="M12 20v2" />
          <path d="m4.93 4.93 1.41 1.41" />
          <path d="m17.66 17.66 1.41 1.41" />
          <path d="M2 12h2" />
          <path d="M20 12h2" />
          <path d="m6.34 17.66-1.41 1.41" />
          <path d="m19.07 4.93-1.41 1.41" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      </button>
    </div>
  </div>
</template>
