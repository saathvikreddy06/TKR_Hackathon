import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { createConsultation, listMyConsultations, updateConsultation } from './services/consultationService'
import { createConsultant } from './services/consultancyService'
import { createChatSession, getChatMessages, sendChatMessage } from './services/chatService'
import { submitFeedback } from './services/feedbackService'
import { clearHistory, deleteHistoryItem, listHistory } from './services/historyService'

function ConsultationsPage({ role = 'user' }) {
    const [searchParams] = useSearchParams()
    const [consultations, setConsultations] = useState([])
    const [history, setHistory] = useState([])
    const [subject, setSubject] = useState('')
    const [description, setDescription] = useState('')
    const [status, setStatus] = useState('')
    const [selectedSession, setSelectedSession] = useState(null)
    const [messages, setMessages] = useState([])
    const [chatMessage, setChatMessage] = useState('')
    const [rating, setRating] = useState(5)
    const [comment, setComment] = useState('')
    const [profileName, setProfileName] = useState('')
    const [profileBio, setProfileBio] = useState('')
    const [profileExpertise, setProfileExpertise] = useState('')

    const refresh = () => Promise.all([listMyConsultations(), listHistory()]).then(([consultationData, historyData]) => {
        setConsultations(consultationData.consultations || [])
        setHistory(historyData.history || [])
    }).catch((error) => setStatus(error.message))

    useEffect(() => { refresh() }, [])

    const requestConsultation = async (event) => {
        event.preventDefault()
        try {
            await createConsultation({ consultant_id: searchParams.get('consultant'), subject, description })
            setSubject('')
            setDescription('')
            setStatus('Consultation request sent.')
            await refresh()
        } catch (error) { setStatus(error.message) }
    }

    const changeStatus = async (id, action) => {
        try { await updateConsultation(id, action); await refresh() } catch (error) { setStatus(error.message) }
    }

    const openChat = async (consultationId) => {
        try {
            const session = await createChatSession(consultationId)
            const data = await getChatMessages(session.id)
            setSelectedSession(session)
            setMessages(data.messages || [])
        } catch (error) { setStatus(error.message) }
    }

    const sendMessage = async (event) => {
        event.preventDefault()
        if (!chatMessage.trim()) return
        try {
            await sendChatMessage(selectedSession.id, chatMessage)
            setChatMessage('')
            const data = await getChatMessages(selectedSession.id)
            setMessages(data.messages || [])
        } catch (error) { setStatus(error.message) }
    }

    const reviewConsultation = async (consultationId) => {
        try { await submitFeedback({ consultation_id: consultationId, rating: Number(rating), comment }); setStatus('Feedback submitted.') } catch (error) { setStatus(error.message) }
    }

    const saveConsultantProfile = async (event) => {
        event.preventDefault()
        try {
            await createConsultant({ name: profileName, bio: profileBio, expertise: profileExpertise.split(',').map((item) => item.trim()).filter(Boolean) })
            setStatus('Consultant profile created.')
        } catch (error) { setStatus(error.message) }
    }

    return <section className="data-page consultation-page">
        <div className="page-intro-row"><div><p className="eyebrow"><span></span> Consultation workspace</p><h1>Bring the right expertise into focus.</h1><p>Request help, follow each status, and keep the conversation in one place.</p></div><Link className="button" to="/consultants">Find a consultant <span>↗</span></Link></div>
        {status && <p className="auth-error" role="status">{status}</p>}
        {searchParams.get('consultant') && <form className="dashboard-callout" onSubmit={requestConsultation}><h2>Request a consultation</h2><label>Subject<input value={subject} onChange={(event) => setSubject(event.target.value)} required /></label><label>Question or description<textarea value={description} onChange={(event) => setDescription(event.target.value)} required rows="4" /></label><button className="button" type="submit">Send request <span>↗</span></button></form>}
        {role === 'consultant' && <form className="dashboard-callout" onSubmit={saveConsultantProfile}><h2>Set up your consultant profile</h2><label>Name<input value={profileName} onChange={(event) => setProfileName(event.target.value)} required /></label><label>Bio<textarea value={profileBio} onChange={(event) => setProfileBio(event.target.value)} rows="3" /></label><label>Expertise, separated by commas<input value={profileExpertise} onChange={(event) => setProfileExpertise(event.target.value)} /></label><button className="button" type="submit">Create profile <span>↗</span></button></form>}
        <div className="dashboard-grid"><article className="dashboard-card dashboard-card-wide"><div className="card-heading"><span>Your consultations</span><span>{consultations.length}</span></div>{consultations.length === 0 ? <p>No consultation requests yet.</p> : consultations.map((consultation) => <div className="query-item" key={consultation.id}><div><Link to={`/consultations/${consultation.id}`}><strong>{consultation.subject}</strong></Link><small>{consultation.status} · {consultation.description}</small></div><div>{consultation.status === 'pending' && (role === 'consultant' ? <><button type="button" onClick={() => changeStatus(consultation.id, 'accept')}>Accept</button><button type="button" onClick={() => changeStatus(consultation.id, 'reject')}>Reject</button></> : <button type="button" onClick={() => changeStatus(consultation.id, 'cancel')}>Cancel</button>)}{consultation.status === 'accepted' && role === 'consultant' && <button type="button" onClick={() => changeStatus(consultation.id, 'start')}>Start</button>}{consultation.status === 'active' && <>{<button type="button" onClick={() => openChat(consultation.id)}>Open chat</button>}{role === 'consultant' && <button type="button" onClick={() => changeStatus(consultation.id, 'complete')}>Complete</button>}</>}{consultation.status === 'completed' && role !== 'consultant' && <button type="button" onClick={() => reviewConsultation(consultation.id)}>Submit feedback</button>}</div></div>)}</article><article className="dashboard-card"><div className="card-heading"><span>Search history</span><button type="button" onClick={async () => { await clearHistory(); setHistory([]) }}>Clear</button></div>{history.slice(0, 6).map((item) => <div className="query-item" key={item.id}><div><strong>{item.query}</strong><small>{item.answer?.slice(0, 80)}</small></div><button type="button" onClick={async () => { await deleteHistoryItem(item.id); await refresh() }}>×</button></div>)}</article></div>
        {selectedSession && <article className="dashboard-card chat-panel"><div className="card-heading"><span>Consultation chat</span><span>{selectedSession.status}</span></div><div className="chat-messages">{messages.map((message) => <p className={message.sender_id === selectedSession.user_id ? 'user' : 'assistant'} key={message.id}>{message.message}</p>)}</div><form onSubmit={sendMessage}><input value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} placeholder="Write a message" required /><button className="button" type="submit">Send</button></form></article>}
        <article className="dashboard-card"><div className="card-heading"><span>Feedback</span><span>1–5</span></div><label>Rating<select value={rating} onChange={(event) => setRating(event.target.value)}>{[1, 2, 3, 4, 5].map((value) => <option key={value}>{value}</option>)}</select></label><label>Comment<textarea value={comment} onChange={(event) => setComment(event.target.value)} rows="3" placeholder="Share what helped." /></label><small>Choose “Submit feedback” beside a completed consultation to submit it.</small></article>
    </section>
}

export default ConsultationsPage