import { Link } from 'react-router-dom'

const principles = [
    ['01', 'Indian Standards', 'Develops and publishes standards covering a wide range of products, processes, and services.'],
    ['02', 'Product Certification', 'Provides conformity assessment and certification mechanisms that help manufacturers demonstrate compliance with applicable standards.'],
    ['03', 'Testing & Laboratories', 'Works with recognized and empanelled laboratories that provide testing facilities for evaluating products against relevant standards.'],
    ['04', 'Consumer Protection', 'Promotes quality, safety, and awareness while supporting consumers through standardization and certification-related resources.'],
]

const bisProcess = [
    ['01', 'Standards', 'Define common technical requirements.'],
    ['02', 'Testing', 'Evaluate products against relevant requirements.'],
    ['03', 'Conformity Assessment', 'Check whether requirements are met.'],
    ['04', 'Certification', 'Demonstrate conformity through an applicable route.'],
    ['05', 'Market Surveillance', 'Support ongoing attention to market compliance.'],
    ['06', 'Consumer Protection', 'Help people make informed choices.'],
]

const matters = [
    ['Safety', 'Helps establish requirements designed to reduce risks associated with products and services.'],
    ['Quality', 'Provides measurable technical and performance requirements.'],
    ['Consistency', 'Creates common benchmarks for products, materials, processes, and services.'],
    ['Consumer Confidence', 'Helps consumers make informed decisions using standardization and certification information.'],
    ['Industry Readiness', 'Helps businesses understand technical and conformity requirements during product development.'],
]

const certificationSteps = ['Identify Product', 'Identify Applicable Standard', 'Check Certification Requirement', 'Understand Testing Requirements', 'Testing & Assessment', 'Certification / Registration', 'Market Compliance']

const schemes = [
    ['Scheme I', 'Product certification scheme used for demonstrating conformity of products with applicable Indian Standards.'],
    ['Scheme II', 'Compulsory Registration Scheme (CRS)', 'A registration-based conformity system applicable to specified products, particularly several electronic and IT products.'],
    ['Scheme IV', 'A conformity assessment route that includes provisions for certification of products manufactured outside India under applicable requirements.'],
]

const industryChecklist = ['Identify applicable Indian Standards', 'Determine whether certification or registration is required', 'Understand the applicable conformity assessment scheme', 'Identify required testing', 'Understand documentation requirements', 'Find relevant testing laboratories', 'Plan compliance during product development']
const consumerChecklist = ['Understand Indian Standards', 'Verify certification information', 'Learn about certified products', 'Access BIS-related resources', 'Raise concerns through applicable channels']

function Checklist({ items }) {
    return <ul className="bis-checklist">{items.map((item) => <li key={item}><span aria-hidden="true">✓</span>{item}</li>)}</ul>
}

