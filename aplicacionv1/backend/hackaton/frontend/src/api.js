const TOKEN_KEY = 'ppto_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

// Convierte {gestion: 2026, region: [1,2]} en query string
export function qs(params) {
  const p = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '' || (Array.isArray(v) && !v.length)) return
    p.set(k, Array.isArray(v) ? v.join(',') : v)
  })
  return p.toString()
}

export async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) }
  const t = getToken()
  if (t) headers.Authorization = `Bearer ${t}`
  const res = await fetch(`/api${path}`, { ...opts, headers })
  if (res.status === 401) {
    setToken(null)
    window.location.reload()
  }
  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new Error(e.detail || `Error ${res.status}`)
  }
  return opts.raw ? res : res.json()
}

export async function descargar(path, nombre) {
  const res = await api(path, { raw: true })
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = nombre
  a.click()
  URL.revokeObjectURL(a.href)
}

export const bs = (n) =>
  n === null || n === undefined ? '—' : Number(n).toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
export const pct = (n) => (n === null || n === undefined ? '—' : `${Number(n).toFixed(1)}%`)
export const corto = (n) => {
  const a = Math.abs(n)
  if (a >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  if (a >= 1e3) return `${(n / 1e3).toFixed(0)}K`
  return String(Math.round(n))
}
