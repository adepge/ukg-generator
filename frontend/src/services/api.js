import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
});

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/documents/upload", formData);
  return response.data;
}

export async function listDocuments() {
  const response = await api.get("/documents");
  return response.data;
}

export async function fetchGraph(query = "") {
  const response = await api.get("/graph", { params: query ? { q: query } : {} });
  return response.data;
}

export async function searchGraph(q, type) {
  const response = await api.get("/search", { params: { q, type } });
  return response.data;
}
