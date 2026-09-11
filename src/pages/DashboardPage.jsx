import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { auth } from './firebase'
import { getUserProfile } from './services/authService'
import { listHistory } from './services/historyService'
import { listMyConsultations } from './services/consultationService'
import { listConsultants } from './services/consultancyService'

const quickAccess = [
    { icon: '✦', title: 'AI Assistant', description: 'Ask questions about BIS standards and get AI-powered guidance.', action: 'Open', to: '/assistant' },
    { icon: '▤', title: 'BIS Standards', description: 'Explore BIS standards, requirements, and certification information.', action: 'Explore', to: '/standards' },
    { icon: '◉', title: 'Consultants', description: 'Find guidance and connect with BIS-related consultants.', action: 'View', to: '/consultants' }
]

function relativeTime(value) {
    if (!value) return 'Recently'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return 'Recently'
    const minutes = Math.max(1, Math.floor((Date.now() - date.getTime()) / 60000))
    if (minutes < 60) return `${minutes} min ago`
    if (minutes < 1440) return `${Math.floor(minutes / 60)} hr ago`
    if (minutes < 2880) return 'Yesterday'
    return `${Math.floor(minutes / 1440)} days ago`
}

function DashboardPage() {
    const navigate = useNavigate()
    const [query, setQuery] = useState('')
    const [userName, setUserName] = useState('')
    const [history, setHistory] = useState([])
    const [consultations, setConsultations] = useState([])
    const [consultantNames, setConsultantNames] = useState({})
    const [loadingHistory, setLoadingHistory] = useState(true)
    const [loadingConsultations, setLoadingConsultations] = useState(true)
    const [historyError, setHistoryError] = useState(false)
    const [consultationsError, setConsultationsError] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)

    useEffect(() => {
        let isMounted = true
        const user = auth.currentUser

        if (user) {
            setUserName(user.displayName || user.email?.split('@')[0] || '')
            getUserProfile(user.uid).then((profile) => {
                if (isMounted && profile?.username) setUserName(profile.username)
            }).catch(() => { })
        }

        listHistory().then((data) => {
            if (isMounted) setHistory((data.history || []).slice(0, 5))
        }).catch(() => {
            if (isMounted) setHistoryError(true)
        }).finally(() => {
            if (isMounted) setLoadingHistory(false)
        })

        listMyConsultations().then(async (data) => {
            const items = data.consultations || []
            if (isMounted) setConsultations(items)
            if (items.length) {
                try {
                    const consultantData = await listConsultants()
                    const names = Object.fromEntries((consultantData.consultants || []).map((consultant) => [consultant.id, consultant.name]))
                    if (isMounted) setConsultantNames(names)
                } catch {
                    // The consultation remains useful without a resolved consultant name.
                }
            }
        }).catch(() => {
            if (isMounted) setConsultationsError(true)
        }).finally(() => {
            if (isMounted) setLoadingConsultations(false)
        })

        return () => { isMounted = false }
    }, [])

    const submitQuery = (event) => {
        event.preventDefault()
        const trimmedQuery = query.trim()
        if (!trimmedQuery || isSubmitting) return
        setIsSubmitting(true)
        navigate(`/assistant?query=${encodeURIComponent(trimmedQuery)}`)
    }

    const counts = {
        pending: consultations.filter((item) => item.status === 'pending').length,
        active: consultations.filter((item) => ['accepted', 'active'].includes(item.status)).length,
        completed: consultations.filter((item) => item.status === 'completed').length
    }

    return <section className="dashboard-page data-page">
        <div className="dashboard-welcome">
            <p className="eyebrow"><span></span> Your workspace</p>
            <h1>Welcome back{userName ? `, ${userName}` : ''} <span aria-hidden="true">👋</span></h1>
            <p>Your BIS standards workspace</p>
            <form className="dashboard-query" onSubmit={submitQuery}>
                <span className="dashboard-query-icon" aria-hidden="true">⌕</span>
                <label className="sr-only" htmlFor="dashboard-query-input">Ask StandIQ about BIS standards</label>
                <input id="dashboard-query-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask StandIQ about BIS standards..." />
                <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Opening...' : 'Ask'}</button>
            </form>
        </div>

        <section className="dashboard-section" aria-labelledby="quick-access-heading">
            <div className="dashboard-section-heading"><h2 id="quick-access-heading">Quick access</h2></div>
            <div className="quick-access-grid">{quickAccess.map((item) => <article className="quick-access-card" key={item.title}><span className="quick-access-icon" aria-hidden="true">{item.icon}</span><h3>{item.title}</h3><p>{item.description}</p><Link to={item.to}>{item.action} <span aria-hidden="true">→</span></Link></article>)}</div>
        </section>

        <section className="dashboard-section" aria-labelledby="recent-searches-heading">
            <div className="dashboard-section-heading"><h2 id="recent-searches-heading">Recent searches</h2><Link to="/history">View all <span aria-hidden="true">→</span></Link></div>
            <div className="dashboard-list">
                {loadingHistory && <p className="dashboard-state">Loading recent searches...</p>}
                {!loadingHistory && historyError && <p className="dashboard-state">Unable to load recent searches.</p>}
                {!loadingHistory && !historyError && history.length === 0 && <div className="dashboard-state"><strong>No recent searches yet.</strong><span>Ask StandIQ a question to get started.</span></div>}
                {!loadingHistory && !historyError && history.map((item) => <Link className="dashboard-list-row" to={`/assistant?query=${encodeURIComponent(item.query || '')}`} key={item.id}><span><strong>{item.query || 'Untitled search'}</strong><small>{relativeTime(item.created_at)}</small></span><span aria-hidden="true">→</span></Link>)}
            </div>
        </section>

        <section className="dashboard-section" aria-labelledby="my-consultations-heading">
            <div className="dashboard-section-heading"><h2 id="my-consultations-heading">My consultations</h2><Link to="/consultations">View all <span aria-hidden="true">→</span></Link></div>
            <div className="consultation-counts">{[['Pending', counts.pending], ['Active', counts.active], ['Completed', counts.completed]].map(([label, count]) => <div key={label}><span>{label}</span><strong>{count}</strong></div>)}</div>
            {loadingConsultations && <p className="dashboard-state">Loading consultations...</p>}
            {!loadingConsultations && consultationsError && <p className="dashboard-state">Unable to load consultations.</p>}
            {!loadingConsultations && !consultationsError && consultations.length === 0 && <div className="dashboard-state"><strong>No consultations yet.</strong><span>Need expert guidance?</span><Link to="/consultants">Browse consultants <span aria-hidden="true">→</span></Link></div>}
            {!loadingConsultations && !consultationsError && consultations.slice(0, 3).map((consultation) => <article className="consultation-row" key={consultation.id}><div><small>Recent consultation</small><h3>{consultation.subject}</h3><p>Consultant: {consultantNames[consultation.consultant_id] || 'Consultant'}</p></div><div className="consultation-row-action"><span className={`status-badge status-${consultation.status}`}>{consultation.status}</span><Link to={`/consultations/${consultation.id}`}>{consultation.status === 'active' ? 'Open chat' : 'View details'} <span aria-hidden="true">→</span></Link></div></article>)}
        </section>
    </section>
}

export default DashboardPage
