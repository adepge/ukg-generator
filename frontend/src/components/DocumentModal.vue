<script setup>
/* DocumentModal component
   This component is a modal that allows the user to filter the documents displayed in the UKG graph.
   It also provides buttons to delete individual documents or all documents.
*/

import { computed, ref } from "vue";
import { deleteDocument } from "../services/api.js";


// Define the props for the component (values passed from the parent component)
const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  documents: {
    type: Array,
    default: () => [],
  },
  selectedIds: {
    type: Array,
    default: () => [],
  },
  clearing: {
    type: Boolean,
    default: false,
  },
});

// Define the emits for the component (values passed to the parent component)
const emit = defineEmits([
  "close",
  "update:selectedIds",
  "clear-all",
  "apply",
  "deleted",
]);

const deletingId = ref(null);

const localSelected = computed({
  get: () => props.selectedIds,
  set: (value) => emit("update:selectedIds", value),
});

// Define the computed property for the allSelected checkbox
const allSelected = computed({
  get() {
    return (
      props.documents.length > 0 &&
      props.selectedIds.length === props.documents.length
    );
  },
  set(checked) {
    emit(
      "update:selectedIds",
      checked ? props.documents.map((doc) => doc.id) : []
    );
  },
});

// Toggles the selection of a document
function toggleDocument(id, checked) {
  const current = new Set(props.selectedIds);
  if (checked) {
    current.add(id);
  } else {
    current.delete(id);
  }
  emit("update:selectedIds", Array.from(current));
}

function isSelected(id) {
  return props.selectedIds.includes(id);
}

// Sets the class for the status chip (e.g "queued") based on the status of the document
function statusChipClass(status) {
  return `status-chip status-${status}`;
}

async function handleDelete(docId) {
  const doc = props.documents.find((d) => d.id === docId);
  const label = doc ? doc.title || doc.file : `#${docId}`;
  if (!window.confirm(`Delete "${label}" and all of its triples? This cannot be undone.`)) {
    return;
  }
  deletingId.value = docId;
  try {
    await deleteDocument(docId);
    emit("deleted", docId);
  } catch (err) {
    const msg = err?.response?.data?.detail || err?.message || "Unknown error";
    window.alert(`Failed to delete document: ${msg}`);
  } finally {
    deletingId.value = null;
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="filter-title">
        <div class="modal-header">
          <h2 id="filter-title">Filter documents</h2>
          <button
            type="button"
            class="modal-close"
            aria-label="Close filter dialog"
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

        <div class="modal-body">
          <div v-if="!documents.length" class="document-empty">
            No documents uploaded yet.
          </div>

          <template v-else>
            <div class="document-filter-controls">
              <label class="document-check-all">
                <input v-model="allSelected" type="checkbox" />
                <span>
                  Select all ({{ selectedIds.length }}/{{ documents.length }})
                </span>
              </label>
              <button
                type="button"
                class="btn btn-danger"
                :disabled="clearing"
                @click="emit('clear-all')"
              >
                {{ clearing ? "Deleting..." : "Delete all" }}
              </button>
            </div>

            <ul class="document-checklist">
              <li v-for="doc in documents" :key="doc.id">
                <label class="document-check-item">
                  <input
                    type="checkbox"
                    :checked="isSelected(doc.id)"
                    @change="toggleDocument(doc.id, $event.target.checked)"
                  />
                  <span class="doc-title" :title="doc.title || doc.file">
                    #{{ doc.id }} · {{ doc.title || doc.file }}
                  </span>
                  <span :class="statusChipClass(doc.status)">
                    {{ doc.status }}
                  </span>
                  <button
                    type="button"
                    class="btn-icon-sm doc-delete-btn"
                    :disabled="deletingId === doc.id || clearing"
                    :title="`Delete document #${doc.id}`"
                    aria-label="Delete document"
                    @click.prevent.stop="handleDelete(doc.id)"
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
                      <path d="M3 6h18" />
                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                    </svg>
                  </button>
                </label>
              </li>
            </ul>
          </template>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn" @click="emit('close')">
            Close
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="!documents.length"
            @click="emit('apply')"
          >
            Apply &amp; refresh
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
