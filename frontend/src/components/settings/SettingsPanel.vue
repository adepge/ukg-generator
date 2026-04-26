<script setup>
/**
 * Right-hand side settings panel hosting the Blacklists / Labels / Ontologies
 * tabs. The panel is a full-height drawer that slides in from the right.
 * Emits `changed` whenever any sub-tab performs a mutation that can affect
 * the toolbar summary, so the parent can refresh the summary chips.
 */

import { ref, watch } from "vue";

import BlacklistsTab from "./BlacklistsTab.vue";
import LabelsTab from "./LabelsTab.vue";
import OntologiesTab from "./OntologiesTab.vue";

// Define the props for the settings panel component
const props = defineProps({
  open: { type: Boolean, default: false },
});

// Define the emits for the settings panel component
const emit = defineEmits(["close", "changed"]);

// Define the tabs for the settings panel component
const TABS = [
  { id: "blacklists", label: "Blacklists" },
  { id: "labels", label: "Labels" },
  { id: "ontologies", label: "Ontologies" },
];

// State for the settings panel component (defaults to the blacklists tab on open)
const activeTab = ref("blacklists"); // The active tab

// Watch the open prop to set the active tab to the blacklists tab on open
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      activeTab.value = "blacklists";
    }
  }
);

// Handles the keydown event (closes the settings panel on Escape key)
function handleKeydown(event) {
  if (event.key === "Escape") emit("close");
}
</script>

<template>
  <Teleport to="body">
    <transition name="settings-panel">
      <div
        v-if="open"
        class="settings-panel-backdrop"
        @click.self="emit('close')"
        @keydown="handleKeydown"
      >
        <aside
          class="settings-panel"
          role="dialog"
          aria-label="Settings"
          aria-modal="true"
          tabindex="-1"
        >
          <header class="settings-panel-header">
            <h2>Settings</h2>
            <button
              type="button"
              class="modal-close"
              aria-label="Close settings"
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
          </header>

          <nav class="settings-tabs" role="tablist">
            <button
              v-for="tab in TABS"
              :key="tab.id"
              type="button"
              class="settings-tab"
              :class="{ active: activeTab === tab.id }"
              role="tab"
              :aria-selected="activeTab === tab.id"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </nav>

          <section class="settings-panel-body">
            <BlacklistsTab
              v-if="activeTab === 'blacklists'"
              @changed="emit('changed')"
            />
            <LabelsTab
              v-else-if="activeTab === 'labels'"
              @changed="emit('changed')"
            />
            <OntologiesTab
              v-else-if="activeTab === 'ontologies'"
              @changed="emit('changed')"
            />
          </section>
        </aside>
      </div>
    </transition>
  </Teleport>
</template>
