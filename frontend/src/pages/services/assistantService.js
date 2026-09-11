import { apiRequest } from './apiClient'

export const askStandIQ = async (query, language = 'en') => {
    return apiRequest('/api/search', {
        method: 'POST',
        body: JSON.stringify({
            query,
            limit: 5,
            language
        })
    })
}