<script setup>
import { ref } from "vue";
import { uploadPdfs } from "../services/api";

const selectedFiles = ref([]);
const busy = ref(false);
const message = ref("");
const fileInput = ref(null);

const emit = defineEmits(["uploaded"]);

function onFileChange(event) {
  selectedFiles.value = Array.from(event.target.files || []);
}

async function submitUpload() {
  if (!selectedFiles.value.length || busy.value) {
    return;
  }

  busy.value = true;
  message.value = `Uploading ${selectedFiles.value.length} PDF${selectedFiles.value.length === 1 ? "" : "s"}...`;

  try {
    const payload = await uploadPdfs(selectedFiles.value);
    const uploadedDocuments = payload.documents || (payload.document ? [payload.document] : []);
    const total = uploadedDocuments.length;
    message.value =
      total === 1
        ? `Uploaded 1 document. Document #${uploadedDocuments[0].id} is processing.`
        : `Uploaded ${total} documents. Processing will start after the batch upload finishes.`;
    emit("uploaded", uploadedDocuments);
    selectedFiles.value = [];
    if (fileInput.value) {
      fileInput.value.value = "";
    }
  } catch (error) {
    message.value = error?.response?.data?.detail || "Upload failed.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="panel">
    <h2>Upload PDF(s)</h2>
    <input ref="fileInput" type="file" accept="application/pdf" multiple @change="onFileChange" />
    <button :disabled="busy || !selectedFiles.length" @click="submitUpload">
      {{ busy ? "Uploading..." : "Upload" }}
    </button>
    <p v-if="message">{{ message }}</p>
  </section>
</template>
