import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listConsultants } from './services/consultancyService'

const laboratories = [
    { name: 'Electrical Research & Development Association', location: 'Vadodara, Gujarat', type: 'BIS-recognized', tests: 'Electrical safety · LED · cables', status: 'Verified' },
    { name: 'Central Food Technological Research Institute', location: 'Mysuru, Karnataka', type: 'NABL accredited', tests: 'Food · water · microbiology', status: 'Verified' },
    { name: 'National Test House', location: 'Kolkata, West Bengal', type: 'BIS-recognized', tests: 'Construction · chemicals · materials', status: 'Verified' },
    { name: 'Textile Committee Testing Centre', location: 'Mumbai, Maharashtra', type: 'NABL accredited', tests: 'Textiles · garments · fibres', status: 'Pending verification' },
]

const content = {
    laboratories: { eyebrow: 'Testing network', title: 'Find a testing laboratory.', intro: 'Explore sample laboratory records by location, accreditation, and testing capability. Confirm scope and availability with the laboratory before commissioning work.', cta: 'Ask the assistant', route: '/assistant' },
    consultants: { eyebrow: 'Human expertise', title: 'Find a BIS consultant.', intro: 'Browse consultants currently available in the StandIQ directory and request help with your BIS decision.', cta: 'View my requests', route: '/consultations' },
}

function SourceTag() {
    return <small className="source-tag">◉ BIS official registry · preview</small>
}

function DiscoveryPage({ type }) {
    const page = content[type]
    const [expertise, setExpertise] = useState('All expertise')
    const [consultants, setConsultants] = useState([])
    const [loading, setLoading] = useState(type === 'consultants')
    const [error, setError] = useState('')

    useEffect(() => {
        if (type !== 'consultants') return undefined
        listConsultants()
            .then((data) => setConsultants(data.consultants || []))
            .catch((requestError) => setError(requestError.message))
            .finally(() => setLoading(false))
        return undefined
    }, [type])

    const expertiseOptions = [...new Set(consultants.flatMap((consultant) => consultant.expertise || []))]
    const filteredConsultants = consultants.filter((consultant) => expertise === 'All expertise' || consultant.expertise?.includes(expertise))

    return <section className={`data-page discovery-page discovery-${type}`}><div className="page-intro-row"><div><p className="eyebrow"><span></span> {page.eyebrow}</p><h1>{page.title}</h1><p>{page.intro}</p></div><Link className="button" to={page.route}>{page.cta} <span>↗</span></Link></div>
        {type === 'laboratories' && <div className="lab-list">{laboratories.map((lab) => <article className="lab-card" key={lab.name}><div className="lab-map-pin" aria-hidden="true">⌖</div><div className="lab-card-body"><div className="card-heading"><div><h2>{lab.name}</h2><span>{lab.location}</span></div><span className={`status-badge status-${lab.status === 'Verified' ? 'current' : 'pending'}`}>{lab.status}</span></div><div className="lab-details"><span>{lab.type}</span><span>{lab.tests}</span></div><SourceTag /></div></article>)}</div>}
        {type === 'consultants' && <>{error && <p className="auth-error" role="alert">{error}</p>}{loading ? <p>Loading consultant profiles...</p> : <><div className="directory-filter"><span>Filter by expertise</span><select value={expertise} onChange={(event) => setExpertise(event.target.value)} aria-label="Filter consultants by expertise"><option>All expertise</option>{expertiseOptions.map((option) => <option key={option}>{option}</option>)}</select><small>{filteredConsultants.length} of {consultants.length} profiles shown</small></div>{filteredConsultants.length === 0 ? <article className="dashboard-callout"><h2>{consultants.length === 0 ? 'No consultant profiles yet.' : 'No matching consultants.'}</h2><p>{consultants.length === 0 ? 'Consultant profiles will appear here as soon as they are added to the directory.' : 'Try selecting All expertise to see every consultant.'}</p></article> : <div className="consultant-grid">{filteredConsultants.map((consultant) => <article className="consultant-card" key={consultant.id}><div className="consultant-avatar">{consultant.name?.split(' ').map((part) => part[0]).join('').slice(0, 2)}</div><div className="consultant-card-head"><div><h2>{consultant.name}</h2><span>{consultant.email || 'BIS consultant'}</span></div><span className={`status-badge status-${consultant.availability ? 'current' : 'pending'}`}>{consultant.availability ? 'Available' : 'Busy'}</span></div><strong className="consultant-expertise">{(consultant.expertise || []).join(' · ') || 'BIS standards'}</strong><p>Standards handled: {(consultant.standards_handled || []).join(' · ') || 'Profile details on request'}</p><Link className="card-link" to={`/consultants/${consultant.id}`}>View profile ↗</Link><Link className="button button-small" to={`/consultations?consultant=${consultant.id}`}>Request consultation <span>↗</span></Link></article>)}</div>}</>}</>}
        <p className="page-disclaimer">Consultants shown here are active records from the StandIQ directory. Review each profile before sending a request.</p>
    </section>
}

export default DiscoveryPage
