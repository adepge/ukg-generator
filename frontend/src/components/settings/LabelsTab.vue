<script setup>
/**
 * Labels tab of the settings panel.
 *
 * - Dropdown of all label lists and also displays the active badge for the currently selected one (used by the pipeline)
 * - Allows the user to edit and delete entity and relation labels
 * - Default label lists cannot be deleted
 * - However only default label lists can be reset to their original state
 * - Allows the user to create new custom label lists
 */

import { computed, onMounted, ref } from "vue";

import {
  activateLabelList,
  createEntityLabel,
  createLabelList,
  createRelationLabel,
  deleteEntityLabel,
  deleteLabelList,
  deleteRelationLabel,
  getLabelList,
  listLabelLists,
  resetLabelList,
  updateEntityLabel,
  updateRelationLabel,
} from "../../services/api.js";

import AddLabelListModal from "./AddLabelListModal.vue";
import ConfirmModal from "./ConfirmModal.vue";
import EditLabelModal from "./EditLabelModal.vue";


// Define the emits for the labels tab component (values passed to the parent component)
const emit = defineEmits(["changed"]);

// State for the labels tab component
const labelLists = ref([]);    // The list of label lists
const selectedId = ref(null);  // The id of the selected label list (dropdown selection)
const detail = ref(null);      // The detail of the selected label list
const error = ref("");
const loading = ref(false);

const addOpen = ref(false);       // Whether the add label list modal is open
const addBusy = ref(false);       // Whether the add label list modal is busy (when submitting the new label list)

const editTarget = ref(null);     // The target of the edit label modal (kind: entity or relation, mode: edit or create, payload: the label or relation)
const editBusy = ref(false);      // Whether the edit label modal is busy (when submitting the edit label)

const confirmTarget = ref(null);  // The target of the confirm modal (kind: delete-entity, delete-relation, reset, delete-list)
const confirmBusy = ref(false);   // Whether the confirm modal is busy (when submitting the confirm modal)

// Computed properties for the labels tab component
const selected = computed(
  () => labelLists.value.find((list) => list.id === selectedId.value) || null
);
const isDefault = computed(() => selected.value?.source === "default");

onMounted(refreshList);

// Refreshes the list of label lists
async function refreshList(preserveId = true) {
  loading.value = true;
  error.value = "";
  try {
    const list = await listLabelLists();
    labelLists.value = list;

    // If the selected id is not in the list, or the preserveId flag is false, set the selected id to the active label list or the first label list
    if (!preserveId || !selectedId.value || !list.some((ll) => ll.id === selectedId.value)) {
      const active = list.find((ll) => ll.is_active);
      selectedId.value = active?.id ?? list[0]?.id ?? null;
    }
    await loadDetail();
  } catch (err) {
    error.value = extractError(err);
  } finally {
    loading.value = false;
  }
}

// Loads the detail of the selected label list
async function loadDetail() {
  if (!selectedId.value) {
    detail.value = null;
    return;
  }
  try {
    detail.value = await getLabelList(selectedId.value);
  } catch (err) {
    error.value = extractError(err);
  }
}

// Handles the selection of a label list from the dropdown
async function handleSelect(id) {
  selectedId.value = id;
  await loadDetail();
}

// Handles the activation of a label list
async function handleActivate() {
  if (!selected.value) return;
  try {
    await activateLabelList(selected.value.id);
    await refreshList();
    emit("changed");
  } catch (err) {
    error.value = extractError(err);
  }
}

// Opens the add label list modal
function openAddModal() {
  addOpen.value = true;
}

// Handles the submission of a new label list
async function handleAddSubmit(payload) {
  addBusy.value = true;
  error.value = "";
  try {
    const created = await createLabelList(payload);
    addOpen.value = false;
    selectedId.value = created.id;
    await refreshList();
    emit("changed");
  } catch (err) {
    error.value = extractError(err);
  } finally {
    addBusy.value = false;
  }
}

// Opens the edit entity label modal
function openEditEntity(entity) {
  editTarget.value = {
    kind: "entity",
    mode: "edit",
    payload: entity,
  };
}

// Opens the create entity label modal
function openCreateEntity() {
  editTarget.value = {
    kind: "entity",
    mode: "create",
    payload: null,
  };
}

