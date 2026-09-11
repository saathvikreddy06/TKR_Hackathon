import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getConsultation, updateConsultation } from './services/consultationService'
import { createChatSession } from './services/chatService'

function ConsultationDetailPage({ role = 'user' }) {
    const { consultationId } = useParams()
    const navigate = useNavigate()
    const [consultation, setConsultation] = useState(null)
    const [error, setError] = useState('')

    const refresh = () => getConsultation(consultationId).then(setConsultation).catch((requestError) => setError(requestError.message))
    useEffect(() => { refresh() }, [consultationId])

    const action = async (name) => {
        try { await updateConsultation(consultationId, name); await refresh() } catch (requestError) { setError(requestError.message) }
    }

    const openChat = async () => {
        try {
            const session = await createChatSession(consultationId)
            navigate(`/chat/${session.id}`)
        } catch (requestError) { setError(requestError.message) }
    }

    if (error) return <section className="data-page"><p className="auth-error">{error}</p><Link to="/consultations">Back to consultations</Link></section>
    if (!consultation) return <section className="data-page"><p>Loading consultation...</p></section>

    return <section className="data-page consultation-detail-page"><Link className="back-link" to="/consultations">Back to consultations</Link><div className="page-intro-row"><div><p className="eyebrow"><span></span> Consultation request</p><h1>{consultation.subject}</h1><p>{consultation.description}</p></div><span className="status-badge status-current">{consultation.status}</span></div><article className="dashboard-card"><div className="card-heading"><span>Request details</span><span>{consultation.created_at ? new Date(consultation.created_at).toLocaleDateString() : ''}</span></div><p>Consultant: {consultation.consultant_id}</p><p>Requester: {consultation.user_id}</p><div className="composer-actions">{consultation.status === 'pending' && (role === 'consultant' ? <><button type="button" onClick={() => action('accept')}>Accept</button><button type="button" onClick={() => action('reject')}>Reject</button></> : <button type="button" onClick={() => action('cancel')}>Cancel request</button>)}{consultation.status === 'accepted' && role === 'consultant' && <button type="button" onClick={() => action('start')}>Start consultation</button>}{consultation.status === 'active' && <><button type="button" onClick={openChat}>Open chat</button>{role === 'consultant' && <button type="button" onClick={() => action('complete')}>Mark completed</button>}</>}{consultation.status === 'completed' && role !== 'consultant' && <Link className="button" to={`/feedback/${consultation.id}`}>Leave feedback <span>↗</span></Link>}</div></article></section>
}

export default ConsultationDetailPage
