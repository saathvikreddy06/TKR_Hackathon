import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { submitFeedback } from './services/feedbackService'

function FeedbackPage() {
    const { consultationId } = useParams()
    const navigate = useNavigate()
    const [rating, setRating] = useState(5)
    const [comment, setComment] = useState('')
    const [error, setError] = useState('')
    const [submitted, setSubmitted] = useState(false)

    const submit = async (event) => {
        event.preventDefault()
        try { await submitFeedback({ consultation_id: consultationId, rating: Number(rating), comment }); setSubmitted(true) } catch (requestError) { setError(requestError.message) }
    }

    return <section className="data-page feedback-page"><Link className="back-link" to={`/consultations/${consultationId}`}>Back to consultation</Link><div className="page-intro-row"><div><p className="eyebrow"><span></span> Close the loop</p><h1>How did the consultation help?</h1><p>Your feedback helps keep the expert network useful and accountable.</p></div></div>{error && <p className="auth-error">{error}</p>}{submitted ? <article className="dashboard-callout"><h2>Thank you for the feedback.</h2><button className="button" type="button" onClick={() => navigate('/consultations')}>Return to workspace <span>↗</span></button></article> : <form className="dashboard-card" onSubmit={submit}><label>Rating<select value={rating} onChange={(event) => setRating(event.target.value)}>{[1, 2, 3, 4, 5].map((value) => <option key={value}>{value}</option>)}</select></label><label>Comment<textarea value={comment} onChange={(event) => setComment(event.target.value)} rows="6" placeholder="What was useful?" /></label><button className="button" type="submit">Submit feedback <span>↗</span></button></form>}</section>
}

export default FeedbackPage
