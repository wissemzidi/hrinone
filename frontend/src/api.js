const BASE = import.meta.env.VITE_API_URL;
const TOKEN_KEY = "hrinone_token";

// Session credentials are HttpOnly cookies; JavaScript never reads the session token.
function readCookie(name) {
  const prefix = `${name}=`;
  const item = document.cookie
    .split("; ")
    .find((part) => part.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : "";
}

let onUnauthorized = null;
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

async function send(method, path, body) {
  const isForm = body instanceof FormData;
  const headers = {};
  if (body && !isForm) headers["Content-Type"] = "application/json";
  const csrf = readCookie("hrinone_csrf");
  if (csrf && !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase()))
    headers["X-CSRF-Token"] = csrf;

  const res = await fetch(BASE + path, {
    method,
    headers,
    credentials: "include",
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });

  if (!res.ok) {
    if (res.status === 401 && path !== "/auth/login") onUnauthorized?.();
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail))
        message = data.detail.map((e) => e.msg).join(". ");
    } catch {
      /* keep generic error */
    }
    throw new Error(message);
  }
  return res;
}

const json = async (res) => (res.status === 204 ? null : res.json());
export const api = {
  get: async (path) => json(await send("GET", path)),
  post: async (path, body) => json(await send("POST", path, body)),
  put: async (path, body) => json(await send("PUT", path, body)),
  patch: async (path, body) => json(await send("PATCH", path, body)),
  del: async (path) => json(await send("DELETE", path)),
  blob: async (path) => (await send("GET", path)).blob(),
};
