import { Link, useNavigate } from 'react-router-dom'

function HomePage() {
    const navigate = useNavigate()
    return (
        <>
            <section className="hero-section" id="home">
                <div className="hero-copy"><p className="eyebrow"><span></span> Your guide to Indian standards</p><h1>Make sense of<br /><em>every standard.</em></h1><p className="hero-description">A simpler way to understand BIS standards, certifications, and services. Find reliable answers and move forward with confidence.</p><div className="hero-actions"><Link className="button" to="/services">Explore BIS services <span>↗</span></Link><button className="text-button" onClick={() => navigate('/assistant')}>Ask the assistant <span>→</span></button></div><div className="hero-proof"><div className="proof-avatars"><span>R</span><span>M</span><span>A</span><span>+</span></div><p><strong>Built for clarity.</strong><br />For consumers, makers, and teams.</p></div></div>
            </section>
            <section className="trust-strip"><span>Powered by a better understanding of</span><strong>INDIAN STANDARDS</strong><i></i><strong>CERTIFICATION</strong><i></i><strong>COMPLIANCE</strong></section>
        </>
    )
}

export default HomePage
