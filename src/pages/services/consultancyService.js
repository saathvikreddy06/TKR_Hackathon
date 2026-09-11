import { apiRequest } from './apiClient'

export const listConsultants = (filters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '' && value !== 'All expertise') {
            params.set(key, value)
        }
    })
    return apiRequest(`/api/consultants${params.toString() ? `?${params}` : ''}`)
}

export const getConsultant = (consultantId) => apiRequest(`/api/consultants/${consultantId}`)
export const createConsultant = (profile) => apiRequest('/api/consultants', { method: 'POST', body: JSON.stringify(profile) })
export const updateConsultant = (consultantId, profile) => apiRequest(`/api/consultants/${consultantId}`, { method: 'PUT', body: JSON.stringify(profile) })