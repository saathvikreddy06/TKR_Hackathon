import { useState } from 'react'
import { Link } from 'react-router-dom'

const capabilities = [
    { title: 'Find the right standard', text: 'Describe a product or ask a question in plain language, and get matched to relevant Indian Standards.' },
    { title: 'Understand certification', text: 'Learn which BIS scheme, licensing route, and documentation apply to your product.' },
    { title: 'See the evidence', text: 'Every answer is backed by real BIS data and sources, not guesswork.' },
    { title: 'Talk to a human when it matters', text: 'When a question needs expert judgment, connect with a qualified consultant.' },
]

const audiences = [
    { label: 'MSMEs & Startups', text: "Know what's required before you manufacture." },
    { label: 'Consultants', text: 'Extend your expertise with AI-assisted research.' },
    { label: 'Students & Researchers', text: 'Explore standards for projects and study.' },
    { label: 'Consumers', text: 'Understand what certification marks actually mean.' },
]

function AboutUsPage() {
    const [activeAudience, setActiveAudience] = useState(0)
    return <section className="about-us-page">
        <div className="about-us-hero"><div><h1>Making sense of Indian Standards, <em>together.</em></h1></div><p>standIQ is an AI-powered guide to Indian Standards, BIS certification, and compliance - built to help manufacturers, startups, MSMEs, students, and everyday consumers understand what applies to them, without wading through dense technical documents alone. We combine structured BIS data with AI reasoning to give clear, source-backed answers you can actually trust.</p></div>
        <div className="about-us-section about-problem"><div className="about-us-section-content"><h2>Why standIQ exists</h2><p>BIS publishes thousands of Indian Standards covering everything from stainless-steel water bottles to electronics and food packaging. For most people - a first-time manufacturer, a student researching a project, or a consumer checking a label - figuring out which standard applies, whether certification is required, or what testing is expected can be confusing and time-consuming. standIQ exists to turn that search into a simple conversation.</p></div></div>
        <div className="about-us-section about-help"><div className="about-us-section-content about-help-content"><h2>How we help</h2><div className="capability-grid">{capabilities.map((capability) => <article className="capability-card" key={capability.title}><strong>{capability.title}</strong><p>{capability.text}</p><small>Explore <span>↗</span></small></article>)}</div></div></div>
        <div className="about-us-section about-bis"><div className="about-us-section-content"><h2>About the Bureau of Indian Standards</h2><p>The Bureau of Indian Standards (BIS) is India's National Standards Body, established under the BIS Act, operating under the Ministry of Consumer Affairs, Food &amp; Public Distribution. BIS develops and publishes Indian Standards, runs product certification and hallmarking schemes, recognizes testing laboratories, and supports consumer protection through standardization and conformity assessment.</p><small className="fact-note">Verify current organizational details against official BIS sources before publishing or relying on them.</small></div></div>
        <div className="responsibility-panel"><div><h2>Built on evidence,<br /><em>not assumptions.</em></h2></div><div><p>standIQ retrieves information from a structured knowledge base before generating any answer - it does not invent standard numbers, certification requirements, or testing details. When evidence is insufficient, we say so clearly and point you toward further verification or a human consultant, rather than guessing.</p><strong>Decision support, not a substitute for official BIS confirmation.</strong></div></div>
        <div className="about-us-section about-audience"><div className="about-us-section-content audience-content"><h2>Built for everyone who works with standards</h2><div className="audience-tabs" role="tablist" aria-label="Who standIQ is for">{audiences.map((audience, index) => <button className={activeAudience === index ? 'active' : ''} type="button" role="tab" aria-selected={activeAudience === index} key={audience.label} onClick={() => setActiveAudience(index)}>{audience.label}</button>)}</div><div className="audience-detail" role="tabpanel"><p><strong>{audiences[activeAudience].label}</strong>{audiences[activeAudience].text}</p></div></div></div>
        <div className="about-us-cta"><div><h2>Have a standards question?</h2></div><Link className="button" to="/assistant">Ask standIQ <span>↗</span></Link></div>
        <p className="about-us-disclaimer">standIQ can make mistakes. Check important information against official BIS sources.</p>
    </section>
}

export default AboutUsPage
