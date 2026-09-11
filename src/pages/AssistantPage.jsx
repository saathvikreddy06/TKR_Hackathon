import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { askStandIQ } from './services/assistantService'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const initialMessage = {
    from: 'assistant',
    text: 'Hello. I can help you find a standard, understand certification, or locate a BIS service.',
    confidence: 'High',
    sources: [{ number: 'BIS source registry', title: 'Assistant scope and service directory', clause: 'Public service catalogue' }],
}

function detectAssistantLanguage(text) {
    if (/[\u0c00-\u0c7f]/u.test(text)) return 'te-IN'
    if (/[\u0900-\u097f]/u.test(text)) return 'hi-IN'
    return 'en-IN'
}

function getOfficialSourceUrl(source) {
    if (source.document_url) return source.document_url
    if (source.source_url) return source.source_url

    const searchTerm = [source.standard_number, source.title]
        .filter(Boolean)
        .join(' ')

    if (!searchTerm) return null

    return `https://standards.bis.gov.in/website/know-your-standards?search=${encodeURIComponent(searchTerm)}`
}

function AnswerEvidence({ message }) {
    if (!message.confidence) return null

    return (
        <>
            <div className="answer-meta">
                <span
                    className={`confidence-badge ${message.confidence === 'High'
                        ? 'confidence-high'
                        : 'confidence-low'
                        }`}
                >
                    {message.confidence}
                </span>

                {message.languageName && (
                    <span className="language-badge">
                        {message.languageName}
                    </span>
                )}

                {message.verdict && (
                    <span className="verdict-badge">
                        {message.verdict}
                    </span>
                )}
            </div>

            {message.sources?.length > 0 && (
                <details className="source-panel">
                    <summary>
                        Sources and evidence ({message.sources.length})
                    </summary>

                    {message.sources.map((source, index) => (
                        <div
                            className="source-item"
                            key={`${source.standard_number}-${source.year}-${index}`}
                        >
                            <strong>
                                {source.standard_number}
                                {source.part
                                    ? ` (${source.part})`
                                    : ''}
                                {source.year
                                    ? `:${source.year}`
                                    : ''}
                            </strong>

                            <span>
                                {source.title}

                                <small>
                                    {source.scheme
                                        ? `Certification: ${source.scheme}`
                                        : ''}

                                    {source.mandatory_qco !== undefined
                                        ? ` • QCO: ${source.mandatory_qco
                                            ? 'Yes'
                                            : 'No'
                                        }`
                                        : ''}
                                </small>
                            </span>

                            {getOfficialSourceUrl(source) && (
                                <a
                                    href={getOfficialSourceUrl(source)}
                                    target="_blank"
                                    rel="noreferrer"
                                    aria-label={`Open ${source.standard_number || source.title || 'BIS source'} on the official BIS website`}
                                >
                                    View source
                                </a>
                            )}
                        </div>
                    ))}
                </details>
            )}

            {message.confidence === 'Insufficient evidence' && (
                <Link
                    className="consultant-link"
                    to="/assistant"
                >
                    Talk to a consultant
                </Link>
            )}
        </>
    )
}

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

    const sendMessage = async (event) => {
        event.preventDefault()

        const trimmedMessage = message.trim()

        if (!trimmedMessage || isThinking) return

        // Add user's message to the conversation
        setMessages((currentMessages) => [
            ...currentMessages,
            {
                from: 'user',
                text: trimmedMessage
            }
        ])

        setMessage('')
        setIsThinking(true)

        try {
            // Send query to the real StandIQ backend
            const data = await askStandIQ(trimmedMessage)

            // Add backend response to the conversation
            setMessages((currentMessages) => [
                ...currentMessages,
                {
                    from: 'assistant',
                    text: data.answer,
                    confidence: data.in_scope ? 'High' : 'Insufficient evidence',
                    sources: data.in_scope ? (data.sources || []) : [],
                    languageName: data.language_name
                }
            ])
        } catch (error) {
            console.error('StandIQ API error:', error)

            setMessages((currentMessages) => [
                ...currentMessages,
                {
                    from: 'assistant',
                    text: 'Sorry, I could not connect to the StandIQ backend. Please make sure the backend server is running and try again.',
                    confidence: 'Insufficient evidence',
                    verdict: 'Backend connection error',
                    sources: []
                }
            ])
        } finally {
            setIsThinking(false)
        }
    }
    const handleComposerKeyDown = (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            sendMessage(event)
        }
    }

    const toggleListening = () => {
        if (!recognitionRef.current) return
        if (isListening) recognitionRef.current.stop()
        else {
            recognitionRef.current.lang = detectAssistantLanguage(message)
            setIsListening(true)
            recognitionRef.current.start()
        }
    }

    return <section className="assistant-page">
        <div className="assistant-topline"><Link className="back-link" to="/">Back to home</Link><span className="assistant-status"><i></i> BIS assistant online</span></div>
        <div className="assistant-intro"><p className="eyebrow"><span></span> Your BIS guide</p><h1>Ask with <em>confidence.</em></h1><p>Describe a product, standard, certification question, or hallmarking need. Use text or your voice.</p></div>
        <div className="assistant-window">
            <div className="assistant-window-head"><div className="assistant-head-identity"><img src="/logo.jpeg" alt="standIQ logo" /><span><strong>standIQ assistant</strong><small>Source-backed guidance for Indian standards</small></span></div><span className="header-sparkle">*</span></div>
            <div className="assistant-conversation" aria-live="polite">{messages.map((chatMessage, index) => <div className={`assistant-message ${chatMessage.from}`} key={`${chatMessage.from}-${index}`}><span className="message-label">{chatMessage.from === 'assistant' ? <><span className="assistant-avatar">*</span> standIQ</> : 'You'}</span><div className="message-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {chatMessage.text}
                </ReactMarkdown>
            </div><AnswerEvidence message={chatMessage} /></div>)}{isThinking && <div className="assistant-message assistant thinking-message"><span className="message-label"><span className="assistant-avatar">*</span> standIQ</span><p className="typing-indicator" aria-label="Assistant is thinking"><i></i><i></i><i></i></p></div>}</div>
            <div className="suggestion-row"><button type="button" onClick={() => setMessage('Which BIS standard applies to my product?')}>Find a product standard</button><button type="button" onClick={() => setMessage('How do I apply for BIS certification?')}>Understand certification</button><button type="button" onClick={() => setMessage('How does hallmarking work?')}>Learn about hallmarking</button></div>
            <form className="assistant-composer" onSubmit={sendMessage}><textarea value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder="Ask anything about BIS standards..." aria-label="Ask the BIS assistant" rows="1" /><div className="composer-actions"><span className="voice-hint">{voiceSupported ? (isListening ? 'Listening...' : 'Text or voice input') : 'Voice input is not supported in this browser'}</span><button className={`voice-button ${isListening ? 'listening' : ''}`} type="button" onClick={toggleListening} disabled={!voiceSupported} aria-label={isListening ? 'Stop voice input' : 'Start voice input'}><span className="mic-icon" aria-hidden="true"></span></button><button className="send-button" type="submit" aria-label="Send message">&uarr;</button></div></form>
        </div>
        <p className="assistant-disclaimer">standIQ can make mistakes. Check important information against official BIS sources.</p>
    </section>
}

export default AssistantPage