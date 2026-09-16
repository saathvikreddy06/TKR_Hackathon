import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { askStandIQ } from './services/assistantService'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const initialMessage = {
    from: 'assistant',
    text: 'Hello. I can help you find a standard, understand certification, or locate a BIS service.',
    confidence: 'High',
    sources: [{ number: 'BIS source registry', title: 'Assistant scope and service directory', clause: 'Public service catalogue' }],
}

const initialMessageByLanguage = {
    en: initialMessage.text,
    te: 'నమస్కారం. ప్రమాణం కనుగొనడం, ధృవీకరణను అర్థం చేసుకోవడం లేదా BIS సేవను గుర్తించడంలో నేను సహాయం చేయగలను.',
    hi: 'नमस्कार। मैं मानक खोजने, प्रमाणन समझने या BIS सेवा ढूँढने में आपकी सहायता कर सकता हूँ।'
}

const assistantLanguages = [
    { code: 'en', label: 'English' },
    { code: 'te', label: 'తెలుగు' },
    { code: 'hi', label: 'हिन्दी' }
]

const UI_TRANSLATIONS = {
    en: {
        sources: 'Sources and evidence',
        certification: 'Certification',
        qco: 'QCO',
        yes: 'Yes',
        no: 'No',
        viewSource: 'View source',
        talkToConsultant: 'Talk to a consultant',
        responseLanguage: 'Response language'
    },
    te: {
        sources: 'మూలాలు మరియు ఆధారాలు',
        certification: 'ధృవీకరణ',
        qco: 'QCO',
        yes: 'అవును',
        no: 'కాదు',
        viewSource: 'మూలాన్ని చూడండి',
        talkToConsultant: 'సలహాదారునితో మాట్లాడండి',
        responseLanguage: 'సమాధాన భాష'
    },
    hi: {
        sources: 'स्रोत और प्रमाण',
        certification: 'प्रमाणन',
        qco: 'QCO',
        yes: 'हाँ',
        no: 'नहीं',
        viewSource: 'स्रोत देखें',
        talkToConsultant: 'सलाहकार से बात करें',
        responseLanguage: 'उत्तर की भाषा'
    }
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

function AnswerEvidence({ message, language }) {
    if (!message.confidence) return null

    const t = UI_TRANSLATIONS[language] || UI_TRANSLATIONS.en

    const uniqueSources = []
    const seen = new Set()

    for (const source of message.sources || []) {
        const key = [
            source.standard_number || source.number || source.id || '',
            source.part || '',
            source.year || '',
            source.lab_code || '',
            source.qco_document_id || '',
            source.source_url || source.document_url || ''
        ].join('|')

        if (seen.has(key)) continue

        seen.add(key)
        uniqueSources.push(source)
    }

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

            {uniqueSources.length > 0 && (
                <details className="source-panel">
                    <summary>
                        {t.sources} ({uniqueSources.length})
                    </summary>

                    {uniqueSources.map((source, index) => {
                        const standardNumber =
                            source.standard_number ||
                            source.number ||
                            source.id

                        const standardLabel = [
                            standardNumber,
                            source.part
                                ? `(${source.part})`
                                : '',
                            source.year
                                ? `:${source.year}`
                                : ''
                        ]
                            .filter(Boolean)
                            .join(' ')

                        const hasQCOStatus =
                            typeof source.mandatory_qco === 'boolean'

                        return (
                            <div
                                className="source-item"
                                key={`${standardLabel}-${source.lab_code || ''}-${source.qco_document_id || ''}-${index}`}
                            >
                                <strong>
                                    {standardLabel}
                                </strong>

                                <span>
                                    {language === 'en' &&
                                        source.title && (
                                            <span>
                                                {source.title}
                                            </span>
                                        )}

                                    <small>
                                        {source.scheme && (
                                            <>
                                                {t.certification}:{' '}
                                                {source.scheme}
                                            </>
                                        )}

                                        {hasQCOStatus && (
                                            <>
                                                {source.scheme
                                                    ? ' • '
                                                    : ''}
                                                {t.qco}:{' '}
                                                {source.mandatory_qco
                                                    ? t.yes
                                                    : t.no}
                                            </>
                                        )}

                                        {!hasQCOStatus &&
                                            source.qco_document_id && (
                                                <>
                                                    {source.scheme
                                                        ? ' • '
                                                        : ''}
                                                    {t.qco}:{' '}
                                                    {source.qco_document_id}
                                                </>
                                            )}

                                        {source.relationship && (
                                            <>
                                                {' • '}
                                                {source.relationship}
                                            </>
                                        )}

                                        {source.lab_name && (
                                            <>
                                                {' • '}
                                                {source.lab_name}
                                                {source.lab_code
                                                    ? ` (${source.lab_code})`
                                                    : ''}
                                            </>
                                        )}
                                    </small>
                                </span>

                                {getOfficialSourceUrl(source) && (
                                    <a
                                        href={getOfficialSourceUrl(source)}
                                        target="_blank"
                                        rel="noreferrer"
                                        aria-label={`${t.viewSource}: ${standardNumber || 'BIS'}`}
                                    >
                                        {t.viewSource}
                                    </a>
                                )}
                            </div>
                        )
                    })}
                </details>
            )}

            {message.confidence === 'Insufficient evidence' && (
                <Link
                    className="consultant-link"
                    to="/assistant"
                >
                    {t.talkToConsultant}
                </Link>
            )}
        </>
    )
}

