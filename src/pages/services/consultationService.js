import { apiRequest } from './apiClient'

export const createConsultation = (payload) => apiRequest('/api/consultations', { method: 'POST', body: JSON.stringify(payload) })
export const listMyConsultations = () => apiRequest('/api/consultations/my')
export const getConsultation = (consultationId) => apiRequest(`/api/consultations/${consultationId}`)
export const updateConsultation = (consultationId, action) => apiRequest(`/api/consultations/${consultationId}/${action}`, { method: 'PUT' })