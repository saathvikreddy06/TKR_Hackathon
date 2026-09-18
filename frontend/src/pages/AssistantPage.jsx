import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { askStandIQ } from './services/assistantService'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const initialMessage = {
    from: 'assistant',
    text: 'Hello. I can help you find a standard, understand certification, or locate a BIS service.',
    confidence: 'High',
    sources: [],
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
        , basedOn: 'Based on retrieved BIS data'
        , evidenceIncomplete: 'Some information could not be verified from the available BIS records.'
        , copyAnswer: 'Copy answer'
        , copied: 'Copied'
        , evidence: 'Evidence'
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
        , basedOn: 'प्राप्त BIS डेटा पर आधारित'
        , evidenceIncomplete: 'कुछ जानकारी उपलब्ध BIS रिकॉर्ड से सत्यापित नहीं हो सकी।'
        , copyAnswer: 'उत्तर कॉपी करें'
        , copied: 'कॉपी किया गया'
        , evidence: 'प्रमाण'
    }
}

function getOfficialSourceUrl(source) {
    return source.url || source.document_url || source.source_url || null
}

function copyText(value, setCopied) {
    if (!value || !navigator.clipboard) return
    navigator.clipboard.writeText(value).then(() => {
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1600)
    })
}

function buildCategorySections(message) {
    const sections = []

    if (message.knowledge?.length > 0) {
        sections.push({
            type: 'overview',
            title: 'Overview',
            content: message.knowledge
                .slice(0, 3)
                .map((item) => item.text || item.title || item.description)
                .filter(Boolean)
                .join('\n\n')
        })
    }

    if (message.standards?.length > 0) {
        sections.push({
            type: 'standards',
            title: 'Relevant Standards',
            items: message.standards.slice(0, 12).map((item) => ({
                standard_number: item.standard_number || item.is_number || item.number,
                title: item.title || item.name || 'BIS standard',
                description: item.description || item.summary || item.text || 'Retrieved BIS standard record.',
                evidence_id: item.document_id || item.chunk_id || item.standard_id
            }))
        })
    }

    if (message.tests?.length > 0) {
        sections.push({
            type: 'testing',
            title: 'Testing & Requirements',
            content: 'Testing evidence retrieved from BIS LIMS records.',
            tests: message.tests.slice(0, 50).map((item) => ({
                standard_number: item.standard_number || item.indian_standard_no,
                product: item.product || item.designation || 'BIS test record',
                designation: item.designation,
                lab_name: item.lab_name,
                lab_code: item.lab_code,
                evidence: item.clause_raw || item.testing_charge_raw || item.remark || 'Verified BIS LIMS test relationship.'
            }))
        })
    }

    if (message.laboratories?.length > 0) {
        sections.push({
            type: 'laboratories',
            title: 'BIS Laboratories',
            content: 'Laboratories linked through verified BIS LIMS relationships.',
            labs: message.laboratories.slice(0, 20).map((item) => ({
                lab_name: item.lab_name,
                lab_code: item.lab_code,
                capability: item.capability || item.product || item.relevant_test,
                standard_number: item.standard_number || item.indian_standard_no
            }))
        })
    }

    if (message.qcos?.length > 0) {
        sections.push({
            type: 'qco',
            title: 'QCO / Regulatory Information',
            content: 'QCO relationships retrieved from the BIS relationship dataset.',
            qcos: message.qcos.slice(0, 20).map((item) => ({
                qco_document_id: item.qco_document_id,
                relationship: item.relationship,
                evidence: item.evidence,
                standard_number: item.standard_number
            }))
        })
    }

    return sections
}

