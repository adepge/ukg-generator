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

export async function uploadPdfs(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const response = await api.post("/documents/upload", formData);
  return response.data;
}

export async function listDocuments() {
  const response = await api.get("/documents");
  return response.data;
}

export async function fetchGraph(params = {}) {
  const response = await api.get("/graph", { params });
  return response.data;
}

export async function searchGraph(q, type) {
  const response = await api.get("/search", { params: { q, type } });
  return response.data;
}