// Opens the edit relation label modal
function openEditRelation(relation) {
  editTarget.value = {
    kind: "relation",
    mode: "edit",
    payload: relation,
  };
}

// Opens the create relation label modal
function openCreateRelation() {
  editTarget.value = {
    kind: "relation",
    mode: "create",
    payload: null,
  };
}

// Handles the submission of an edit label
async function handleEditSubmit(payload) {
  if (!editTarget.value || !detail.value) return;
  editBusy.value = true;
  error.value = "";
  try {
    const { kind, mode, payload: current } = editTarget.value;

    // Determine the request to submit based on the kind and mode
    if (kind === "entity") {
      if (mode === "create") {
        await createEntityLabel(detail.value.id, payload);
      } else {
        await updateEntityLabel(detail.value.id, current.id, payload);
      }
    } else if (kind === "relation") {
      if (mode === "create") {
        await createRelationLabel(detail.value.id, payload);
      } else {
        await updateRelationLabel(detail.value.id, current.id, payload);
      }
    }
    editTarget.value = null;
    await loadDetail();
  } catch (err) {
    error.value = extractError(err);
  } finally {
    editBusy.value = false;
  }
}

// Opens the confirm modal
function openConfirm(kind, payload = null) {
  confirmTarget.value = { kind, payload };
}

// Closes the confirm modal
function closeConfirm() {
  if (confirmBusy.value) return;
  confirmTarget.value = null;
}

// Handles the submission of a confirm modal
async function runConfirm() {
  if (!confirmTarget.value || !detail.value) return;
  const { kind, payload } = confirmTarget.value;
  confirmBusy.value = true;
  error.value = "";
  try {
    // Determine the request to submit based on the kind
    if (kind === "delete-entity") {
      await deleteEntityLabel(detail.value.id, payload.id);
      await loadDetail();
    } else if (kind === "delete-relation") {
      await deleteRelationLabel(detail.value.id, payload.id);
      await loadDetail();
    } else if (kind === "reset") {
      await resetLabelList(detail.value.id);
      await loadDetail();
    } else if (kind === "delete-list") {
      await deleteLabelList(detail.value.id);
      selectedId.value = null;
      await refreshList(false);
      emit("changed");
    }
    confirmTarget.value = null;
  } catch (err) {
    error.value = extractError(err);
  } finally {
    confirmBusy.value = false;
  }
}

// Extracts the error message from the error object
function extractError(err) {
  const data = err?.response?.data;
  if (!data) return err?.message || "Unknown error";
  return data.detail || err?.message || "Unknown error";
}

// Computed property for the confirm modal
// Determines the title, message, confirm label and danger based on the kind of the confirm modal
const confirmCopy = computed(() => {
  if (!confirmTarget.value) return { title: "", message: "", confirmLabel: "" };
  if (confirmTarget.value.kind === "delete-entity") {
    return {
      title: "Delete entity label?",
      message: `"${confirmTarget.value.payload.label}" will be removed from this label list.`,
      confirmLabel: "Delete",
      danger: true,
    };
  }
  if (confirmTarget.value.kind === "delete-relation") {
    return {
      title: "Delete relation label?",
      message: `"${confirmTarget.value.payload.label}" will be removed from this label list.`,
      confirmLabel: "Delete",
      danger: true,
    };
  }
  if (confirmTarget.value.kind === "reset") {
    return {
      title: "Reset label list?",
      message: "All entity and relation labels will be restored to their original values.",
      confirmLabel: "Reset",
      danger: true,
    };
  }
  if (confirmTarget.value.kind === "delete-list") {
    return {
      title: "Delete label list?",
      message: `"${detail.value?.name}" and all of its labels will be removed.`,
      confirmLabel: "Delete",
      danger: true,
    };
  }
  return { title: "", message: "", confirmLabel: "" };
});

// Computed property for the edit label modal
// Determines the initial label and description based on the kind and mode of the edit label modal
const editModalInitial = computed(() => {
  if (!editTarget.value || editTarget.value.mode !== "edit") {
    return { label: "", description: "" };
  }
  const payload = editTarget.value.payload || {};
  return {
    label: payload.label || "",
    description: payload.description || "",
  };
});
</script>

