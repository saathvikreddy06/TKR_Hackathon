import { auth } from '../firebase'

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export const apiRequest = async (path, options = {}) => {
    const headers = new Headers(options.headers || {})
    headers.set('Accept', 'application/json')

    if (options.body && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
    }

    if (auth.currentUser) {
        headers.set('Authorization', `Bearer ${await auth.currentUser.getIdToken()}`)
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(
            data.detail || `Request failed with status ${response.status}`
        )
    }

    return data
}

export { API_BASE_URL }