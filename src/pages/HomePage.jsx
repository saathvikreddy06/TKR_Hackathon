import { Link, useNavigate } from 'react-router-dom'

function HomePage() {
    const navigate = useNavigate()
    return (
        <>
            <section className="hero-section" id="home">
                <div className="hero-copy"><p className="eyebrow"><span></span> Your guide to Indian standards</p><h1>Make sense of<br /><em>every standard.</em></h1><p className="hero-description">Understand Indian Standards, certification requirements, testing procedures, and BIS services with evidence-backed assistance.</p><div className="hero-actions"><Link className="button" to="/services">Explore BIS services <span>↗</span></Link><button className="text-button" onClick={() => navigate('/assistant')}>Ask the assistant <span>→</span></button></div><div className="hero-proof"><div className="proof-avatars"><span>R</span><span>M</span><span>A</span><span>+</span></div><p><strong>Built for clarity.</strong><br />For consumers, makers, and teams.</p></div></div>
            </section>
            <section className="home-search"><p className="eyebrow"><span></span> Start with a question</p><h2>What are you looking for?</h2><button type="button" onClick={() => navigate('/assistant')}>Ask about a product, standard, certification, testing requirement... <span>↗</span></button><div className="question-chips"><button type="button" onClick={() => navigate('/assistant')}>What standard applies to stainless-steel water bottles?</button><button type="button" onClick={() => navigate('/assistant')}>Do I need BIS certification for my product?</button><button type="button" onClick={() => navigate('/laboratories')}>Which laboratories may be relevant?</button></div></section>
            <section className="home-features"><article><span>01</span><h2>Find a Standard</h2><p>Search by standard number, product, industry, category, or keyword.</p><Link to="/standards">Explore standards ↗</Link></article><article><span>02</span><h2>Analyze Your Product</h2><p>Discover potentially applicable standards, testing requirements, and BIS schemes.</p><Link to="/recommend">Analyze a product ↗</Link></article><article><span>03</span><h2>Certification Guide</h2><p>Understand schemes, licensing procedures, requirements, documentation, and testing.</p><Link to="/assistant">Ask about certification ↗</Link></article><article><span>04</span><h2>Find a Consultant</h2><p>Connect with relevant human expertise when additional review is required.</p><Link to="/consultants">Find a consultant ↗</Link></article></section>
            <section className="trust-strip"><span>Powered by a better understanding of</span><strong>INDIAN STANDARDS</strong><i></i><strong>CERTIFICATION</strong><i></i><strong>COMPLIANCE</strong></section>
        </>
    )
}

export default HomePage
