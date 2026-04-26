<script setup>
/**
 * Modal used to create a brand-new custom label list (subject-specific).
 * Collects the list name, its entity labels (with optional descriptions),
 * and its relation labels in a single submission.
 */

import { ref, watch } from "vue";

// Define the props for the add label list modal component (values passed from the parent component)
const props = defineProps({
  open: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
});

// Define the emits for the add label list modal component (values passed to the parent component)s
const emit = defineEmits(["submit", "cancel"]);

// Label list state
const name = ref("");                                       // The name of the label list
const entityLabels = ref([{ label: "", description: "" }]); // The entity labels of the label list
const relationLabels = ref([""]);                           // The relation labels of the label list
const error = ref("");                                      // The error message of the label list

// Watch the open prop to reset the label list state when the modal is opened
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      name.value = "";
      entityLabels.value = [{ label: "", description: "" }];
      relationLabels.value = [""];
      error.value = "";
    }
  }
);

// Add an entity label to the label list
function addEntity() {
  entityLabels.value.push({ label: "", description: "" });
}

// Remove an entity label from the label list
function removeEntity(index) {
  entityLabels.value.splice(index, 1);
  if (entityLabels.value.length === 0) {
    entityLabels.value.push({ label: "", description: "" });
  }
}

// Add a relation label to the label list
function addRelation() {
  relationLabels.value.push("");
}

// Remove a relation label from the label list
function removeRelation(index) {
  relationLabels.value.splice(index, 1);
  if (relationLabels.value.length === 0) {
    relationLabels.value.push("");
  }
}

// On submit, validate the label list state and emit the submit event
function handleSubmit() {
  // Reset the error message
  error.value = "";
  const trimmedName = name.value.trim();

  // If the name is empty, set the error message and return
  if (!trimmedName) {
    error.value = "Name is required.";
    return;
  }

  // Validate the entity labels
  const entities = entityLabels.value
    .map((entry) => ({
      label: (entry.label || "").trim(),
      description: (entry.description || "").trim(),
    }))
    .filter((entry) => entry.label);
  if (entities.length === 0) {
    error.value = "Add at least one entity label.";
    return;
  }
  const entitySeen = new Set();
  for (const entry of entities) {
    if (entitySeen.has(entry.label)) {
      error.value = `Duplicate entity label: ${entry.label}`;
      return;
    }
    entitySeen.add(entry.label);
  }

  // Validate the relation labels
  const relations = relationLabels.value
    .map((label) => (label || "").trim())
    .filter(Boolean);
  if (relations.length === 0) {
    error.value = "Add at least one relation label.";
    return;
  }
  const relationSeen = new Set();
  for (const label of relations) {
    if (relationSeen.has(label)) {
      error.value = `Duplicate relation label: ${label}`;
      return;
    }
    relationSeen.add(label);
  }

  // Emit the submit event with the label list state
  emit("submit", {
    name: trimmedName,
    entity_labels: entities,
    relation_labels: relations,
  });
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="emit('cancel')">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h2>New label list</h2>
          <button
            type="button"
            class="modal-close"
            aria-label="Close"
            :disabled="busy"
            @click="emit('cancel')"
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

        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
          <label class="form-field">
            <span class="form-label">Name (subject)</span>
            <input
              v-model="name"
              type="text"
              class="form-input"
              placeholder="e.g. finance"
              :disabled="busy"
            />
          </label>

          <section class="label-builder">
            <div class="label-builder-header">
              <h3>Entity labels</h3>
              <button
                type="button"
                class="btn btn-sm"
                :disabled="busy"
                @click="addEntity"
              >
                + Add
              </button>
            </div>
            <div
              v-for="(entry, index) in entityLabels"
              :key="`entity-${index}`"
              class="label-builder-row"
            >
              <input
                v-model="entry.label"
                type="text"
                class="form-input"
                placeholder="label"
                :disabled="busy"
              />
              <input
                v-model="entry.description"
                type="text"
                class="form-input"
                placeholder="description (optional)"
                :disabled="busy"
              />
              <button
                type="button"
                class="btn-icon-sm"
                aria-label="Remove entity"
                :disabled="busy"
                @click="removeEntity(index)"
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
          </section>

          <section class="label-builder">
            <div class="label-builder-header">
              <h3>Relation labels</h3>
              <button
                type="button"
                class="btn btn-sm"
                :disabled="busy"
                @click="addRelation"
              >
                + Add
              </button>
            </div>
            <div
              v-for="(label, index) in relationLabels"
              :key="`relation-${index}`"
              class="label-builder-row"
            >
              <input
                v-model="relationLabels[index]"
                type="text"
                class="form-input"
                placeholder="label"
                :disabled="busy"
              />
              <button
                type="button"
                class="btn-icon-sm"
                aria-label="Remove relation"
                :disabled="busy"
                @click="removeRelation(index)"
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
          </section>

          <p v-if="error" class="form-error">{{ error }}</p>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn" :disabled="busy" @click="emit('cancel')">
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="busy"
            @click="handleSubmit"
          >
            {{ busy ? "Creating..." : "Create" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
