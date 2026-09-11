import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { auth } from './firebase'
import { getConsultant, updateConsultant } from './services/consultancyService'

function ConsultantProfilePage() {
    const { consultantId } = useParams()
    const [consultant, setConsultant] = useState(null)
    const [error, setError] = useState('')
    const [editing, setEditing] = useState(false)
    const [bio, setBio] = useState('')
    const [availability, setAvailability] = useState(true)

    useEffect(() => {
        getConsultant(consultantId)
            .then((data) => {
                setConsultant(data)
                setBio(data.bio || '')
                setAvailability(Boolean(data.availability))
            })
            .catch((requestError) => setError(requestError.message))
    }, [consultantId])

    const isOwner = auth.currentUser?.uid === consultant?.user_id || auth.currentUser?.uid === consultant?.id

    const saveProfile = async (event) => {
        event.preventDefault()
        try {
            const updated = await updateConsultant(consultantId, { bio, availability })
            setConsultant(updated)
            setEditing(false)
        } catch (requestError) {
            setError(requestError.message)
        }
    }

    if (error) return <section className="data-page"><p className="auth-error">{error}</p><Link className="back-link" to="/consultants">Back to consultants</Link></section>
    if (!consultant) return <section className="data-page"><p>Loading consultant profile...</p></section>

    const hasAvailability = typeof consultant.availability === 'boolean'

    return <section className="data-page consultant-profile-page">
        <Link className="back-link" to="/consultants">Back to consultants</Link>
        <div className="page-intro-row"><div><p className="eyebrow"><span></span> BIS consultant profile</p><h1>{consultant.consultancy_name || consultant.name}</h1><p>{consultant.bio || 'Review this consultant profile to understand their available BIS expertise.'}</p></div>{hasAvailability && <span className={`status-badge status-${consultant.availability ? 'current' : 'pending'}`}>{consultant.availability ? 'Available' : 'Currently unavailable'}</span>}</div>
        <div className="consultant-contact-strip"><div><small>Consultant</small><strong>{consultant.name}</strong></div><div><small>Consultancy area</small><strong>{consultant.consultancy_area || 'BIS standards'}</strong></div><div><small>Place</small><strong>{consultant.place || 'India'}</strong></div><div><small>Contact</small><strong>Phone shared after acceptance</strong></div></div>
        <div className="dashboard-grid"><article className="dashboard-card dashboard-card-wide"><div className="card-heading"><span>Areas of expertise</span></div><p>{(consultant.expertise || []).join(' · ') || 'BIS standards and certification'}</p><div className="card-heading"><span>Standards handled</span></div><p>{(consultant.standards_handled || []).join(' · ') || 'Discuss your product with the consultant.'}</p><div className="card-heading"><span>Product categories</span></div><p>{(consultant.categories || []).join(' · ') || 'General BIS compliance'}</p></article><article className="dashboard-card"><div className="card-heading"><span>Next step</span></div><Link className="button" to={`/consultations?consultant=${consultant.id}`}>Request consultation <span>↗</span></Link>{isOwner && <button className="card-link" type="button" onClick={() => setEditing((value) => !value)}>{editing ? 'Close editor' : 'Edit profile'}</button>}</article></div>
        {editing && <form className="dashboard-callout" onSubmit={saveProfile}><h2>Update your profile</h2><label>Bio<textarea value={bio} onChange={(event) => setBio(event.target.value)} rows="5" /></label><label>Availability<select value={availability ? 'available' : 'busy'} onChange={(event) => setAvailability(event.target.value === 'available')}><option value="available">Available</option><option value="busy">Busy</option></select></label><button className="button" type="submit">Save changes <span>↗</span></button></form>}
    </section>
}

export default ConsultantProfilePage