function AboutPage() {
    return <section className="bis-page" id="about">
        <div className="bis-hero">
            <div className="bis-hero-copy"><p className="eyebrow"><span></span> About the standards body</p><h1>Understanding BIS &amp; Indian <em>Standards.</em></h1><p className="bis-lede">The Bureau of Indian Standards (BIS) is India's national standards body, helping promote quality, safety, reliability, and consistency across products, services, and processes.</p><Link className="button" to="/assistant">Explore BIS Assistant <span>↗</span></Link></div>
            <div className="bis-hero-art" aria-label="Abstract illustration of connected standards and certification" role="img"><div className="bis-seal">BIS<span>INDIA'S<br />STANDARDS</span></div><div className="bis-art-line line-one"></div><div className="bis-art-line line-two"></div><div className="bis-art-node node-one">IS</div><div className="bis-art-node node-two">✓</div><div className="bis-art-node node-three">QA</div><span className="bis-art-label label-one">QUALITY</span><span className="bis-art-label label-two">TRUST</span></div>
        </div>

        <div className="bis-section bis-overview"><div className="bis-section-intro"><p className="eyebrow"><span></span> The foundation</p><h2>What is <em>BIS?</em></h2><p>The Bureau of Indian Standards (BIS) is India's national standards body. BIS develops and publishes Indian Standards and operates conformity assessment and certification systems that help ensure products meet applicable quality, safety, and technical requirements.</p></div><div className="bis-principle-grid">{principles.map(([number, title, text]) => <article className="bis-card" key={title}><span className="bis-card-number">{number}</span><h3>{title}</h3><p>{text}</p><span className="bis-card-mark">↗</span></article>)}</div></div>

        <div className="bis-band"><div className="bis-section bis-process"><div className="bis-section-intro"><p className="eyebrow"><span></span> From rule to reassurance</p><h2>What does <em>BIS do?</em></h2></div><div className="bis-process-track">{bisProcess.map(([number, title, text]) => <article key={title}><span className="bis-process-icon">{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div></div></div>

        <div className="bis-section"><div className="bis-section-heading"><div><p className="eyebrow"><span></span> The value of a common language</p><h2>Why Indian Standards <em>matter.</em></h2></div><p>Standards turn expectations into requirements that people and organizations can understand, test, and use.</p></div><div className="bis-matter-grid">{matters.map(([title, text], index) => <article className="bis-matter-card" key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{text}</p></article>)}</div></div>

        <div className="bis-section bis-certification"><div className="bis-section-heading"><div><p className="eyebrow"><span></span> A practical path</p><h2>How BIS certification <em>works.</em></h2></div><p>The exact process, requirements, and applicable scheme depend on the product, relevant Indian Standard, and prevailing regulatory requirements.</p></div><div className="bis-cert-track">{certificationSteps.map((step, index) => <div className="bis-cert-step" key={step}><span>{String(index + 1).padStart(2, '0')}</span><strong>{step}</strong></div>)}</div></div>

        <div className="bis-band bis-soft-band"><div className="bis-section"><div className="bis-section-heading"><div><p className="eyebrow"><span></span> Routes to conformity</p><h2>BIS certification <em>schemes.</em></h2></div><p>Applicable routes depend on the product and relevant regulatory framework.</p></div><div className="bis-scheme-grid">{schemes.map((scheme) => <article className="bis-scheme-card" key={scheme[0]}><span className="bis-card-number">{scheme[0]}</span><h3>{scheme[0]}</h3>{scheme.length === 3 && <p className="bis-scheme-subtitle">{scheme[1]}</p>}<p>{scheme.length === 2 ? scheme[1] : scheme[2]}</p></article>)}</div><p className="bis-disclaimer">The applicable scheme depends on the product and relevant regulatory framework. Check current official requirements before acting.</p></div></div>

        <div className="bis-section bis-labs"><div className="bis-section-intro"><p className="eyebrow"><span></span> Evidence in the process</p><h2>Testing &amp; Laboratory <em>Network.</em></h2><p>Testing is an important part of demonstrating product conformity. BIS maintains information about recognized and empanelled laboratories, including their testing capabilities and areas of scope.</p></div><div className="bis-lab-panel"><div className="bis-lab-panel-head"><span>LABORATORY DIRECTORY</span><span>VERIFY CURRENT DETAILS</span></div><div className="bis-lab-fields">{['Laboratory Name', 'Location', 'Applicable Indian Standards', 'Testing Scope', 'Test Parameters / Clauses', 'Contact Information'].map((field) => <div key={field}><span>{field}</span><b>Available through verified records</b></div>)}</div><Link className="text-button" to="/laboratories">Explore Laboratories <span>↗</span></Link></div></div>

        <div className="bis-band bis-standards-band"><div className="bis-section bis-standards"><div className="bis-section-heading"><div><p className="eyebrow"><span></span> The reference layer</p><h2>Explore Indian <em>Standards.</em></h2></div><p>Indian Standards provide common technical benchmarks for products, materials, processes, and services. They may define specifications, safety requirements, performance characteristics, testing methods, marking requirements, and other technical requirements.</p></div></div></div>

        <div className="bis-section bis-audiences"><div className="bis-audience-grid"><div><p className="eyebrow"><span></span> For the people building</p><h2>For Manufacturers &amp; <em>Businesses.</em></h2><p>For manufacturers, startups, MSMEs, and businesses, understanding BIS requirements can be an important part of bringing a product to market.</p><Checklist items={industryChecklist} /><Link className="button button-light" to="/recommend">Analyze My Product <span>↗</span></Link></div><div className="bis-consumer-block"><p className="eyebrow"><span></span> For the people choosing</p><h2>For <em>Consumers.</em></h2><p>BIS provides resources that help consumers understand standardized and certified products and access relevant certification and consumer-related information.</p><Checklist items={consumerChecklist} /></div></div></div>

        <div className="bis-band bis-story-band"><div className="bis-section bis-story"><div className="bis-section-heading"><div><p className="eyebrow"><span></span> Why we built this</p><h2>Making BIS information <em>easier to access.</em></h2></div><p>BIS information is extensive and can be distributed across standards, certification resources, testing information, laboratory databases, and other official resources.</p></div><p className="bis-story-copy">Our platform brings this information together into an AI-powered, conversational experience. Instead of searching through multiple documents and resources manually, users can describe their product or question in natural language and receive relevant, source-backed information. From identifying applicable standards to understanding certification, testing, and laboratory requirements, our goal is to make BIS-related information easier to discover, understand, and use.</p><div className="bis-comparison"><div><span>TRADITIONAL SEARCH</span><strong>Multiple resources</strong><strong>Manual searching</strong><strong>Scattered information</strong><strong>Generic search</strong></div><div className="bis-comparison-arrow">→</div><div className="bis-comparison-active"><span>INTELLIGENT ASSISTANT</span><strong>Unified experience</strong><strong>Natural-language queries</strong><strong>Connected knowledge</strong><strong>Context-aware guidance</strong></div></div></div></div>

        <div className="bis-final-cta"><p className="eyebrow"><span></span> Start with a question</p><h2>Have a BIS <em>question?</em></h2><p>Ask our AI assistant about Indian Standards, certification, testing requirements, laboratories, and BIS services.</p><Link className="button" to="/assistant">Ask BIS Assistant <span>↗</span></Link></div>
        <p className="about-us-disclaimer">Information is general guidance. Check important details against current official BIS sources.</p>
    </section>
}

export default AboutPage
