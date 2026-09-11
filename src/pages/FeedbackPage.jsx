import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { submitFeedback } from './services/feedbackService'

function FeedbackPage() {
    const { consultationId } = useParams()
    const navigate = useNavigate()
    const [rating, setRating] = useState(0)
    const [comment, setComment] = useState('')
    const [error, setError] = useState('')
    const [submitted, setSubmitted] = useState(false)

    const submit = async (event) => {
        event.preventDefault()
        if (!rating) {
            setError('Please choose a star rating.')
            return
        }
        try { await submitFeedback({ consultation_id: consultationId, rating, comment }); setSubmitted(true) } catch (requestError) { setError(requestError.message) }
    }

    return <section className="data-page feedback-page"><Link className="back-link" to={`/consultations/${consultationId}`}>Back to consultation</Link><div className="page-intro-row"><div><p className="eyebrow"><span></span> Close the loop</p><h1>How did the consultation help?</h1><p>Your feedback helps keep the expert network useful and accountable.</p></div></div>{error && <p className="auth-error">{error}</p>}{submitted ? <article className="dashboard-callout"><h2>Thank you for the feedback.</h2><button className="button" type="button" onClick={() => navigate('/consultations')}>Return to workspace <span>↗</span></button></article> : <form className="dashboard-card feedback-form" onSubmit={submit}><fieldset><legend>Rating</legend><div className="star-rating" role="radiogroup" aria-label="Consultation rating">{[1, 2, 3, 4, 5].map((value) => <button className={value <= rating ? 'star is-selected' : 'star'} type="button" role="radio" aria-checked={rating === value} aria-label={`${value} star${value > 1 ? 's' : ''}`} onClick={() => setRating(value)}>★</button>)}</div><span className="rating-hint">{rating ? `${rating} out of 5 stars` : 'Choose a rating'}</span></fieldset><label className="feedback-comment-label">Comment<textarea value={comment} onChange={(event) => setComment(event.target.value)} rows="12" placeholder="Tell the consultant what was useful, what could be clearer, and what you will do next." /></label><button className="button" type="submit">Submit feedback <span>↗</span></button></form>}</section>
}

export default FeedbackPage
