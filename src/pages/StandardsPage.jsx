import { useState } from 'react'
import { Link } from 'react-router-dom'

const standards = [
    { number: 'IS 302 (Part 1)', title: 'Safety of household and similar electrical appliances', category: 'Electrical & Electronics', year: '2024', status: 'Current', scope: 'General requirements for household electrical appliances.' },
    { number: 'IS 456:2000', title: 'Plain and reinforced concrete — code of practice', category: 'Construction', year: '2023', status: 'Current', scope: 'Structural use of plain and reinforced concrete.' },
    { number: 'IS 17017:2018', title: 'Electric vehicle conductive charging system', category: 'Automotive', year: '2018', status: 'Current', scope: 'Connection and charging requirements for electric vehicles.' },
    { number: 'IS 15757:2007', title: 'Gold and gold alloys — fineness and marking', category: 'Jewellery & Hallmarking', year: '2022', status: 'Current', scope: 'Requirements for fineness grades and marking.' },
]

function StandardsPage() {
    const [query, setQuery] = useState('')
    const [category, setCategory] = useState('All categories')
    const results = standards.filter((standard) => {
        const matchesQuery = `${standard.number} ${standard.title} ${standard.category}`.toLowerCase().includes(query.toLowerCase())
        return matchesQuery && (category === 'All categories' || standard.category === category)
    })
    return <section className="data-page standards-page"><div className="page-intro-row"><div><p className="eyebrow"><span></span> Standards explorer</p><h1>Find the right <em>standard.</em></h1><p>Search the Indian Standards catalogue by IS number, product, category, or keyword.</p></div><Link className="button" to="/recommend">Recommend a standard <span>↗</span></Link></div><div className="search-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by IS number, product, or keyword" aria-label="Search Indian Standards" /><select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category"><option>All categories</option><option>Electrical & Electronics</option><option>Construction</option><option>Automotive</option><option>Jewellery & Hallmarking</option></select><button className="filter-button" type="button">More filters</button></div><div className="results-meta"><span>{results.length} standards found</span><span>Source registry · Frontend preview</span></div><div className="standards-list">{results.length ? results.map((standard) => <article className="standard-result" key={standard.number}><div className="standard-result-top"><span className="standard-number">{standard.number}</span><span className="confidence-badge confidence-high">Current</span></div><h2>{standard.title}</h2><p>{standard.scope}</p><div className="standard-meta"><span>{standard.category}</span><span>Edition {standard.year}</span><Link to="/assistant">Ask standIQ <span>↗</span></Link></div></article>) : <div className="empty-state"><strong>No reliable match found</strong><p>Try a broader product description or ask the assistant for help.</p><Link className="button" to="/assistant">Ask the assistant <span>↗</span></Link></div>}</div><p className="page-disclaimer">Search results are a frontend preview. Verify the current standard and source document before making compliance decisions.</p></section>
}

export default StandardsPage
