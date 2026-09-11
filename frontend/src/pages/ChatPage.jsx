import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getChatMessages, getChatSession, sendChatMessage, closeChatSession } from './services/chatService'

function ChatPage() {
    const { sessionId } = useParams()
    const [session, setSession] = useState(null)
    const [messages, setMessages] = useState([])
    const [message, setMessage] = useState('')
    const [error, setError] = useState('')

    const refresh = async () => {
        try {
            const [sessionData, messageData] = await Promise.all([getChatSession(sessionId), getChatMessages(sessionId)])
            setSession(sessionData)
            setMessages(messageData.messages || [])
        } catch (requestError) { setError(requestError.message) }
    }

    useEffect(() => { refresh() }, [sessionId])

    const send = async (event) => {
        event.preventDefault()
        if (!message.trim()) return
        try { await sendChatMessage(sessionId, message); setMessage(''); await refresh() } catch (requestError) { setError(requestError.message) }
    }

    const close = async () => {
        try { await closeChatSession(sessionId); await refresh() } catch (requestError) { setError(requestError.message) }
    }

    if (error) return <section className="data-page"><p className="auth-error">{error}</p><Link to="/consultations">Back to consultations</Link></section>
    if (!session) return <section className="data-page"><p>Loading chat...</p></section>

    return <section className="data-page chat-page"><Link className="back-link" to="/consultations">Back to consultations</Link><div className="page-intro-row"><div><p className="eyebrow"><span></span> Private consultation chat</p><h1>Work through the details together.</h1><p>Only the user and consultant attached to this consultation can access these messages.</p></div><span className="status-badge status-current">{session.status}</span></div><article className="dashboard-card chat-panel"><div className="chat-messages">{messages.length === 0 ? <p>No messages yet.</p> : messages.map((item) => <div className="query-item" key={item.id}><div><strong>{item.sender_role}</strong><p>{item.message}</p></div></div>)}</div>{session.status === 'active' ? <form onSubmit={send}><input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Write a message" required /><button className="button" type="submit">Send <span>↗</span></button><button type="button" onClick={close}>Close chat</button></form> : <p>This chat is closed.</p>}</article></section>
}

export default ChatPage
