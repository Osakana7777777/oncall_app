// 管理 API 用 fetch ラッパー。
// サーバ側で ADMIN_TOKEN 環境変数が設定されている場合、
// X-Admin-Token ヘッダによる認証が必要になる。
const STORAGE_KEY = 'admin_token'

export function getAdminToken() {
  return sessionStorage.getItem(STORAGE_KEY) || ''
}

export function setAdminToken(token) {
  if (token) {
    sessionStorage.setItem(STORAGE_KEY, token)
  } else {
    sessionStorage.removeItem(STORAGE_KEY)
  }
}

export function adminFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getAdminToken()
  if (token) headers['X-Admin-Token'] = token
  return fetch(url, { ...options, headers })
}
