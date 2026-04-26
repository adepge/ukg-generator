import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
});

// API endpoints

// Upload a single PDF file
export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/documents/upload", formData);
  return response.data;
}

// Upload multiple PDF files
export async function uploadPdfs(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const response = await api.post("/documents/upload", formData);
  return response.data;
}

// List all documents
export async function listDocuments() {
  const response = await api.get("/documents");
  return response.data;
}

// Fetch the graph
export async function fetchGraph(params = {}) {
  const response = await api.get("/graph", { params });
  return response.data;
}

// Search the graph
export async function searchGraph(q, type, matchMode, params = {}) {
  const response = await api.get("/search", { params: { q, type, match_mode: matchMode, ...params } });
  return response.data;
}

// Fetch the full details of a single triple (evidence, source document,
// section, and section citations).
export async function fetchTripleDetail(id) {
  const response = await api.get(`/triples/${id}`);
  return response.data;
}

// Delete a single document and all of its related triples
export async function deleteDocument(id) {
  const response = await api.delete(`/documents/${id}`);
  return response.data;
}

// Clear all documents, triples, and graph data
export async function clearAll() {
  const response = await api.delete("/clear-all");
  return response.data;
}


// =========================================================
// Settings: summary
// =========================================================

// Get the summary of the settings (used to populate the toolbar summary chips)
export async function getSettingsSummary() {
  const response = await api.get("/settings/summary");
  return response.data;
}


// =========================================================
// Settings: blacklists
// =========================================================

// List all blacklists
export async function listBlacklists() {
  const response = await api.get("/settings/blacklists");
  return response.data;
}

// Get a single blacklist
export async function getBlacklist(id) {
  const response = await api.get(`/settings/blacklists/${id}`);
  return response.data;
}

// Paginated term list; server-side filtered by category and query
export async function listBlacklistTerms(id, params = {}) {
  const response = await api.get(`/settings/blacklists/${id}/terms`, { params });
  return response.data;
}

// Update a single term in a blacklist
export async function updateBlacklistTerm(blacklistId, termId, patch) {
  const response = await api.patch(
    `/settings/blacklists/${blacklistId}/terms/${termId}`,
    patch
  );
  return response.data;
}

// Reset a blacklist to its default terms
export async function resetBlacklist(id) {
  const response = await api.post(`/settings/blacklists/${id}/reset`);
  return response.data;
}

// Toggle a blacklist to be enabled or disabled
export async function toggleBlacklist(id, isEnabled) {
  const response = await api.post(`/settings/blacklists/${id}/toggle`, {
    is_enabled: isEnabled,
  });
  return response.data;
}

// Upload a new blacklist
export async function uploadBlacklist(file, name) {
  const formData = new FormData();
  formData.append("file", file);
  if (name) {
    formData.append("name", name);
  }
  const response = await api.post("/settings/blacklists/upload", formData);
  return response.data;
}

// Returns the CSV URL so the browser can trigger a native download
export function blacklistDownloadUrl(id) {
  return `${api.defaults.baseURL}/settings/blacklists/${id}/download`;
}

// Delete a single blacklist
export async function deleteBlacklist(id) {
  const response = await api.delete(`/settings/blacklists/${id}`);
  return response.data;
}


// =========================================================
// Settings: label lists
// =========================================================

// List all label lists
export async function listLabelLists() {
  const response = await api.get("/settings/label-lists");
  return response.data;
}

// Get a single label list
export async function getLabelList(id) {
  const response = await api.get(`/settings/label-lists/${id}`);
  return response.data;
}

// Create a new label list
export async function createLabelList(payload) {
  const response = await api.post("/settings/label-lists", payload);
  return response.data;
}

// Delete a single label list
export async function deleteLabelList(id) {
  const response = await api.delete(`/settings/label-lists/${id}`);
  return response.data;
}

// Set this label list to be the active label list
export async function activateLabelList(id) {
  const response = await api.post(`/settings/label-lists/${id}/activate`);
  return response.data;
}

// Reset a label list to its default entities and relations
export async function resetLabelList(id) {
  const response = await api.post(`/settings/label-lists/${id}/reset`);
  return response.data;
}

// Create a new entity label
export async function createEntityLabel(labelListId, payload) {
  const response = await api.post(
    `/settings/label-lists/${labelListId}/entity-labels`,
    payload
  );
  return response.data;
}

// Update a single entity label
export async function updateEntityLabel(labelListId, entityId, patch) {
  const response = await api.patch(
    `/settings/label-lists/${labelListId}/entity-labels/${entityId}`,
    patch
  );
  return response.data;
}

// Delete a single entity label
export async function deleteEntityLabel(labelListId, entityId) {
  const response = await api.delete(
    `/settings/label-lists/${labelListId}/entity-labels/${entityId}`
  );
  return response.data;
}

// Create a new relation label
export async function createRelationLabel(labelListId, payload) {
  const response = await api.post(
    `/settings/label-lists/${labelListId}/relation-labels`,
    payload
  );
  return response.data;
}

// Update a single relation label
export async function updateRelationLabel(labelListId, relationId, patch) {
  const response = await api.patch(
    `/settings/label-lists/${labelListId}/relation-labels/${relationId}`,
    patch
  );
  return response.data;
}

// Delete a single relation label
export async function deleteRelationLabel(labelListId, relationId) {
  const response = await api.delete(
    `/settings/label-lists/${labelListId}/relation-labels/${relationId}`
  );
  return response.data;
}


// =========================================================
// Settings: ontologies
// =========================================================

// List all ontologies
export async function listOntologies() {
  const response = await api.get("/settings/ontologies");
  return response.data;
}

// Upload a new ontology
export async function uploadOntology(file, name) {
  const formData = new FormData();
  formData.append("file", file);
  if (name) {
    formData.append("name", name);
  }
  const response = await api.post("/settings/ontologies/upload", formData);
  return response.data;
}

// Delete a single ontology
export async function deleteOntology(id) {
  const response = await api.delete(`/settings/ontologies/${id}`);
  return response.data;
}

// Save the enabled state of multiple ontologies
export async function saveOntologyEnabled(enabledIds) {
  const response = await api.patch("/settings/ontologies", {
    ids_enabled: enabledIds,
  });
  return response.data;
}
