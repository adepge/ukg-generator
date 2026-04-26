<script setup>
/**
 * Blacklists tab of the settings panel.
 *
 * - Dropdown of all blacklists
 * - Category filter dropdown + search over terms by text
 * - Term table with exact_match / subject / object checkboxes (patches the term when changed)
 * - Functions: 
 *     - Upload a CSV file to create a new blacklist
 *     - Download the current blacklist as a CSV file
 *     - Enable/Disable the current blacklist
 *     - Delete the current blacklist (default blacklist cannot be deleted)
 *     - Reset the current blacklist to its original state
 */

import { computed, onMounted, ref, watch } from "vue";

import {
  blacklistDownloadUrl,
  deleteBlacklist,
  getBlacklist,
  listBlacklists,
  listBlacklistTerms,
  resetBlacklist,
  toggleBlacklist,
  updateBlacklistTerm,
  uploadBlacklist,
} from "../../services/api.js";

import ConfirmModal from "./ConfirmModal.vue";

const emit = defineEmits(["changed"]);

// ----- state -----
const blacklists = ref([]);
const selectedId = ref(null);
const selectedDetail = ref(null);
const terms = ref([]);
const termCount = ref(0);
const categoryFilter = ref("");
const searchTerm = ref("");
const loading = ref(false);
const error = ref("");

const fileInput = ref(null);
const uploadBusy = ref(false);
const confirmTarget = ref(null); // { kind: 'reset'|'delete'|'disable' }
const confirmBusy = ref(false);

// Server-side paginated term list parameters.
const TERM_PAGE_LIMIT = 1000;
const offset = ref(0);

const selected = computed(() =>
  blacklists.value.find((bl) => bl.id === selectedId.value) || null
);

const isDefault = computed(() => selected.value?.is_default === true);

watch(searchTerm, debounce(loadTerms, 250));
watch(categoryFilter, () => {
  offset.value = 0;
  loadTerms();
});

onMounted(async () => {
  await refreshList();
});

