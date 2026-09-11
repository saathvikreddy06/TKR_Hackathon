import { Link } from 'react-router-dom'

const services = [
    { number: '01', title: 'Standards explorer', description: 'Search Indian Standards by product, IS number, category, or keyword.', example: 'Search standards like IS 302 or IS 456.', action: 'Explore standards', icon: '⌕', route: '/standards' },
    { number: '02', title: 'Product analyzer', description: 'Describe what you make and see potentially applicable standards with clear verification gaps.', example: 'Try: stainless steel water bottles.', action: 'Analyze your product', icon: '↗', route: '/recommend' },
    { number: '03', title: 'Testing laboratories', description: 'Follow the path from a possible standard to relevant testing capability when verified data is available.', example: 'Browse labs offering electrical safety tests.', action: 'Find a laboratory', icon: '⌁', route: '/laboratories' },
    { number: '04', title: 'Consultant support', description: 'Connect with human expertise when the available evidence is not enough for your next decision.', example: 'Find help with certification planning.', action: 'Find a consultant', icon: '✦', route: '/consultants' },
]

function ServicesPage() {
    return <section className="services-section page-section" id="services">
        <div className="services-hero">
            <div className="section-heading"><div><p className="eyebrow"><span></span> Everything BIS, in one place</p><h2>Start with what<br /><em>you need.</em></h2></div><p className="section-intro">From your first question to your next big step, standIQ brings the right BIS service closer.</p></div>
            <div className="services-hero-art" role="img" aria-label="Connected standards, checklist, and certification badge"><div className="services-art-ring"><strong>✓</strong><span>VERIFIED</span></div><div className="services-art-node node-a">IS 302</div><div className="services-art-node node-b">TEST</div><div className="services-art-node node-c">QCO</div><i className="services-art-line line-a"></i><i className="services-art-line line-b"></i><i className="services-art-line line-c"></i></div>
        </div>
        <div className="service-grid">{services.map((service) => <article className="service-card" key={service.number}><div className="card-top"><span className="service-number">{service.number}</span><span className="service-icon">{service.icon}</span></div><h3>{service.title}</h3><p>{service.description}</p><small className="service-example"><span>{service.icon}</span>{service.example}</small><Link to={service.route}>{service.action} <span>↗</span></Link></article>)}</div>
        <div className="service-stats"><div><strong>12k+</strong><span>standards indexed</span></div><div><strong>48</strong><span>lab records in preview</span></div><div><strong>26</strong><span>consultant profiles in preview</span></div><small><span>◉</span> BIS-linked catalogue coverage</small></div>
    </section>
}

export default ServicesPage
