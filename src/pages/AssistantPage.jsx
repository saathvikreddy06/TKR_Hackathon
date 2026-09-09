import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

const initialMessage = { from: 'assistant', text: 'Hello. I can help you find a standard, understand certification, or locate a BIS service.' }

function AssistantPage() {
    const [message, setMessage] = useState('')
    const [messages, setMessages] = useState([initialMessage])
    const [isThinking, setIsThinking] = useState(false)
    const [isListening, setIsListening] = useState(false)
    const [voiceSupported] = useState(() => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition))
    const recognitionRef = useRef(null)

    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
        if (!SpeechRecognition) return undefined
        const recognition = new SpeechRecognition()
        recognition.continuous = false
        recognition.interimResults = false
        recognition.lang = 'en-IN'
        recognition.onresult = (event) => setMessage((currentMessage) => `${currentMessage} ${event.results[0][0].transcript}`.trim())
        recognition.onend = () => setIsListening(false)
        recognition.onerror = () => setIsListening(false)
        recognitionRef.current = recognition
        return () => recognition.stop()
    }, [])

    const sendMessage = (event) => {
        event.preventDefault()
        const trimmedMessage = message.trim()
        if (!trimmedMessage) return
        setMessages((currentMessages) => [...currentMessages, { from: 'user', text: trimmedMessage }])
        setMessage('')
        setIsThinking(true)
        window.setTimeout(() => {
            setMessages((currentMessages) => [...currentMessages, { from: 'assistant', text: 'I am ready to help with BIS standards and services. Try asking about certification, a product standard, or hallmarking.' }])
            setIsThinking(false)
        }, 650)
    }

    const toggleListening = () => {
        if (!recognitionRef.current) return
        if (isListening) recognitionRef.current.stop()
        else {
            setIsListening(true)
            recognitionRef.current.start()
        }
    }

    return <section className="assistant-page"><div className="assistant-topline"><Link className="back-link" to="/">← Back to home</Link><span className="assistant-status"><i></i> BIS assistant online</span></div><div className="assistant-intro"><p className="eyebrow"><span></span> Your BIS guide</p><h1>Ask with <em>confidence.</em></h1><p>Describe a product, standard, certification question, or hallmarking need. Use text or your voice.</p></div><div className="assistant-window"><div className="assistant-window-head"><div className="assistant-head-identity"><img src="/logo.jpeg" alt="standIQ logo" /><span><strong>standIQ assistant</strong><small>Source-backed guidance for Indian standards</small></span></div><span className="header-sparkle">✦</span></div><div className="assistant-conversation">{messages.map((chatMessage, index) => <div className={`assistant-message ${chatMessage.from}`} key={`${chatMessage.from}-${index}`}><span className="message-label">{chatMessage.from === 'assistant' ? <><span className="assistant-avatar">✦</span> standIQ</> : 'You'}</span><p>{chatMessage.text}</p></div>)}{isThinking && <div className="assistant-message assistant thinking-message"><span className="message-label"><span className="assistant-avatar">✦</span> standIQ</span><p className="typing-indicator" aria-label="Assistant is thinking"><i></i><i></i><i></i></p></div>}</div><div className="suggestion-row"><button type="button" onClick={() => setMessage('Which BIS standard applies to my product?')}>Find a product standard</button><button type="button" onClick={() => setMessage('How do I apply for BIS certification?')}>Understand certification</button><button type="button" onClick={() => setMessage('How does hallmarking work?')}>Learn about hallmarking</button></div><form className="assistant-composer" onSubmit={sendMessage}><textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Ask anything about BIS standards..." aria-label="Ask the BIS assistant" rows="1" /><div className="composer-actions"><span className="voice-hint">{voiceSupported ? (isListening ? 'Listening...' : 'Text or voice input') : 'Voice input is not supported in this browser'}</span><button className={`voice-button ${isListening ? 'listening' : ''}`} type="button" onClick={toggleListening} disabled={!voiceSupported} aria-label={isListening ? 'Stop voice input' : 'Start voice input'}>{isListening ? '■' : '⌕'}</button><button className="send-button" type="submit" aria-label="Send message">↑</button></div></form></div><p className="assistant-disclaimer">standIQ can make mistakes. Check important information against official BIS sources.</p></section>
}

export default AssistantPage