<template>
  <div class="settings-tab-body">
    <header class="settings-section-header">
      <div class="settings-filters">
        <label class="form-field form-field-inline form-field-grow">
          <span class="form-label-sm">Label list</span>
          <select
            class="form-input"
            :value="selectedId"
            @change="handleSelect(Number($event.target.value))"
          >
            <option v-for="ll in labelLists" :key="ll.id" :value="ll.id">
              {{ ll.name }}
              <template v-if="ll.is_active"> (active)</template>
              <template v-if="ll.source === 'custom'"> (custom)</template>
            </option>
          </select>
        </label>
      </div>

      <div class="settings-actions">
        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="!selected || selected.is_active"
          @click="handleActivate"
        >
          Use this label list
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :disabled="!selected || !isDefault"
          @click="openConfirm('reset')"
        >
          Reset to default
        </button>
        <button type="button" class="btn btn-sm" @click="openAddModal">
          New label list
        </button>
        <button
          type="button"
          class="btn btn-sm btn-danger"
          :disabled="!selected || isDefault"
          @click="openConfirm('delete-list')"
        >
          Delete list
        </button>
      </div>
    </header>

    <p v-if="error" class="form-error">{{ error }}</p>

    <div class="label-grid" v-if="detail">
      <section class="label-card">
        <header class="label-card-header">
          <h3>Entity labels</h3>
          <button type="button" class="btn btn-sm" @click="openCreateEntity">
            + Add
          </button>
        </header>
        <ul class="label-list">
          <li v-for="entity in detail.entity_labels" :key="entity.id" class="label-list-item">
            <div class="label-list-text">
              <span class="label-list-label">{{ entity.label }}</span>
              <span v-if="entity.description" class="label-list-desc">
                {{ entity.description }}
              </span>
            </div>
            <div class="label-list-actions">
              <button
                type="button"
                class="btn-icon-sm"
                aria-label="Edit"
                @click="openEditEntity(entity)"
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
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
                </svg>
              </button>
              <button
                type="button"
                class="btn-icon-sm"
                aria-label="Delete"
                @click="openConfirm('delete-entity', entity)"
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
            </div>
          </li>
          <li v-if="!detail.entity_labels.length" class="settings-empty">
            No entity labels yet.
          </li>
        </ul>
      </section>

      <section class="label-card">
        <header class="label-card-header">
          <h3>Relation labels</h3>
          <button type="button" class="btn btn-sm" @click="openCreateRelation">
            + Add
          </button>
        </header>
        <ul class="label-list">
          <li v-for="relation in detail.relation_labels" :key="relation.id" class="label-list-item">
            <div class="label-list-text">
              <span class="label-list-label">{{ relation.label }}</span>
            </div>
            <div class="label-list-actions">
              <button
                type="button"
                class="btn-icon-sm"
                aria-label="Edit"
                @click="openEditRelation(relation)"
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
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
                </svg>
              </button>
              <button
                type="button"
                class="btn-icon-sm"
                aria-label="Delete"
                @click="openConfirm('delete-relation', relation)"
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
            </div>
          </li>
          <li v-if="!detail.relation_labels.length" class="settings-empty">
            No relation labels yet.
          </li>
        </ul>
      </section>
    </div>

    <p v-else class="settings-empty">Loading...</p>

    <AddLabelListModal
      :open="addOpen"
      :busy="addBusy"
      @submit="handleAddSubmit"
      @cancel="addOpen = false"
    />

    <EditLabelModal
      :open="editTarget !== null"
      :mode="editTarget?.mode || 'edit'"
      :kind="editTarget?.kind || 'entity'"
      :initial-label="editModalInitial.label"
      :initial-description="editModalInitial.description"
      :busy="editBusy"
      @submit="handleEditSubmit"
      @cancel="editTarget = null"
    />

    <ConfirmModal
      :open="confirmTarget !== null"
      :title="confirmCopy.title"
      :message="confirmCopy.message"
      :confirm-label="confirmCopy.confirmLabel || 'Confirm'"
      :danger="confirmCopy.danger || false"
      :busy="confirmBusy"
      @confirm="runConfirm"
      @cancel="closeConfirm"
    />
  </div>
</template>
