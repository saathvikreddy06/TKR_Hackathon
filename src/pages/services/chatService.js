import { apiRequest } from './apiClient'

export const createChatSession = (consultationId) => apiRequest('/api/chat/sessions', { method: 'POST', body: JSON.stringify({ consultation_id: consultationId }) })
export const listChatSessions = () => apiRequest('/api/chat/sessions')
export const getChatSession = (sessionId) => apiRequest(`/api/chat/sessions/${sessionId}`)
export const getChatMessages = (sessionId) => apiRequest(`/api/chat/sessions/${sessionId}/messages`)
export const sendChatMessage = (sessionId, message) => apiRequest(`/api/chat/sessions/${sessionId}/messages`, { method: 'POST', body: JSON.stringify({ message }) })
export const closeChatSession = (sessionId) => apiRequest(`/api/chat/sessions/${sessionId}/close`, { method: 'PUT' })