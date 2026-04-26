<script setup>
/**
 * Ontologies tab of the settings panel.
 *
 * - Table of ontologies with per-row enable/disable checkbox
 * - Save button performs a single bulk PATCH (sets the enabled state of all ontologies)
 * - Users can upload custom ontologies and delete custom ontologies (as .txt files)
 * - Default ontologies cannot be deleted
 */

import { computed, onMounted, ref } from "vue";

import {
  deleteOntology,
  listOntologies,
  saveOntologyEnabled,
  uploadOntology,
} from "../../services/api.js";

import ConfirmModal from "./ConfirmModal.vue";

// Define the emits for the ontologies tab component (values passed to the parent component)
const emit = defineEmits(["changed"]);

// State for the ontologies tab component
const ontologies = ref([]);              // The list of ontologies
const error = ref("");                   // The error message
const loading = ref(false);              // Whether the ontologies are loading
const saving = ref(false);               // Whether the ontologies are saving
const fileInput = ref(null);             // The file input for the upload
const uploadBusy = ref(false);           // Whether the upload is busy
const confirmTarget = ref(null);         // The target of the confirm modal (ontology to delete)
const confirmBusy = ref(false);          // Whether the confirm modal is busy (when submitting the confirm modal)

// Computed property for the ontologies tab component
// Determines if the ontologies are dirty (have changed since the initial load)
const dirty = computed(() =>
  ontologies.value.some((o) => o.is_enabled !== o.__initial)
);

// Refreshes the list of ontologies on mount
onMounted(refreshList);

// Refreshes the list of ontologies and sets the initial enabled state
async function refreshList() {
  loading.value = true;
  error.value = "";
  try {
    const list = await listOntologies();
    ontologies.value = list.map((o) => ({ ...o, __initial: o.is_enabled }));
  } catch (err) {
    error.value = extractError(err);
  } finally {
    loading.value = false;
  }
}

// Handles the submission of the save button
async function handleSave() {
  saving.value = true;
  error.value = "";
  try {
    // Get the enabled IDs of the ontologies
    const enabledIds = ontologies.value
      .filter((o) => o.is_enabled)
      .map((o) => o.id);

    // Save the enabled state of the ontologies
    const updated = await saveOntologyEnabled(enabledIds);
    // Update the ontologies with the new enabled state
    ontologies.value = updated.map((o) => ({ ...o, __initial: o.is_enabled }));
    emit("changed");
  } catch (err) {
    error.value = extractError(err);
  } finally {
    saving.value = false;
  }
}

// Triggers the file picker for the upload
function triggerFilePicker() {
  fileInput.value?.click();
}

// Handles the submission of the upload button
async function handleUpload(event) {
  // Get the file from the event
  const file = event.target.files?.[0];
  if (!file) return;
  uploadBusy.value = true;
  error.value = "";
  try {
    // Upload the ontology
    await uploadOntology(file);
    // Refresh the list of ontologies
    await refreshList();
    emit("changed");
  } catch (err) {
    error.value = extractError(err);
  } finally {
    uploadBusy.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}

// Opens the confirm modal for the delete action
function openDelete(ontology) {
  confirmTarget.value = ontology;
}

// Closes the confirm modal for the delete action
function closeConfirm() {
  if (confirmBusy.value) return;
  confirmTarget.value = null;
}

// Handles the submission of the delete button
async function runDelete() {
  if (!confirmTarget.value) return;
  confirmBusy.value = true;
  error.value = "";
  try {
    // Delete the ontology
    await deleteOntology(confirmTarget.value.id);
    // Refresh the list of ontologies
    confirmTarget.value = null;
    await refreshList();
    emit("changed");
  } catch (err) {
    error.value = extractError(err);
  } finally {
    confirmBusy.value = false;
  }
}

// Extracts the error message from the error object (API response or error message)
function extractError(err) {
  const data = err?.response?.data;
  if (!data) return err?.message || "Unknown error";
  return data.detail || err?.message || "Unknown error";
}
</script>

<template>
  <div class="settings-tab-body">
    <header class="settings-section-header">
      <div class="settings-summary-row">
        <span class="chip">
          {{ ontologies.filter((o) => o.is_enabled).length }} of {{ ontologies.length }} enabled
        </span>
      </div>

      <div class="settings-actions">
        <input
          ref="fileInput"
          type="file"
          accept=".txt"
          hidden
          @change="handleUpload"
        />
        <button
          type="button"
          class="btn btn-sm"
          :disabled="uploadBusy"
          @click="triggerFilePicker"
        >
          {{ uploadBusy ? "Uploading..." : "Upload" }}
        </button>
        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="!dirty || saving"
          @click="handleSave"
        >
          {{ saving ? "Saving..." : "Save" }}
        </button>
      </div>
    </header>

    <p v-if="error" class="form-error">{{ error }}</p>

    <div class="terms-table-wrapper">
      <table class="terms-table" v-if="ontologies.length">
        <thead>
          <tr>
            <th>Name</th>
            <th>Source</th>
            <th class="terms-table-check">Enabled</th>
            <th class="terms-table-check">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ontology in ontologies" :key="ontology.id">
            <td>{{ ontology.name }}</td>
            <td>
              <span class="chip" :class="ontology.source === 'default' ? 'chip-muted' : ''">
                {{ ontology.source }}
              </span>
            </td>
            <td class="terms-table-check">
              <input type="checkbox" v-model="ontology.is_enabled" />
            </td>
            <td class="terms-table-check">
              <button
                type="button"
                class="btn-icon-sm"
                aria-label="Delete"
                :disabled="ontology.source === 'default'"
                :title="
                  ontology.source === 'default'
                    ? 'Default ontologies cannot be deleted'
                    : 'Delete'
                "
                @click="openDelete(ontology)"
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
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="settings-empty">
        <template v-if="loading">Loading...</template>
        <template v-else>No ontologies configured.</template>
      </p>
    </div>

    <ConfirmModal
      :open="confirmTarget !== null"
      title="Delete ontology?"
      :message="confirmTarget ? `\u201c${confirmTarget.name}\u201d will be removed.` : ''"
      confirm-label="Delete"
      :danger="true"
      :busy="confirmBusy"
      @confirm="runDelete"
      @cancel="closeConfirm"
    />
  </div>
</template>
