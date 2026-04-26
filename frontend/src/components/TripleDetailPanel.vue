<script setup>
import { computed } from "vue";

// Define the props for the triple detail panel component (values passed from the parent component)
const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
  detail: {
    type: Object,
    default: null,
  },
});

// Define the emits for the triple detail panel component (values passed to the parent component)
const emit = defineEmits(["close"]);

// Formats the confidence value to a string (2 decimal places)
function formatConfidence(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";
  return n.toFixed(2);
}

// Formats the date value to a string (medium date and short time)
function formatDate(value) {
  if (!value) return "N/A";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// Formats the document label to a string (title or file name)
function documentLabel(document) {
  if (!document) return "Unknown document";
  if (document.title) return document.title;
  if (document.file) {
    const parts = document.file.split("/");
    return parts[parts.length - 1] || document.file;
  }
  return `Document #${document.id}`;
}

// Sorts the evidence by confidence
const sortedEvidence = computed(() => props.detail?.evidence || []);
</script>

<template>
  <aside v-if="open" class="detail-panel" aria-label="Triple details">
    <header class="detail-header">
      <div class="detail-header-text">
        <span class="detail-eyebrow">Triple details</span>
        <h2 v-if="detail" class="detail-title">
          <span class="triple-part subject">{{ detail.subject }}</span>
          <span class="triple-sep">&rarr;</span>
          <span class="triple-part predicate">{{ detail.predicate }}</span>
          <span class="triple-sep">&rarr;</span>
          <span class="triple-part object">{{ detail.object }}</span>
        </h2>
        <h2 v-else class="detail-title">
          <span class="triple-part">Loading...</span>
        </h2>
      </div>
      <button
        type="button"
        class="modal-close"
        aria-label="Close triple details"
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

    <div class="detail-body">
      <div v-if="loading" class="detail-loading">Loading triple details...</div>
      <div v-else-if="error" class="detail-error">{{ error }}</div>
      <template v-else-if="detail">
        <section class="detail-section">
          <h3 class="detail-section-title">Summary</h3>
          <dl class="detail-grid">
            <div class="detail-grid-row">
              <dt>Confidence</dt>
              <dd>{{ formatConfidence(detail.confidence) }}</dd>
            </div>
            <div class="detail-grid-row">
              <dt>Support count</dt>
              <dd>{{ detail.support_count }}</dd>
            </div>
            <div class="detail-grid-row">
              <dt>Last seen</dt>
              <dd>{{ formatDate(detail.last_seen) }}</dd>
            </div>
          </dl>
        </section>

        <section class="detail-section">
          <h3 class="detail-section-title">
            Evidence
            <span class="detail-section-count">({{ sortedEvidence.length }})</span>
          </h3>

          <p v-if="!sortedEvidence.length" class="detail-empty">
            No evidence recorded for this triple.
          </p>

          <ol v-else class="evidence-list">
            <li
              v-for="(evidence, index) in sortedEvidence"
              :key="evidence.id"
              class="evidence-item"
            >
              <div class="evidence-item-header">
                <span class="evidence-index">#{{ index + 1 }}</span>
                <span class="evidence-confidence">
                  Confidence {{ formatConfidence(evidence.confidence) }}
                </span>
                <span
                  v-if="evidence.source_method"
                  class="status-chip evidence-method"
                >
                  {{ evidence.source_method }}
                </span>
              </div>

              <dl class="detail-grid">
                <div class="detail-grid-row">
                  <dt>Document</dt>
                  <dd>
                    <span v-if="evidence.document" :title="evidence.document.file">
                      {{ documentLabel(evidence.document) }}
                    </span>
                    <span v-else class="detail-muted">Unknown</span>
                  </dd>
                </div>
                <div
                  v-if="evidence.document && evidence.document.journal"
                  class="detail-grid-row"
                >
                  <dt>Journal</dt>
                  <dd>{{ evidence.document.journal }}</dd>
                </div>
                <div
                  v-if="evidence.document && evidence.document.doi"
                  class="detail-grid-row"
                >
                  <dt>DOI</dt>
                  <dd>
                    <a
                      class="detail-link"
                      :href="`https://doi.org/${evidence.document.doi}`"
                      target="_blank"
                      rel="noopener"
                    >
                      {{ evidence.document.doi }}
                    </a>
                  </dd>
                </div>
                <div
                  v-if="evidence.document && evidence.document.citations_count"
                  class="detail-grid-row"
                >
                  <dt>Cited by</dt>
                  <dd>{{ evidence.document.citations_count }}</dd>
                </div>
                <div class="detail-grid-row">
                  <dt>Section</dt>
                  <dd>
                    <span v-if="evidence.section">
                      {{ evidence.section.path || evidence.section.heading }}
                    </span>
                    <span v-else class="detail-muted">Unknown</span>
                  </dd>
                </div>
                <div
                  v-if="evidence.section && (evidence.section.page_numbers || []).length"
                  class="detail-grid-row"
                >
                  <dt>Pages</dt>
                  <dd>{{ evidence.section.page_numbers.join(", ") }}</dd>
                </div>
                <div class="detail-grid-row">
                  <dt>Extracted</dt>
                  <dd>{{ formatDate(evidence.created_at) }}</dd>
                </div>
              </dl>

              <div class="evidence-citations">
                <h4 class="evidence-citations-title">
                  Section citations
                  <span class="detail-section-count">
                    ({{ (evidence.citations || []).length }})
                  </span>
                </h4>
                <p
                  v-if="!evidence.citations || !evidence.citations.length"
                  class="detail-empty"
                >
                  No citations recorded for this section.
                </p>
                <table v-else class="citations-table">
                  <thead>
                    <tr>
                      <th class="citations-col-ref">Ref</th>
                      <th>Reference</th>
                      <th class="citations-col-count">Citations</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="citation in evidence.citations"
                      :key="citation.id"
                    >
                      <td class="citations-col-ref">
                        <span v-if="citation.ref_index !== null && citation.ref_index !== undefined">
                          [{{ citation.ref_index }}]
                        </span>
                        <span v-else class="detail-muted">&mdash;</span>
                      </td>
                      <td>
                        <a
                          v-if="citation.url"
                          class="detail-link citation-text"
                          :href="citation.url"
                          target="_blank"
                          rel="noopener"
                          :title="citation.text"
                        >
                          {{ citation.text }}
                        </a>
                        <span v-else class="citation-text" :title="citation.text">
                          {{ citation.text }}
                        </span>
                        <div v-if="citation.doi || citation.pmid" class="citation-meta">
                          <span v-if="citation.doi">DOI: {{ citation.doi }}</span>
                          <span v-if="citation.pmid">PMID: {{ citation.pmid }}</span>
                        </div>
                      </td>
                      <td class="citations-col-count">
                        {{ citation.citations_count ?? 0 }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </li>
          </ol>
        </section>
      </template>
    </div>
  </aside>
</template>
