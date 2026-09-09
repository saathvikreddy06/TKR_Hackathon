import { Link } from 'react-router-dom'

function AboutPage() {
    return <section className="about-section page-section" id="about"><div><p className="eyebrow"><span></span> About standIQ</p><h2>Clarity is a form<br />of <em>progress.</em></h2></div><p>Indian standards help build safer products, stronger businesses, and a more trusted marketplace. standIQ makes that knowledge easier to find, understand, and act on.</p><Link className="button button-light" to="/services">Explore BIS services <span>↗</span></Link></section>
}

export default AboutPage
