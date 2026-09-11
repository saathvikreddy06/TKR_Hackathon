import { apiRequest } from './apiClient'

export const askStandIQ = async (query) => {
    return apiRequest('/api/search', {
        method: 'POST',
        body: JSON.stringify({
            query,
            limit: 5
        })
    })
}