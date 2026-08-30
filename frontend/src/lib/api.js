import axios from "axios";

const rawBase = (process.env.REACT_APP_BACKEND_URL || "").trim().replace(/\/+$/, "");
export const API = rawBase
  ? rawBase.endsWith("/api")
    ? rawBase
    : `${rawBase}/api`
  : "/api";

const client = axios.create({ baseURL: API, withCredentials: true });

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const api = {
  get: (path, config) => client.get(path, config).then((r) => r.data),
  post: (path, body, config) => client.post(path, body, config).then((r) => r.data),
  patch: (path, body) => client.patch(path, body).then((r) => r.data),
  del: (path) => client.delete(path).then((r) => r.data),
  upload: (path, formData, onUploadProgress) =>
    client.post(path, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress,
    }).then((r) => r.data),
  raw: client,
};

export default api;
