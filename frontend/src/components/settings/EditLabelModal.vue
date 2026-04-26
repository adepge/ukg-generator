<script setup>
/**
 * Modal that edits (or creates) a single entity/relation label inside a
 * LabelList. When `kind === "relation"` the description field is hidden.
 */

import { computed, ref, watch } from "vue";

// Define the props for the edit label modal component (values passed from the parent component)
const props = defineProps({
  open: { type: Boolean, default: false },
  mode: {
    type: String,
    default: "edit", // "edit" | "create"
  },
  kind: {
    type: String,
    default: "entity", // "entity" | "relation"
  },
  initialLabel: { type: String, default: "" },
  initialDescription: { type: String, default: "" },
  busy: { type: Boolean, default: false },
});

// Define the emits for the edit label modal component (values passed to the parent component)
const emit = defineEmits(["submit", "cancel"]);

// State for the edit label modal component
const label = ref("");
const description = ref("");
const error = ref("");

// Used to determine the title of the edit label modal
const title = computed(() => {
  const subject = props.kind === "entity" ? "entity label" : "relation label";
  return props.mode === "create" ? `New ${subject}` : `Edit ${subject}`;
});

// Watch the open prop to reset the label state when the modal is opened
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      label.value = props.initialLabel || "";
      description.value = props.initialDescription || "";
      error.value = "";
    }
  }
);

// On submit, validate the label state and emit the submit event
function handleSubmit() {
  const trimmedLabel = label.value.trim();
  if (!trimmedLabel) {
    error.value = "Label is required.";
    return;
  }
  const payload = { label: trimmedLabel };
  if (props.kind === "entity") {
    payload.description = description.value.trim();
  }
  emit("submit", payload);
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="emit('cancel')">
      <div class="modal modal-sm" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h2>{{ title }}</h2>
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

        <div class="modal-body">
          <label class="form-field">
            <span class="form-label">Label</span>
            <input
              v-model="label"
              type="text"
              class="form-input"
              placeholder="e.g. disease"
              :disabled="busy"
              @keyup.enter="handleSubmit"
            />
          </label>

          <label v-if="kind === 'entity'" class="form-field">
            <span class="form-label">Description (optional)</span>
            <textarea
              v-model="description"
              class="form-input"
              rows="3"
              placeholder="How should the extractor interpret this entity?"
              :disabled="busy"
            />
          </label>

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
            {{ busy ? "Saving..." : "Save" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