function AssistantPage({ language = 'en', onLanguageChange }) {
    const [searchParams] = useSearchParams()
    const [message, setMessage] = useState('')
    const [messages, setMessages] = useState(() => [{
        ...initialMessage,
        text: initialMessageByLanguage[language] || initialMessage.text
    }])
    const [isThinking, setIsThinking] = useState(false)
    const [isListening, setIsListening] = useState(false)
    const [voiceSupported] = useState(() => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition))
    const recognitionRef = useRef(null)
    const conversationRef = useRef(null)

    useEffect(() => {
        const query = searchParams.get('query')
        if (query) setMessage(query)
    }, [searchParams])

    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
        if (!SpeechRecognition) return undefined
        const recognition = new SpeechRecognition()
        recognition.continuous = false
        recognition.interimResults = false
        recognition.lang = {
            en: 'en-IN',
            hi: 'hi-IN',
            te: 'te-IN'
        }[language] || 'en-IN'
        recognition.onresult = (event) => setMessage((currentMessage) => `${currentMessage} ${event.results[0][0].transcript}`.trim())
        recognition.onend = () => setIsListening(false)
        recognition.onerror = () => setIsListening(false)
        recognitionRef.current = recognition
        return () => recognition.stop()
    }, [language])

    useEffect(() => {
        const conversation = conversationRef.current
        if (!conversation) return

        conversation.scrollTo({
            top: conversation.scrollHeight,
            behavior: 'smooth'
        })
    }, [messages, isThinking])

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
            const data = await askStandIQ(trimmedMessage, language)

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
            recognitionRef.current.lang = {
                en: 'en-IN',
                hi: 'hi-IN',
                te: 'te-IN'
            }[language] || 'en-IN'
            setIsListening(true)
            recognitionRef.current.start()
        }
    }

    return <section className="assistant-page">
        <div className="assistant-topline"><Link className="back-link" to="/">Back to home</Link><span className="assistant-status"><i></i> BIS assistant online</span></div>
        <div className="assistant-intro"><p className="eyebrow"><span></span> Your BIS guide</p><h1>Ask with <em>confidence.</em></h1><p>Describe a product, standard, certification question, or hallmarking need. Use text or your voice.</p><label className="assistant-language-picker" htmlFor="assistant-language">{(UI_TRANSLATIONS[language] || UI_TRANSLATIONS.en).responseLanguage}<select id="assistant-language" value={language} onChange={(event) => onLanguageChange?.(event.target.value)}>{assistantLanguages.map((option) => <option key={option.code} value={option.code}>{option.label}</option>)}</select></label></div>
        <div className="assistant-window">
            <div className="assistant-window-head"><div className="assistant-head-identity"><img src="/logo.jpeg" alt="standIQ logo" /><span><strong>standIQ assistant</strong><small>Source-backed guidance for Indian standards</small></span></div><span className="header-sparkle">*</span></div>
            <div ref={conversationRef} className="assistant-conversation" aria-live="polite">{messages.map((chatMessage, index) => <div className={`assistant-message ${chatMessage.from}`} key={`${chatMessage.from}-${index}`}><span className="message-label">{chatMessage.from === 'assistant' ? <><span className="assistant-avatar">*</span> standIQ</> : 'You'}</span><div className="message-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {chatMessage.text}
                </ReactMarkdown>
            </div><AnswerEvidence message={chatMessage} language={language} /></div>)}{isThinking && <div className="assistant-message assistant thinking-message"><span className="message-label"><span className="assistant-avatar">*</span> standIQ</span><p className="typing-indicator" aria-label="Assistant is thinking"><i></i><i></i><i></i></p></div>}</div>
            <div className="suggestion-row"><button type="button" onClick={() => setMessage('Which BIS standard applies to my product?')}>Find a product standard</button><button type="button" onClick={() => setMessage('How do I apply for BIS certification?')}>Understand certification</button><button type="button" onClick={() => setMessage('How does hallmarking work?')}>Learn about hallmarking</button></div>
            <form className="assistant-composer" onSubmit={sendMessage}><textarea value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder="Ask anything about BIS standards..." aria-label="Ask the BIS assistant" rows="1" /><div className="composer-actions"><span className="voice-hint">{voiceSupported ? (isListening ? 'Listening...' : 'Text or voice input') : 'Voice input is not supported in this browser'}</span><button className={`voice-button ${isListening ? 'listening' : ''}`} type="button" onClick={toggleListening} disabled={!voiceSupported} aria-label={isListening ? 'Stop voice input' : 'Start voice input'}><span className="mic-icon" aria-hidden="true"></span></button><button className="send-button" type="submit" aria-label="Send message">&uarr;</button></div></form>
        </div>
        <p className="assistant-disclaimer">standIQ can make mistakes. Check important information against official BIS sources.</p>
    </section>
}

export default AssistantPage