function StructuredResponse({ message, language, onFollowup }) {
    const t = UI_TRANSLATIONS[language] || UI_TRANSLATIONS.en
    const [copied, setCopied] = useState(false)

    if (!message.confidence) return null

    const uniqueSources = []
    const seen = new Set()

    for (const source of message.sources || []) {
        const key = [
            source.standard_number || source.number || source.id || source.identifier || '',
            source.part || '',
            source.year || '',
            source.lab_code || '',
            source.qco_document_id || '',
            source.source_url || source.document_url || source.url || ''
        ].join('|')

        if (seen.has(key)) continue

        seen.add(key)
        uniqueSources.push(source)
    }

    const sections = message.sections?.length > 0
        ? message.sections
        : buildCategorySections(message)

    const renderSectionBody = (section) => {
        if (!section) return null

        if (section.type === 'standards' && Array.isArray(section.items)) {
            return (
                <div className="section-grid">
                    {section.items.map((item) => (
                        <article className="standard-card" key={`${item.standard_number || item.title}-${item.evidence_id || item.description}`}>
                            <div className="card-headline">
                                <span className="card-label">{item.standard_number || 'BIS record'}</span>
                            </div>
                            <h4>{item.title || 'BIS record'}</h4>
                            <p>{item.description || 'No description was available in the retrieved evidence.'}</p>
                            {item.evidence_id && <small className="evidence-meta">Evidence ID: {item.evidence_id}</small>}
                        </article>
                    ))}
                </div>
            )
        }

        if (section.type === 'testing' && Array.isArray(section.tests)) {
            return (
                <div>
                    {section.content && <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>}
                    {section.tests.length > 0 && (
                        <div className="section-grid">
                            {section.tests.map((test, index) => (
                                <article className="standard-card" key={`${test.standard_number}-${test.product}-${index}`}>
                                    <div className="card-headline"><span className="card-label">{test.standard_number || 'Standard'}</span></div>
                                    <h4>{test.product || 'Test record'}</h4>
                                    {test.designation && <p><strong>Designation:</strong> {test.designation}</p>}
                                    {(test.lab_name || test.lab_code) && <p><strong>Lab:</strong> {test.lab_name || 'Lab'} {test.lab_code ? `(${test.lab_code})` : ''}</p>}
                                    <p>{test.evidence || 'Test evidence was not available in the retrieved records.'}</p>
                                </article>
                            ))}
                        </div>
                    )}
                </div>
            )
        }

        if (section.type === 'laboratories' && Array.isArray(section.labs)) {
            if (section.labs.length === 0) {
                return <p>{section.content}</p>
            }

            return (
                <div className="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Laboratory</th>
                                <th>Lab Code</th>
                                <th>Relevant Capability</th>
                                <th>Standard</th>
                            </tr>
                        </thead>
                        <tbody>
                            {section.labs.map((lab, index) => (
                                <tr key={`${lab.lab_name}-${lab.lab_code}-${index}`}>
                                    <td>{lab.lab_name || 'BIS laboratory'}</td>
                                    <td>{lab.lab_code || '-'}</td>
                                    <td>{lab.capability || 'Laboratory information available in retrieved BIS records.'}</td>
                                    <td>{lab.standard_number || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )
        }

        if (section.type === 'qco' && Array.isArray(section.qcos)) {
            if (section.qcos.length === 0) {
                return <p>{section.content}</p>
            }

            return (
                <div className="section-grid">
                    {section.qcos.map((qco, index) => (
                        <article className="standard-card" key={`${qco.qco_document_id || qco.relationship || 'qco'}-${index}`}>
                            <div className="card-headline"><span className="card-label">{qco.qco_document_id || 'QCO record'}</span></div>
                            <h4>{qco.relationship || 'QCO relationship'}</h4>
                            <p><strong>Standard:</strong> {qco.standard_number || 'Not provided'}</p>
                            <p>{qco.evidence || 'No evidence text was retrieved.'}</p>
                        </article>
                    ))}
                </div>
            )
        }

        if (section.type === 'certification' || section.type === 'related' || section.type === 'overview') {
            return <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content || ''}</ReactMarkdown>
        }

        if (typeof section.content === 'string') {
            return <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
        }

        return null
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
                {message.evidenceStatus === 'supported' && (
                    <span className="evidence-badge">{t.basedOn}</span>
                )}
            </div>

            {message.title && <h2 className="structured-title">{message.title}</h2>}
            {message.summary && <p className="structured-summary">{message.summary}</p>}

            {message.evidenceStatus === 'insufficient' && (
                <p className="evidence-note">{t.evidenceIncomplete}</p>
            )}

            <div className="answer-actions">
                <button type="button" onClick={() => copyText(message.text || message.answer || '', setCopied)}>
                    {copied ? t.copied : t.copyAnswer}
                </button>
            </div>

            {sections.length > 0 && (
                <div className="structured-sections">
                    {sections.map((section) => (
                        <section className="structured-section" key={`${section.title}-${section.type}`}>
                            <h3>{section.title}</h3>
                            {renderSectionBody(section)}
                        </section>
                    ))}
                </div>
            )}

            {uniqueSources.length > 0 && (
                <details className="source-panel">
                    <summary>
                        {t.sources} ({uniqueSources.length})
                    </summary>

                    {uniqueSources.map((source, index) => {
                        const standardNumber =
                            source.standard_number ||
                            source.number ||
                            source.identifier ||
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

                        const sourceText = source.evidence || source.title || source.identifier || ''
                        const sourceUrl = source.url || source.source_url || source.document_url || getOfficialSourceUrl(source)

                        return (
                            <div
                                className="source-item"
                                key={`${standardLabel}-${source.lab_code || ''}-${source.qco_document_id || ''}-${index}`}
                            >
                                <span className="source-type-badge">{source.type || 'source'}</span>

                                <span>
                                    <strong>{standardLabel || source.title || source.identifier || 'BIS record'}</strong>
                                    {source.title && standardLabel && <span>{source.title}</span>}

                                    <small>
                                        {source.source && <>{source.source} </>}
                                        {source.lab_name && <>• {source.lab_name} </>}
                                        {source.lab_code && <>• Lab {source.lab_code} </>}
                                        {source.qco_document_id && <>• QCO {source.qco_document_id}</>}
                                    </small>
                                </span>

                                {sourceText && (
                                    <details className="source-evidence">
                                        <summary>{t.evidence}</summary>
                                        <p>{sourceText}</p>
                                    </details>
                                )}

                                {sourceUrl ? (
                                    <a
                                        className="source-item-link"
                                        href={sourceUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                        aria-label={`${t.viewSource}: ${standardNumber || 'BIS'}`}
                                    >
                                        {t.viewSource}
                                    </a>
                                ) : (
                                    <span className="source-unavailable">No direct official link available</span>
                                )}
                            </div>
                        )
                    })}
                </details>
            )}

            {message.followups?.length > 0 && (
                <div className="followup-row">
                    {message.followups.map((followup) => (
                        <button type="button" key={followup.query} onClick={() => onFollowup(followup.query)}>
                            {followup.label}
                        </button>
                    ))}
                </div>
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
                    answer: data.answer,
                    title: data.title,
                    summary: data.summary,
                    confidence: data.in_scope ? 'High' : 'Insufficient evidence',
                    sources: data.in_scope ? (data.sources || []) : [],
                    sections: data.sections || [],
                    standards: data.in_scope ? (data.standards || []) : [],
                    tests: data.in_scope ? (data.tests || []) : [],
                    laboratories: data.in_scope ? (data.laboratories || []) : [],
                    qcos: data.in_scope ? (data.qcos || []) : [],
                    knowledge: data.in_scope ? (data.knowledge || []) : [],
                    structuredStatus: data.structured_status,
                    qcoStatus: data.qco_status,
                    evidenceStatus: data.evidence_status || 'supported',
                    followups: data.followups || [],
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
                    sources: [],
                    sections: [],
                    followups: []
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
            <div ref={conversationRef} className="assistant-conversation" aria-live="polite">{messages.map((chatMessage, index) => <div className={`assistant-message ${chatMessage.from}`} key={`${chatMessage.from}-${index}`}><span className="message-label">{chatMessage.from === 'assistant' ? <><span className="assistant-avatar">*</span> standIQ</> : 'You'}</span>{(chatMessage.from === 'user' || (!chatMessage.sections?.length && !chatMessage.standards?.length && !chatMessage.tests?.length && !chatMessage.laboratories?.length && !chatMessage.qcos?.length)) && <div className="message-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {chatMessage.text}
                </ReactMarkdown>
            </div>}<StructuredResponse message={chatMessage} language={language} onFollowup={setMessage} /></div>)}{isThinking && <div className="assistant-message assistant thinking-message"><span className="message-label"><span className="assistant-avatar">*</span> standIQ</span><p className="typing-indicator" aria-label="Assistant is thinking"><i></i><i></i><i></i></p></div>}</div>
            <div className="suggestion-row"><button type="button" onClick={() => setMessage('Which BIS standard applies to my product?')}>Find a product standard</button><button type="button" onClick={() => setMessage('How do I apply for BIS certification?')}>Understand certification</button><button type="button" onClick={() => setMessage('How does hallmarking work?')}>Learn about hallmarking</button></div>
            <form className="assistant-composer" onSubmit={sendMessage}><textarea value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder="Ask anything about BIS standards..." aria-label="Ask the BIS assistant" rows="1" /><div className="composer-actions"><span className="voice-hint">{voiceSupported ? (isListening ? 'Listening...' : 'Text or voice input') : 'Voice input is not supported in this browser'}</span><button className={`voice-button ${isListening ? 'listening' : ''}`} type="button" onClick={toggleListening} disabled={!voiceSupported} aria-label={isListening ? 'Stop voice input' : 'Start voice input'}><span className="mic-icon" aria-hidden="true"></span></button><button className="send-button" type="submit" aria-label="Send message">&uarr;</button></div></form>
        </div>
        <p className="assistant-disclaimer">standIQ can make mistakes. Check important information against official BIS sources.</p>
    </section>
}

export default AssistantPage