import { apiRequest } from './apiClient'

export const getAdminStats = () => apiRequest('/api/admin/stats')
export const getAdminConsultants = () => apiRequest('/api/admin/consultants')
export const getAdminConsultations = () => apiRequest('/api/admin/consultations')
export const getAdminFeedback = () => apiRequest('/api/admin/feedback')