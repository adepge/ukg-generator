<script setup>
/* ProgressBar component
   Shows the progress of document uploads and processing.
   The tooltip is shown when the user hovers over the progress bar (or when there are documents being processed).
*/

import { computed, ref } from "vue";


// Define the props for the component (values passed from the parent component)
const props = defineProps({
  documents: {
    type: Array,
    default: () => [],
  },
});

const hovered = ref(false);

// Count the number of documents in each status
const counts = computed(() => {
  const result = { queued: 0, processing: 0, completed: 0, failed: 0, total: 0 };
  for (const doc of props.documents) {
    result.total += 1;
    if (doc.status === "queued") result.queued += 1;
    else if (doc.status === "processing") result.processing += 1;
    else if (doc.status === "completed") result.completed += 1;
    else if (doc.status === "failed") result.failed += 1;
  }
  return result;
});


// Properties for the progress bar
const finishedCount = computed(() => counts.value.completed + counts.value.failed); // The number of documents that have been processed (completed or failed)
const remaining = computed(() => counts.value.queued + counts.value.processing);    // The number of documents that are remaining to be processed (queued or processing)
const isActive = computed(() => remaining.value > 0);                               // Whether the progress bar is active (i.e. there are documents still queued to be processed)
const percent = computed(() => {                                                    // The percentage of documents that have been processed (completed or failed)
  if (counts.value.total === 0) return 0;
  return Math.round((finishedCount.value / counts.value.total) * 100);
});

const processingDocument = computed(() =>
  props.documents.find((doc) => doc.status === "processing")
);

// Summary status label for the progress bar
const statusLabel = computed(() => {
  if (isActive.value) {
    if (processingDocument.value) {
      const label =
        processingDocument.value.title ||
        getFileStem(processingDocument.value.file) ||
        `#${processingDocument.value.id}`;
      return `Processing: ${label}`;
    }
    return "Queued for processing...";
  }
  if (counts.value.total === 0) {
    return "No documents uploaded yet.";
  }
  if (counts.value.failed > 0) {
    return `All documents processed (${counts.value.failed} failed).`;
  }
  return "All documents processed.";
});

// Get the stem of a file path 
// Example: "path/to/interesting_file.txt" -> "interesting_file"
function getFileStem(file) {
  if (!file) return "";
  const parts = file.split("/");
  const filename = parts[parts.length - 1];
  const stem = filename.split(".").shift();
  return stem || filename;
}
</script>

<template>
  <div
    class="progress-edge"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div
      class="progress-edge-track"
      role="progressbar"
      :aria-valuenow="percent"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div
        class="progress-edge-fill"
        :class="{ active: isActive }"
        :style="{ width: `${percent}%` }"
      ></div>
    </div>

    <Transition name="progress-tooltip">
      <div v-if="hovered || (isActive && counts.total > 0)" class="progress-tooltip">
        <div class="progress-tooltip-header">
          <span class="progress-tooltip-title">Generation progress</span>
          <span class="progress-tooltip-percent">{{ percent }}%</span>
        </div>
        <div class="progress-tooltip-stats">
          <span>{{ finishedCount }} / {{ counts.total }} documents</span>
          <span v-if="counts.processing > 0" class="status-chip status-processing">
            {{ counts.processing }} processing
          </span>
          <span v-if="counts.queued > 0" class="status-chip status-queued">
            {{ counts.queued }} queued
          </span>
          <span v-if="counts.completed > 0" class="status-chip status-completed">
            {{ counts.completed }} completed
          </span>
          <span v-if="counts.failed > 0" class="status-chip status-failed">
            {{ counts.failed }} failed
          </span>
        </div>
        <p class="progress-tooltip-status">
          Note: Each document may take up to 60 seconds to process
        </p>
        <p class="progress-tooltip-status">{{ statusLabel }}</p>
      </div>
    </Transition>
  </div>
</template>
