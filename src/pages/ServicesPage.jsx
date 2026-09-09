const services = [
    { number: '01', title: 'Standards explorer', description: 'Search Indian Standards by product, IS number, category, or keyword.', action: 'Explore standards', icon: '⌕' },
    { number: '02', title: 'Certification guide', description: 'Understand the path from testing and assessment to your BIS licence.', action: 'View certification', icon: '↗' },
    { number: '03', title: 'Laboratory finder', description: 'Find recognised laboratories by product, test, standard, or location.', action: 'Find a laboratory', icon: '⌁' },
    { number: '04', title: 'Hallmarking help', description: 'Get clear, consumer-first guidance on purity, HUID, and hallmarking.', action: 'Learn about hallmarking', icon: '✦' },
]

function ServicesPage() {
    return <section className="services-section page-section" id="services"><div className="section-heading"><div><p className="eyebrow"><span></span> Everything BIS, in one place</p><h2>Start with what<br /><em>you need.</em></h2></div><p className="section-intro">From your first question to your next big step, standIQ brings the right BIS service closer.</p></div><div className="service-grid">{services.map((service) => <article className="service-card" key={service.number}><div className="card-top"><span className="service-number">{service.number}</span><span className="service-icon">{service.icon}</span></div><h3>{service.title}</h3><p>{service.description}</p><a href="#services">{service.action} <span>↗</span></a></article>)}</div></section>
}

export default ServicesPage
