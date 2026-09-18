import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { auth } from './firebase'
import { getUserProfile } from './services/authService'
import { listHistory } from './services/historyService'
import { listMyConsultations } from './services/consultationService'
import { listConsultants } from './services/consultancyService'
import { getMyConsultantProfile } from './services/consultancyService'
import { listConsultantFeedback } from './services/feedbackService'
import { updateConsultation } from './services/consultationService'

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

export function ConsultantDashboard() {
    const [profile, setProfile] = useState(null)
    const [requests, setRequests] = useState([])
    const [feedback, setFeedback] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    const refresh = async () => {
        try {
            const [profileData, consultationData] = await Promise.all([getMyConsultantProfile(), listMyConsultations()])
            setProfile(profileData.profile)
            setRequests(consultationData.consultations || [])
            if (profileData.profile?.id) {
                const feedbackData = await listConsultantFeedback(profileData.profile.id)
                setFeedback(feedbackData.feedback || [])
            }
        } catch (requestError) {
            setError(requestError.message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { refresh() }, [])

    const transition = async (id, action) => {
        try {
            await updateConsultation(id, action)
            await refresh()
        } catch (requestError) {
            setError(requestError.message)
        }
    }

    const pending = requests.filter((item) => item.status === 'pending')
    const active = requests.filter((item) => ['accepted', 'active'].includes(item.status))
    const completed = requests.filter((item) => ['completed', 'rejected', 'cancelled'].includes(item.status))

    if (loading) return <section className="dashboard-page data-page"><p className="dashboard-state">Loading consultant dashboard...</p></section>
    return <section className="dashboard-page data-page consultant-dashboard-page">
        <div className="dashboard-welcome"><p className="eyebrow"><span></span> Consultant workspace</p><h1>{profile?.consultancy_name || 'Your consultancy dashboard'}</h1><p>{profile?.consultancy_area || 'BIS consultancy'} · {profile?.place || 'Location not set'}</p></div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <section className="consultant-dashboard-profile"><div className="consultant-dashboard-avatar">{initials(profile?.name)}</div><div><p className="eyebrow"><span></span> Public profile</p><h2>{profile?.name}</h2><p>{profile?.bio || 'Add a short bio to help users understand your BIS experience.'}</p><div className="consultant-dashboard-tags">{[...(profile?.expertise || []), ...(profile?.categories || [])].slice(0, 6).map((item) => <span key={item}>{item}</span>)}</div></div><Link className="button button-small" to={`/consultants/${profile?.id}`}>View profile <span>↗</span></Link></section>
        <section className="consultant-dashboard-stats"><div><span>Pending requests</span><strong>{pending.length}</strong></div><div><span>Active consultations</span><strong>{active.length}</strong></div><div><span>Completed history</span><strong>{completed.length}</strong></div><div><span>Feedback received</span><strong>{feedback.length}</strong></div></section>
        <ConsultantRequestSection title="New consultation requests" items={pending} empty="No new requests right now." actions={(item) => <><button type="button" onClick={() => transition(item.id, 'accept')}>Accept</button><button type="button" onClick={() => transition(item.id, 'reject')}>Reject</button></>} />
        <ConsultantRequestSection title="Current consultations" items={active} empty="No active consultations." actions={(item) => <>{item.status === 'accepted' && <button type="button" onClick={() => transition(item.id, 'start')}>Start</button>}{item.status === 'active' && <><Link to={`/consultations/${item.id}`}>Open details →</Link><button type="button" onClick={() => transition(item.id, 'complete')}>Complete</button></>}</>} />
        <ConsultantRequestSection title="Consultation history" items={completed} empty="Completed and closed consultations will appear here." actions={(item) => <Link to={`/consultations/${item.id}`}>View details →</Link>} />
        <section className="dashboard-section consultant-feedback-section"><div className="dashboard-section-heading"><h2>Feedback from users</h2><span>{feedback.length}</span></div>{feedback.length === 0 ? <p className="dashboard-state">Feedback from completed consultations will appear here.</p> : <div className="feedback-list">{feedback.map((item) => <article className="feedback-row" key={item.id}><div className="feedback-stars" aria-label={`${item.rating} out of 5 stars`}>{'★'.repeat(item.rating)}<span>{'★'.repeat(5 - item.rating)}</span></div><p>{item.comment || 'No written comment.'}</p><small>Consultation {item.consultation_id}</small></article>)}</div>}</section>
    </section>
}

function ConsultantRequestSection({ title, items, empty, actions }) {
    return <section className="dashboard-section consultant-request-section"><div className="dashboard-section-heading"><h2>{title}</h2><span>{items.length}</span></div>{items.length === 0 ? <p className="dashboard-state">{empty}</p> : <div className="consultant-request-list">{items.map((item) => <article className="consultant-request-row" key={item.id}><div><small>{item.status}</small><h3>{item.subject}</h3><p>{item.description}</p><span className="requester-details">Requested by {item.requester?.username || item.requester?.email || 'StandIQ user'}{item.requester?.email ? ` · ${item.requester.email}` : ''}</span></div><div className="consultant-request-actions">{actions(item)}</div></article>)}</div>}</section>
}

function initials(name = '') {
    return name.split(' ').filter(Boolean).map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'C'
}

function DashboardPage({ role = 'user' }) {
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
        if (role === 'consultant') return undefined

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
    }, [role])

    if (role === 'consultant') return <ConsultantDashboard />

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
