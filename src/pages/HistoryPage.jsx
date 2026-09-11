import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { clearHistory, deleteHistoryItem, listHistory } from './services/historyService'

function HistoryPage() {
    const [history, setHistory] = useState([])
    const [error, setError] = useState('')

    const refresh = () => listHistory().then((data) => setHistory(data.history || [])).catch((requestError) => setError(requestError.message))
    useEffect(() => { refresh() }, [])

    const clear = async () => { await clearHistory(); setHistory([]) }
    const remove = async (id) => { await deleteHistoryItem(id); await refresh() }

    return <section className="data-page history-page"><div className="page-intro-row"><div><p className="eyebrow"><span></span> Private history</p><h1>Your standards trail.</h1><p>Review the BIS searches you chose to save while signed in.</p></div><button className="button" type="button" onClick={clear}>Clear history</button></div>{error && <p className="auth-error">{error}</p>}<div className="dashboard-card">{history.length === 0 ? <p>No saved searches yet. Ask the assistant to start building your trail.</p> : history.map((item) => <article className="query-item" key={item.id}><div><strong>{item.query}</strong><small>{item.answer}</small></div><button type="button" onClick={() => remove(item.id)} aria-label={`Delete search ${item.query}`}>×</button></article>)}</div><Link className="back-link" to="/assistant">Ask the assistant</Link></section>
}

export default HistoryPage
