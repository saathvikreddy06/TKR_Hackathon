import { auth } from '../firebase'

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const API_BASE_URL = configuredApiBaseUrl || (
    import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''
)

export const apiRequest = async (path, options = {}) => {
    if (!API_BASE_URL) {
        throw new Error('The production API URL is not configured.')
    }

    const headers = new Headers(options.headers || {})
    headers.set('Accept', 'application/json')

    if (options.body && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
    }

    if (auth.currentUser) {
        headers.set('Authorization', `Bearer ${await auth.currentUser.getIdToken()}`)
    }

    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 30000)

    let response
    try {
        response = await fetch(`${API_BASE_URL}${path}`, {
            ...options,
            headers,
            signal: options.signal || controller.signal
        })
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('The StandIQ backend request timed out.')
        }
        throw new Error('The StandIQ backend could not be reached.')
    } finally {
        window.clearTimeout(timeout)
    }

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(
            data.detail || `Request failed with status ${response.status}`
        )
    }

    return data
}

export { API_BASE_URL }