import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listConsultants } from './services/consultancyService'
import { createConsultation } from './services/consultationService'

const laboratories = [
    { name: 'Electrical Research & Development Association', location: 'Vadodara, Gujarat', type: 'BIS-recognized', tests: 'Electrical safety · LED · cables', status: 'Verified' },
    { name: 'Central Food Technological Research Institute', location: 'Mysuru, Karnataka', type: 'NABL accredited', tests: 'Food · water · microbiology', status: 'Verified' },
    { name: 'National Test House', location: 'Kolkata, West Bengal', type: 'BIS-recognized', tests: 'Construction · chemicals · materials', status: 'Verified' },
    { name: 'Textile Committee Testing Centre', location: 'Mumbai, Maharashtra', type: 'NABL accredited', tests: 'Textiles · garments · fibres', status: 'Pending verification' },
]

const content = {
    laboratories: { eyebrow: 'Testing network', title: 'Find a testing laboratory.', intro: 'Explore sample laboratory records by location, accreditation, and testing capability. Confirm scope and availability with the laboratory before commissioning work.', cta: 'Ask the assistant', route: '/assistant' },
    consultants: { eyebrow: 'Human expertise', title: 'Consultants', intro: 'Find the right guidance for your BIS-related requirements. Connect with registered consultants for expert assistance.', cta: 'View my consultations', route: '/consultations' },
}

function SourceTag() {
    return <small className="source-tag">◉ BIS official registry · preview</small>
}

function initials(name = '') {
    return name.split(' ').filter(Boolean).map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'C'
}

function friendlyRequestError(error) {
    if (error.message?.toLowerCase().includes('pending consultation')) {
        return 'You already have a pending consultation request with this consultant.'
    }
    if (error.message?.toLowerCase().includes('inactive')) {
        return 'This consultant is currently unavailable for new requests.'
    }
    return 'Unable to send your consultation request. Please try again.'
}

function ConsultationRequest({ consultant, onClose, onSuccess }) {
    const [subject, setSubject] = useState('')
    const [description, setDescription] = useState('')
    const [validationError, setValidationError] = useState('')
    const [requestError, setRequestError] = useState('')
    const [sending, setSending] = useState(false)

    const submit = async (event) => {
        event.preventDefault()
        if (subject.trim().length < 2) {
            setValidationError('Please enter a subject for your request.')
            return
        }
        if (description.trim().length < 2) {
            setValidationError('Please describe what you need help with.')
            return
        }
        setValidationError('')
        setRequestError('')
        setSending(true)
        try {
            await createConsultation({ consultant_id: consultant.id, subject: subject.trim(), description: description.trim() })
            onSuccess()
        } catch (error) {
            setRequestError(friendlyRequestError(error))
        } finally {
            setSending(false)
        }
    }

    return <div className="consultant-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
        <section className="consultant-modal" role="dialog" aria-modal="true" aria-labelledby="request-consultation-title">
            <button className="consultant-modal-close" type="button" onClick={onClose} aria-label="Close request form">×</button>
            <p className="eyebrow"><span></span> Consultation request</p>
            <h2 id="request-consultation-title">Request consultation</h2>
            <p className="consultant-modal-consultant">Consultant: <strong>{consultant.name}</strong></p>
            <form onSubmit={submit}>
                <label htmlFor="consultation-subject">Subject / requirement <span>*</span></label>
                <input id="consultation-subject" value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="What do you need help with?" required />
                <label htmlFor="consultation-description">Describe your requirement <span>*</span></label>
                <textarea id="consultation-description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Share the BIS requirement, product, or standard you want to discuss." rows="5" required />
                {(validationError || requestError) && <p className="consultant-form-error" role="alert">{validationError || requestError}</p>}
                <div className="consultant-modal-actions"><button className="text-button" type="button" onClick={onClose}>Cancel</button><button className="button" type="submit" disabled={sending}>{sending ? 'Sending...' : 'Send request'} <span>↗</span></button></div>
            </form>
        </section>
    </div>
}

function ConsultantCard({ consultant, onRequest }) {
    const expertise = consultant.expertise || []
    const categories = consultant.categories || []
    const hasAvailability = typeof consultant.availability === 'boolean'
    return <article className="consultant-card consultant-card-polished">
        <div className="consultant-card-top"><div className="consultant-avatar">{initials(consultant.name)}</div>{hasAvailability && <span className={`status-badge status-${consultant.availability ? 'current' : 'pending'}`}>{consultant.availability ? 'Available' : 'Currently unavailable'}</span>}</div>
        <div className="consultant-card-head"><div><h2>{consultant.consultancy_name || consultant.name}</h2><span>{consultant.name}{consultant.place ? ` · ${consultant.place}` : ''}</span></div></div>
        {(expertise.length > 0 || categories.length > 0) && <div className="consultant-tags">{[...expertise, ...categories].slice(0, 4).map((item) => <span key={item}>{item}</span>)}</div>}
        <p>{consultant.bio || 'Review this consultant profile to understand their available BIS expertise.'}</p>
        <div className="consultant-card-actions"><Link className="card-link" to={`/consultants/${consultant.id}`}>View profile <span>→</span></Link><button className="button button-small" type="button" onClick={() => onRequest(consultant)}>Request <span>↗</span></button></div>
    </article>
}

