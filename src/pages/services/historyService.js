import { apiRequest } from './apiClient'

export const listHistory = () => apiRequest('/api/history')
export const deleteHistoryItem = (historyId) => apiRequest(`/api/history/${historyId}`, { method: 'DELETE' })
export const clearHistory = () => apiRequest('/api/history', { method: 'DELETE' })