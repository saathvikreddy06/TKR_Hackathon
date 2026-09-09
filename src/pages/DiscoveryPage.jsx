import { Link } from 'react-router-dom'

const pageContent = {
    laboratories: {
        eyebrow: 'Testing network', title: 'Find a testing laboratory.', intro: 'Discover laboratories relevant to your product and testing requirements. Current laboratory availability and capabilities require verification against official sources.', cards: ['Product and test capability', 'Relevant standard or parameter', 'Location and verification status'], cta: 'Ask the assistant', route: '/assistant', note: 'No verified laboratory records are connected yet. Use this space for backend results when the laboratory registry is available.',
    },
    related: {
        eyebrow: 'Standards relationships', title: 'See how standards connect.', intro: 'Trace relationships such as related to, supersedes, amended by, or associated with a scheme when those relationships are present in the knowledge base.', cards: ['Related standard', 'Supersedes or amended by', 'Associated scheme'], cta: 'Explore standards', route: '/standards', note: 'Relationship data will appear here when confirmed by the BIS knowledge base. No relationships are inferred in the frontend.',
    },
    consultants: {
        eyebrow: 'Human expertise', title: 'Find a BIS consultant.', intro: 'When AI evidence is incomplete, connect with someone who can help you understand what to verify next.', cards: ['Expertise and categories', 'Standards handled', 'Availability and request status'], cta: 'Ask standIQ first', route: '/assistant', note: 'Consultant profiles and availability will be populated from the consultation service. No consultant details are invented here.',
    },
}

function DiscoveryPage({ type }) {
    const content = pageContent[type]
    return <section className="data-page discovery-page"><div className="page-intro-row"><div><p className="eyebrow"><span></span> {content.eyebrow}</p><h1>{content.title}</h1><p>{content.intro}</p></div><Link className="button" to={content.route}>{content.cta} <span>↗</span></Link></div><div className="discovery-grid">{content.cards.map((card, index) => <article className="discovery-card" key={card}><span>0{index + 1}</span><h2>{card}</h2><p>Available when supported by verified BIS data and source records.</p></article>)}</div><div className="empty-state discovery-empty"><strong>{content.note}</strong><p>This frontend is ready for API-backed records, loading states, source links, and verification metadata.</p><Link className="button button-light" to={content.route}>Continue exploring <span>↗</span></Link></div></section>
}

export default DiscoveryPage