function DiscoveryPage({ type }) {
    const page = content[type]
    const [consultants, setConsultants] = useState([])
    const [loading, setLoading] = useState(type === 'consultants')
    const [error, setError] = useState('')
    const [search, setSearch] = useState('')
    const [filter, setFilter] = useState('All')
    const [selectedConsultant, setSelectedConsultant] = useState(null)
    const [confirmation, setConfirmation] = useState('')

    useEffect(() => {
        if (type !== 'consultants') return undefined
        listConsultants()
            .then((data) => setConsultants(data.consultants || []))
            .catch(() => setError('Unable to load consultants. Please try again.'))
            .finally(() => setLoading(false))
        return undefined
    }, [type])

    const filters = useMemo(() => ['All', ...new Set(consultants.flatMap((consultant) => [...(consultant.expertise || []), ...(consultant.categories || [])]))], [consultants])
    const filteredConsultants = useMemo(() => {
        const term = search.trim().toLowerCase()
        return consultants.filter((consultant) => {
            const fields = [consultant.name, consultant.bio, ...(consultant.expertise || []), ...(consultant.categories || []), ...(consultant.standards_handled || [])].filter(Boolean).join(' ').toLowerCase()
            const matchesSearch = !term || fields.includes(term)
            const matchesFilter = filter === 'All' || [...(consultant.expertise || []), ...(consultant.categories || [])].some((item) => item.toLowerCase() === filter.toLowerCase())
            return matchesSearch && matchesFilter
        })
    }, [consultants, filter, search])

    if (type !== 'consultants') return <section className={`data-page discovery-page discovery-${type}`}><div className="page-intro-row"><div><p className="eyebrow"><span></span> {page.eyebrow}</p><h1>{page.title}</h1><p>{page.intro}</p></div><Link className="button" to={page.route}>{page.cta} <span>↗</span></Link></div><div className="lab-list">{laboratories.map((lab) => <article className="lab-card" key={lab.name}><div className="lab-map-pin" aria-hidden="true">⌖</div><div className="lab-card-body"><div className="card-heading"><div><h2>{lab.name}</h2><span>{lab.location}</span></div><span className={`status-badge status-${lab.status === 'Verified' ? 'current' : 'pending'}`}>{lab.status}</span></div><div className="lab-details"><span>{lab.type}</span><span>{lab.tests}</span></div><SourceTag /></div></article>)}</div><p className="page-disclaimer">Laboratory records shown here are directory previews. Confirm scope and availability before commissioning work.</p></section>

    return <section className="data-page discovery-page discovery-consultants">
        <div className="consultants-hero"><div><p className="eyebrow"><span></span> Human expertise</p><h1>Consultants</h1><p>Find the right guidance for your BIS-related requirements. Connect with registered consultants for expert assistance.</p></div><Link className="button" to="/consultations">My consultations <span>↗</span></Link></div>
        <div className="consultants-toolbar"><label className="consultants-search" htmlFor="consultant-search"><span aria-hidden="true">⌕</span><span className="sr-only">Search consultants</span><input id="consultant-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search consultants..." /></label><div className="consultant-filters" aria-label="Filter consultants">{filters.slice(0, 7).map((option) => <button className={filter === option ? 'is-selected' : ''} type="button" key={option} onClick={() => setFilter(option)}>{option}</button>)}</div></div>
        <div className="consultants-section-heading"><h2>Available consultants</h2><span>{filteredConsultants.length} {filteredConsultants.length === 1 ? 'profile' : 'profiles'}</span></div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        {loading ? <div className="consultant-grid">{[1, 2, 3, 4, 5, 6].map((item) => <div className="consultant-skeleton" key={item} aria-hidden="true"></div>)}</div> : filteredConsultants.length === 0 ? <article className="consultants-empty"><strong>{consultants.length === 0 ? 'No consultants available' : 'No consultants found'}</strong><p>{consultants.length === 0 ? 'There are currently no registered consultants available for consultation.' : 'Try a different search or filter.'}</p></article> : <div className="consultant-grid">{filteredConsultants.map((consultant) => <ConsultantCard key={consultant.id} consultant={consultant} onRequest={setSelectedConsultant} />)}</div>}
        <p className="page-disclaimer">Consultants shown here are active records from the StandIQ directory. Review each profile before sending a request.</p>
        {confirmation && <div className="consultant-confirmation" role="status"><strong>Consultation request sent</strong><span>Your request has been sent to {confirmation}. You can track its status from My Consultations.</span><div><Link className="button button-small" to="/consultations">View My Consultations <span>↗</span></Link><button className="text-button" type="button" onClick={() => setConfirmation('')}>Continue browsing</button></div></div>}
        {selectedConsultant && <ConsultationRequest consultant={selectedConsultant} onClose={() => setSelectedConsultant(null)} onSuccess={() => { setSelectedConsultant(null); setConfirmation(selectedConsultant.name) }} />}
    </section>
}

export default DiscoveryPage
