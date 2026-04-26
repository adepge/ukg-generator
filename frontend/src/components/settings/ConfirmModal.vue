<script setup>
/**
 * Reusable "Are you sure?" modal used by destructive settings actions
 * (reset, delete, disable).
 */

 // Define the props for the confirm modal component (values passed from the parent component)
const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: "Are you sure?" },
  message: { type: String, default: "" },
  confirmLabel: { type: String, default: "Confirm" },
  cancelLabel: { type: String, default: "Cancel" },
  danger: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
});

// Define the emits for the confirm modal component (values passed to the parent component)
const emit = defineEmits(["confirm", "cancel"]);

// On cancel, if the busy state is true, return
function handleCancel() {
  if (props.busy) return;
  emit("cancel");
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="handleCancel">
      <div class="modal modal-sm" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h2>{{ title }}</h2>
          <button
            type="button"
            class="modal-close"
            aria-label="Close"
            :disabled="busy"
            @click="handleCancel"
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
          <p v-if="message" class="confirm-message">{{ message }}</p>
          <slot />
        </div>

        <div class="modal-footer">
          <button type="button" class="btn" :disabled="busy" @click="handleCancel">
            {{ cancelLabel }}
          </button>
          <button
            type="button"
            class="btn"
            :class="danger ? 'btn-danger' : 'btn-primary'"
            :disabled="busy"
            @click="emit('confirm')"
          >
            {{ busy ? "Working..." : confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
