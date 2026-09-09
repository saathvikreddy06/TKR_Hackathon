const services = [
    { number: '01', title: 'Standards explorer', description: 'Search Indian Standards by product, IS number, category, or keyword.', action: 'Explore standards', icon: '⌕', route: '/standards' },
    { number: '02', title: 'Product analyzer', description: 'Describe what you make and see potentially applicable standards with clear verification gaps.', action: 'Analyze your product', icon: '↗', route: '/recommend' },
    { number: '03', title: 'Testing laboratories', description: 'Follow the path from a possible standard to relevant testing capability when verified data is available.', action: 'Find a laboratory', icon: '⌁', route: '/laboratories' },
    { number: '04', title: 'Consultant support', description: 'Connect with human expertise when the available evidence is not enough for your next decision.', action: 'Find a consultant', icon: '✦', route: '/consultants' },
]

function ServicesPage() {
    return <section className="services-section page-section" id="services"><div className="section-heading"><div><p className="eyebrow"><span></span> Everything BIS, in one place</p><h2>Start with what<br /><em>you need.</em></h2></div><p className="section-intro">From your first question to your next big step, standIQ brings the right BIS service closer.</p></div><div className="service-grid">{services.map((service) => <article className="service-card" key={service.number}><div className="card-top"><span className="service-number">{service.number}</span><span className="service-icon">{service.icon}</span></div><h3>{service.title}</h3><p>{service.description}</p><a href={service.route}>{service.action} <span>↗</span></a></article>)}</div></section>
}

export default ServicesPage
