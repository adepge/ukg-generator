<script setup>
import { ref } from "vue";
import { uploadPdf } from "../services/api";

const selectedFile = ref(null);
const busy = ref(false);
const message = ref("");

const emit = defineEmits(["uploaded"]);

function onFileChange(event) {
  const [file] = event.target.files || [];
  selectedFile.value = file || null;
}

async function submitUpload() {
  if (!selectedFile.value || busy.value) {
    return;
  }
  busy.value = true;
  message.value = "";
  try {
    const payload = await uploadPdf(selectedFile.value);
    message.value = `Uploaded. Document #${payload.document.id} is processing.`;
    emit("uploaded", payload.document);
  } catch (error) {
    message.value = error?.response?.data?.detail || "Upload failed.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="panel">
    <h2>Upload PDF</h2>
    <input type="file" accept="application/pdf" @change="onFileChange" />
    <button :disabled="busy || !selectedFile" @click="submitUpload">
      {{ busy ? "Uploading..." : "Upload" }}
    </button>
    <p v-if="message">{{ message }}</p>
  </section>
</template>
