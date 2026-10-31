const BASE = '/api'
const TOKEN_KEY = 'hrinone_token'

export const auth = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

let onUnauthorized = null
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn
}

async function send(method, path, body) {
  const isForm = body instanceof FormData
  const headers = {}
  if (body && !isForm) headers['Content-Type'] = 'application/json'
  const token = auth.get()
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  })

  if (!res.ok) {
    if (res.status === 401 && token && path !== '/auth/login') {
      auth.clear()
      onUnauthorized?.()
    }
    let message = `Request failed (${res.status})`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') message = data.detail
      else if (Array.isArray(data.detail)) message = data.detail.map((e) => e.msg).join('. ')
    } catch {
      // response had no JSON body; keep the generic message
    }
    throw new Error(message)
  }
  return res
}

const json = async (res) => (res.status === 204 ? null : res.json())

export const api = {
  get: async (path) => json(await send('GET', path)),
  post: async (path, body) => json(await send('POST', path, body)),
  put: async (path, body) => json(await send('PUT', path, body)),
  patch: async (path, body) => json(await send('PATCH', path, body)),
  del: async (path) => json(await send('DELETE', path)),
  blob: async (path) => (await send('GET', path)).blob(),
}
