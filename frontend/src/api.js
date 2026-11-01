const BASE = import.meta.env.VITE_API_URL;

const CSRF_COOKIE = "hrinone_csrf";

let onUnauthorized = null;

export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

function getCsrfToken() {
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${CSRF_COOKIE}=`));

  return cookie ? decodeURIComponent(cookie.split("=")[1]) : null;
}

async function send(method, path, body) {
  const isForm = body instanceof FormData;
  const headers = {};

  if (body && !isForm) {
    headers["Content-Type"] = "application/json";
  }

  const unsafe = ["POST", "PUT", "PATCH", "DELETE"].includes(method);

  if (unsafe && path !== "/auth/login") {
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });

  if (!res.ok) {
    if (res.status === 401 && path !== "/auth/login") {
      onUnauthorized?.();
    }

    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res;
}

const json = async (res) => (res.status === 204 ? null : res.json());

export const api = {
  get: (path) => send("GET", path).then(json),
  post: (path, body) => send("POST", path, body).then(json),
  put: (path, body) => send("PUT", path, body).then(json),
  patch: (path, body) => send("PATCH", path, body).then(json),
  del: (path) => send("DELETE", path).then(json),
  blob: (path) => send("GET", path).then((res) => res.blob()),
};
