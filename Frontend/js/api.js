// Backend address. Change here only, when you deploy.
const API_BASE = "http://127.0.0.1:8000";

// ---------- Token storage ----------
const Auth = {
  getToken: () => localStorage.getItem("token"),
  setToken: (token) => localStorage.setItem("token", token),
  logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
  },
  // Call at top of every protected page
  requireLogin() {
    if (!this.getToken()) window.location.href = "login.html";
  },
};

// FastAPI error → readable text. 422 gives a list, others give a string.
function formatError(data) {
  if (!data || !data.detail) return null;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((e) => e.msg).join(", ");
  }
  return null;
}

// One function for every API call.
// Adds the Bearer token, handles JSON, handles errors.
async function apiFetch(path, options = {}) {
  const { json, ...rest } = options;
  const headers = { ...(rest.headers || {}) };

  const token = Auth.getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    rest.body = JSON.stringify(json);
  }

  let res;
  try {
    res = await fetch(API_BASE + path, { ...rest, headers });
  } catch {
    throw new Error("Cannot reach server. Is the backend running?");
  }

  // Token expired or invalid → back to login (but not on the login call itself)
  if (res.status === 401 && token && !path.startsWith("/auth/login")) {
    Auth.logout();
    throw new Error("Session expired. Please login again.");
  }

  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(formatError(data) || `Error ${res.status}`);
  return data;
}