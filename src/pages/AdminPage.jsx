import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAdminConsultants, getAdminConsultations, getAdminFeedback, getAdminStats } from './services/adminService'

function AdminPage() {
    const [stats, setStats] = useState({})
    const [consultants, setConsultants] = useState([])
    const [consultations, setConsultations] = useState([])
    const [feedback, setFeedback] = useState([])
    const [error, setError] = useState('')

    useEffect(() => {
        Promise.all([getAdminStats(), getAdminConsultants(), getAdminConsultations(), getAdminFeedback()])
            .then(([statsData, consultantData, consultationData, feedbackData]) => {
                setStats(statsData)
                setConsultants(consultantData.consultants || [])
                setConsultations(consultationData.consultations || [])
                setFeedback(feedbackData.feedback || [])
            })
            .catch((requestError) => setError(requestError.message))
    }, [])

    return <section className="data-page admin-page">
        <div className="page-intro-row"><div><p className="eyebrow"><span></span> Admin workspace</p><h1>Keep the network trustworthy.</h1><p>Review consultant records, requests, and feedback through secured admin endpoints.</p></div><Link className="button" to="/dashboard">Back to dashboard <span>↗</span></Link></div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <div className="dashboard-grid">{[['Consultants', stats.consultants], ['Consultations', stats.consultations], ['Feedback', stats.feedback], ['Searches', stats.search_history]].map(([label, value]) => <article className="dashboard-card" key={label}><small>{label}</small><strong className="metric">{value ?? '—'}</strong></article>)}</div>
        <div className="dashboard-grid"><article className="dashboard-card dashboard-card-wide"><div className="card-heading"><span>Consultants</span><span>{consultants.length}</span></div>{consultants.map((consultant) => <div className="query-item" key={consultant.id}><div><strong>{consultant.name}</strong><small>{consultant.email || 'No email'} · {consultant.active === false ? 'Inactive' : 'Active'}</small></div><span>{consultant.availability ? 'Available' : 'Busy'}</span></div>)}</article><article className="dashboard-card"><div className="card-heading"><span>Recent feedback</span><span>{feedback.length}</span></div>{feedback.slice(0, 5).map((item) => <div className="query-item" key={item.id}><div><strong>{item.rating}/5</strong><small>{item.comment || 'No comment'}</small></div></div>)}</article></div>
        <article className="dashboard-card"><div className="card-heading"><span>Consultation requests</span><span>{consultations.length}</span></div>{consultations.slice(0, 8).map((consultation) => <div className="query-item" key={consultation.id}><div><strong>{consultation.subject}</strong><small>{consultation.status} · {consultation.user_id}</small></div><span>{consultation.consultant_id}</span></div>)}</article>
    </section>
}

export default AdminPage
