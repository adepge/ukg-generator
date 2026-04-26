<script setup>
import { ref } from "vue";
import { uploadPdfs } from "../services/api";

// Define the props for the upload modal component (values passed from the parent component)
const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
});

// Define the emits for the upload modal component (values passed to the parent component)
const emit = defineEmits(["close", "uploaded"]);

// State for the upload modal component
const selectedFiles = ref([]);
const dragging = ref(false);
const busy = ref(false);
const message = ref("");
const fileInput = ref(null);

// Adds files to the selected files list
function addFiles(files) {
  // Ensure only PDF files are added
  const accepted = Array.from(files || []).filter(
    (file) =>
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf")
  );

  // If no accepted files, return
  if (!accepted.length) {
    return;
  }

  // Add the accepted files to the selected files list
  const existingKeys = new Set(
    selectedFiles.value.map((f) => `${f.name}:${f.size}`)
  );
  for (const file of accepted) {
    const key = `${file.name}:${file.size}`;
    if (!existingKeys.has(key)) {
      selectedFiles.value.push(file);
      existingKeys.add(key);
    }
  }
}

// On file input change, add the files to the selected files list
function onFileInputChange(event) {
  addFiles(event.target.files);
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

// On drop, add the files to the selected files list
function onDrop(event) {
  dragging.value = false;
  addFiles(event.dataTransfer?.files);
}

// On drag over, set the dragging state to true (highlight the dropzone)
function onDragOver() {
  dragging.value = true;
}

// On drag leave, set the dragging state to false (remove the highlight from the dropzone)
function onDragLeave() {
  dragging.value = false;
}

// On remove file, remove the file from the selected files list
function removeFile(index) {
  selectedFiles.value.splice(index, 1);
}

// On pick files, open the file input
function pickFiles() {
  fileInput.value?.click();
}

// On close modal, reset the selected files, message and emit the close event
function closeModal() {
  if (busy.value) return;
  selectedFiles.value = [];
  message.value = "";
  emit("close");
}

// On submit upload, upload the selected files and emit the uploaded event
async function submitUpload() {
  if (!selectedFiles.value.length || busy.value) {
    return;
  }
  busy.value = true;
  message.value = `Uploading ${selectedFiles.value.length} PDF${
    selectedFiles.value.length === 1 ? "" : "s"
  }...`;

  try {
    // Upload all files from the selected files list
    const payload = await uploadPdfs(selectedFiles.value);
    const uploadedDocuments =
      payload.documents || (payload.document ? [payload.document] : []);
    const total = uploadedDocuments.length;

    // Set the message to the number of documents uploaded
    message.value =
      total === 1
        ? `Uploaded 1 document. Processing has started.`
        : `Uploaded ${total} documents. Processing will begin shortly.`;
    emit("uploaded", uploadedDocuments);
    selectedFiles.value = [];
    
    // Close the modal after 900ms
    setTimeout(() => {
      if (!busy.value) {
        closeModal();
      }
    }, 900);
  } catch (error) {
    message.value = error?.response?.data?.detail || "Upload failed.";
  } finally {
    busy.value = false;
  }
}

// Formats the size of a file to a human readable string (bytes, KB, MB)
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="closeModal">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title">
        <div class="modal-header">
          <h2 id="upload-title">Upload documents</h2>
          <button
            type="button"
            class="modal-close"
            aria-label="Close upload dialog"
            @click="closeModal"
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
          <div
            class="dropzone"
            :class="{ dragging }"
            @click="pickFiles"
            @dragover.prevent="onDragOver"
            @dragenter.prevent="onDragOver"
            @dragleave.prevent="onDragLeave"
            @drop.prevent="onDrop"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <div class="dropzone-title">
              Drop PDFs here or click to browse
            </div>
            <div class="dropzone-hint">
              PDF files only. You can select multiple files at once.
            </div>
            <input
              ref="fileInput"
              type="file"
              accept="application/pdf"
              multiple
              @change="onFileInputChange"
            />
          </div>

          <ul v-if="selectedFiles.length" class="file-list">
            <li v-for="(file, index) in selectedFiles" :key="`${file.name}-${index}`">
              <span>{{ file.name }}</span>
              <span style="display: flex; align-items: center; gap: 8px;">
                <span style="color: var(--color-text-subtle); font-size: 12px;">{{
                  formatSize(file.size)
                }}</span>
                <button
                  type="button"
                  class="file-remove"
                  :disabled="busy"
                  aria-label="Remove file"
                  @click="removeFile(index)"
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
              </span>
            </li>
          </ul>

          <p v-if="message" class="upload-message">{{ message }}</p>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn" :disabled="busy" @click="closeModal">
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="busy || !selectedFiles.length"
            @click="submitUpload"
          >
            {{ busy ? "Uploading..." : `Upload ${selectedFiles.length || ""}`.trim() }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