function debounce(fn, wait) {
  let t = null;
  return (...args) => {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

async function refreshList() {
  loading.value = true;
  error.value = "";
  try {
    const list = await listBlacklists();
    blacklists.value = list;
    if (!selectedId.value && list.length) {
      selectedId.value = list[0].id;
    } else if (selectedId.value && !list.some((bl) => bl.id === selectedId.value)) {
      selectedId.value = list[0]?.id ?? null;
    }
    await loadDetail();
    await loadTerms();
  } catch (err) {
    error.value = extractError(err);
  } finally {
    loading.value = false;
  }
}

async function loadDetail() {
  if (!selectedId.value) {
    selectedDetail.value = null;
    return;
  }
  try {
    selectedDetail.value = await getBlacklist(selectedId.value);
    categoryFilter.value = "";
    offset.value = 0;
  } catch (err) {
    error.value = extractError(err);
  }
}

async function loadTerms() {
  if (!selectedId.value) {
    terms.value = [];
    termCount.value = 0;
    return;
  }
  try {
    const params = {
      limit: TERM_PAGE_LIMIT,
      offset: offset.value,
    };
    if (categoryFilter.value) params.category = categoryFilter.value;
    if (searchTerm.value.trim()) params.q = searchTerm.value.trim();
    const data = await listBlacklistTerms(selectedId.value, params);
    terms.value = data.results;
    termCount.value = data.count;
  } catch (err) {
    error.value = extractError(err);
  }
}

async function handleSelect(id) {
  selectedId.value = id;
  offset.value = 0;
  searchTerm.value = "";
  categoryFilter.value = "";
  await loadDetail();
  await loadTerms();
}

async function handleFieldChange(term, field) {
  // Optimistic update: the v-model has already flipped the local value.
  try {
    const patch = { [field]: term[field] };
    const updated = await updateBlacklistTerm(selectedId.value, term.id, patch);
    Object.assign(term, updated);
  } catch (err) {
    // Revert on failure.
    term[field] = !term[field];
    error.value = extractError(err);
  }
}

async function handleUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  uploadBusy.value = true;
  error.value = "";
  try {
    const created = await uploadBlacklist(file);
    await refreshList();
    selectedId.value = created.id;
    await loadDetail();
    await loadTerms();
    emit("changed");
  } catch (err) {
    error.value = extractError(err);
  } finally {
    uploadBusy.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}

function triggerFilePicker() {
  fileInput.value?.click();
}

function handleDownload() {
  if (!selectedId.value) return;
  window.open(blacklistDownloadUrl(selectedId.value), "_blank");
}

function openConfirm(kind) {
  confirmTarget.value = { kind };
}

function closeConfirm() {
  if (confirmBusy.value) return;
  confirmTarget.value = null;
}

async function runConfirm() {
  if (!confirmTarget.value || !selected.value) return;
  const kind = confirmTarget.value.kind;
  confirmBusy.value = true;
  error.value = "";
  try {
    if (kind === "reset") {
      await resetBlacklist(selected.value.id);
      await loadTerms();
    } else if (kind === "delete") {
      await deleteBlacklist(selected.value.id);
      selectedId.value = null;
      await refreshList();
      emit("changed");
    } else if (kind === "disable") {
      await toggleBlacklist(selected.value.id, false);
      await refreshList();
      emit("changed");
    }
    confirmTarget.value = null;
  } catch (err) {
    error.value = extractError(err);
  } finally {
    confirmBusy.value = false;
  }
}

async function handleToggleClick() {
  if (!selected.value) return;
  if (selected.value.is_enabled) {
    openConfirm("disable");
    return;
  }

  // Enabling doesn't need a confirmation, so toggle directly without
  // touching confirmTarget (which would briefly flash the modal).
  error.value = "";
  try {
    await toggleBlacklist(selected.value.id, true);
    await refreshList();
    emit("changed");
  } catch (err) {
    error.value = extractError(err);
  }
}

function extractError(err) {
  const data = err?.response?.data;
  if (!data) return err?.message || "Unknown error";
  if (Array.isArray(data.errors) && data.errors.length) {
    return data.errors.join(" \u2022 ");
  }
  return data.detail || err.message || "Unknown error";
}

const confirmCopy = computed(() => {
  if (!confirmTarget.value) return { title: "", message: "", confirmLabel: "", danger: false };
  if (confirmTarget.value.kind === "reset") {
    return {
      title: "Reset blacklist?",
      message:
        "Every term in this blacklist will be returned to its originally-seeded values. Your current overrides will be lost.",
      confirmLabel: "Reset",
      danger: true,
    };
  }
  if (confirmTarget.value.kind === "delete") {
    return {
      title: "Delete blacklist?",
      message: `"${selected.value?.name}" and all of its terms will be removed.`,
      confirmLabel: "Delete",
      danger: true,
    };
  }
  if (confirmTarget.value.kind === "disable") {
    return {
      title: "Disable blacklist?",
      message: `"${selected.value?.name}" will be skipped by future pipeline runs until re-enabled.`,
      confirmLabel: "Disable",
      danger: false,
    };
  }
  return { title: "", message: "", confirmLabel: "", danger: false };
});
</script>

<template>
  <div class="settings-tab-body">
    <header class="settings-section-header">
      <div class="settings-filters">
        <label class="form-field form-field-inline">
          <span class="form-label-sm">Blacklist</span>
          <select
            class="form-input"
            :value="selectedId"
            @change="handleSelect(Number($event.target.value))"
          >
            <option v-for="bl in blacklists" :key="bl.id" :value="bl.id">
              {{ bl.name }}
              <template v-if="bl.is_default">(default)</template>
              <template v-else-if="!bl.is_enabled"> (disabled)</template>
            </option>
          </select>
        </label>

        <label class="form-field form-field-inline">
          <span class="form-label-sm">Category</span>
          <select v-model="categoryFilter" class="form-input">
            <option value="">All</option>
            <option
              v-for="cat in selectedDetail?.categories || []"
              :key="cat || 'uncategorized'"
              :value="cat"
            >
              {{ cat || "(none)" }}
            </option>
          </select>
        </label>

        <label class="form-field form-field-inline form-field-grow">
          <span class="form-label-sm">Search</span>
          <input
            v-model="searchTerm"
            type="search"
            class="form-input"
            placeholder="Filter terms..."
          />
        </label>
      </div>

      <div class="settings-actions">
        <input
          ref="fileInput"
          type="file"
          accept=".csv"
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
          class="btn btn-sm"
          :disabled="!selected"
          @click="handleDownload"
        >
          Download
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :disabled="!selected || isDefault"
          @click="handleToggleClick"
        >
          {{ selected?.is_enabled ? "Disable" : "Enable" }}
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :disabled="!selected"
          @click="openConfirm('reset')"
        >
          Reset
        </button>
        <button
          type="button"
          class="btn btn-sm btn-danger"
          :disabled="!selected || isDefault"
          @click="openConfirm('delete')"
        >
          Delete
        </button>
      </div>
    </header>

    <p v-if="error" class="form-error">{{ error }}</p>

    <div class="settings-summary-row">
      <span v-if="selected" class="chip">
        {{ terms.length }} of {{ termCount }} terms
      </span>
      <span v-if="selected" class="chip" :class="{ 'chip-muted': !selected.is_enabled }">
        {{ selected.is_enabled ? "Enabled" : "Disabled" }}
      </span>
      <span v-if="selected" class="chip">{{ selected.source }}</span>
    </div>

    <div class="terms-table-wrapper" :class="{ loading }">
      <table class="terms-table" v-if="terms.length">
        <thead>
          <tr>
            <th class="terms-table-term">Term</th>
            <th class="terms-table-check" title="Exact match (`excl_only` in CSV) when on, substring (`excl`) when off">
              Exact match
            </th>
            <th class="terms-table-check">Subject</th>
            <th class="terms-table-check">Object</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="term in terms" :key="term.id">
            <td class="terms-table-term">
              <span class="term-label">{{ term.term }}</span>
              <span v-if="term.category" class="term-chip">{{ term.category }}</span>
            </td>
            <td class="terms-table-check">
              <input
                type="checkbox"
                v-model="term.exact_match"
                @change="handleFieldChange(term, 'exact_match')"
              />
            </td>
            <td class="terms-table-check">
              <input
                type="checkbox"
                v-model="term.subject"
                @change="handleFieldChange(term, 'subject')"
              />
            </td>
            <td class="terms-table-check">
              <input
                type="checkbox"
                v-model="term.object"
                @change="handleFieldChange(term, 'object')"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="settings-empty">
        <template v-if="loading">Loading...</template>
        <template v-else>No terms match the current filter.</template>
      </p>
    </div>

    <ConfirmModal
      :open="confirmTarget !== null"
      :title="confirmCopy.title"
      :message="confirmCopy.message"
      :confirm-label="confirmCopy.confirmLabel"
      :danger="confirmCopy.danger"
      :busy="confirmBusy"
      @confirm="runConfirm"
      @cancel="closeConfirm"
    />
  </div>
</template>
