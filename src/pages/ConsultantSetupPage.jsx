import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createConsultant } from './services/consultancyService'

function ConsultantSetupPage({ onComplete }) {
    const navigate = useNavigate()
    const [form, setForm] = useState({
        name: '',
        email: '',
        phone: '',
        consultancy_name: '',
        consultancy_area: '',
        place: '',
        bio: '',
        expertise: '',
        standards_handled: '',
        categories: ''
    })
    const [error, setError] = useState('')
    const [saving, setSaving] = useState(false)

    const updateField = (event) => {
        const { name, value } = event.target
        setForm((current) => ({ ...current, [name]: value }))
    }

    const submit = async (event) => {
        event.preventDefault()
        setError('')
        setSaving(true)
        try {
            await createConsultant({
                ...form,
                expertise: form.expertise.split(',').map((item) => item.trim()).filter(Boolean),
                standards_handled: form.standards_handled.split(',').map((item) => item.trim()).filter(Boolean),
                categories: form.categories.split(',').map((item) => item.trim()).filter(Boolean)
            })
            onComplete?.()
            navigate('/consultant-dashboard', { replace: true })
        } catch (requestError) {
            setError(requestError.message || 'Unable to save consultant profile.')
        } finally {
            setSaving(false)
        }
    }

    return <section className="data-page consultant-setup-page">
        <div className="consultant-setup-intro"><p className="eyebrow"><span></span> Consultant onboarding</p><h1>Tell people what your consultancy does.</h1><p>Complete your BIS consultancy profile once. It will appear in the consultant directory and power your consultant dashboard.</p></div>
        <form className="consultant-setup-form" onSubmit={submit}>
            <div className="setup-form-section"><div><span className="setup-step">01</span><h2>Contact details</h2><p>Give users a reliable way to recognize your practice.</p></div><div className="setup-form-fields"><label>Consultant name<input name="name" value={form.name} onChange={updateField} placeholder="Your full name" required /></label><label>Email address<input name="email" type="email" value={form.email} onChange={updateField} placeholder="you@consultancy.com" required /></label><label>Phone number<input name="phone" value={form.phone} onChange={updateField} placeholder="Contact number" /></label></div></div>
            <div className="setup-form-section"><div><span className="setup-step">02</span><h2>Consultancy identity</h2><p>Help users find the right BIS specialist for their need.</p></div><div className="setup-form-fields"><label>Consultancy name<input name="consultancy_name" value={form.consultancy_name} onChange={updateField} placeholder="Your consultancy or firm name" required /></label><label>Consultancy area<input name="consultancy_area" value={form.consultancy_area} onChange={updateField} placeholder="Certification, electrical safety, food standards..." required /></label><label>Place<input name="place" value={form.place} onChange={updateField} placeholder="City, state" required /></label></div></div>
            <div className="setup-form-section"><div><span className="setup-step">03</span><h2>What you handle</h2><p>Use comma-separated terms so users can discover your profile.</p></div><div className="setup-form-fields"><label>Expertise<input name="expertise" value={form.expertise} onChange={updateField} placeholder="BIS certification, QCO, hallmarking" /></label><label>Standards handled<input name="standards_handled" value={form.standards_handled} onChange={updateField} placeholder="IS 302, IS 456, IS 16046" /></label><label>Product categories<input name="categories" value={form.categories} onChange={updateField} placeholder="Electrical, construction, food" /></label><label>Short bio<textarea name="bio" value={form.bio} onChange={updateField} rows="4" placeholder="Describe your BIS consulting experience." /></label></div></div>
            {error && <p className="auth-error" role="alert">{error}</p>}
            <div className="setup-form-actions"><span>Your profile can be updated later from your dashboard.</span><button className="button" type="submit" disabled={saving}>{saving ? 'Saving profile...' : 'Complete profile'} <span>↗</span></button></div>
        </form>
    </section>
}

export default ConsultantSetupPage
