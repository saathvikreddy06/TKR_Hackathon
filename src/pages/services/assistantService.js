const API_BASE_URL = 'http://127.0.0.1:8000'

export const askStandIQ = async (query) => {
    const response = await fetch(
        `${API_BASE_URL}/api/search`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                limit: 5
            })
        }
    )

    if (!response.ok) {
        throw new Error(
            `Backend request failed: ${response.status}`
        )
    }

    return await response.json()
}