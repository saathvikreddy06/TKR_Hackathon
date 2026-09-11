import { apiRequest } from './apiClient'

export const submitFeedback = (payload) => apiRequest('/api/feedback', { method: 'POST', body: JSON.stringify(payload) })
export const listMyFeedback = () => apiRequest('/api/feedback/my')
export const listConsultantFeedback = (consultantId) => apiRequest(`/api/consultants/${consultantId}/feedback`)