import { useState } from 'react'
import { Link } from 'react-router-dom'

const standards = [
    { number: 'IS 14543:2024', title: 'Packaged drinking water — specification', category: 'Food & Beverages', year: '2024', status: 'Current', scope: 'Requirements and methods of sampling and test for packaged drinking water.', badge: 'Recently updated', icon: '◒' },
    { number: 'IS 13428:2024', title: 'Packaged natural mineral water — specification', category: 'Food & Beverages', year: '2024', status: 'Current', scope: 'Requirements for natural mineral water obtained from natural sources.', icon: '◒' },
    { number: 'IS 302 (Part 1):2024', title: 'Safety of household and similar electrical appliances', category: 'Electrical', year: '2024', status: 'Current', scope: 'General requirements for household electrical appliances.', badge: 'Trending', icon: 'ϟ' },
    { number: 'IS 16046 (Part 1):2018', title: 'Secondary cells and batteries for portable applications', category: 'Electrical', year: '2018', status: 'Current', scope: 'Safety requirements for portable sealed secondary cells and batteries.', icon: 'ϟ' },
    { number: 'IS 456:2000', title: 'Plain and reinforced concrete — code of practice', category: 'Construction', year: '2000', status: 'Current', scope: 'Structural use of plain and reinforced concrete.', icon: '⌂' },
    { number: 'IS 2062:2011', title: 'Structural steel — hot rolled medium and high tensile', category: 'Construction', year: '2011', status: 'Current', scope: 'Requirements for structural steel products used in construction.', icon: '⌂' },
    { number: 'IS 17017:2018', title: 'Electric vehicle conductive charging system', category: 'Automotive', year: '2018', status: 'Current', scope: 'Connection and charging requirements for electric vehicles.', badge: 'Trending', icon: '◇' },
    { number: 'IS 15757:2007', title: 'Gold and gold alloys — fineness and marking', category: 'Jewellery & Hallmarking', year: '2007', status: 'Current', scope: 'Requirements for fineness grades and marking.', icon: '✦' },
    { number: 'IS 1786:2008', title: 'High strength deformed steel bars and wires for concrete', category: 'Construction', year: '2008', status: 'Current', scope: 'Requirements for reinforcement bars and wires used in reinforced concrete.', icon: '⌂' },
    { number: 'IS 9873 (Part 1):2012', title: 'Safety of toys — mechanical and physical properties', category: 'Consumer Products', year: '2012', status: 'Amended', scope: 'Mechanical and physical safety requirements for toys.', badge: 'Amended', icon: '▣' },
    { number: 'IS 10322 (Part 5):2012', title: 'Luminaires — particular requirements', category: 'Electrical', year: '2012', status: 'Current', scope: 'Particular safety requirements for luminaires and lighting equipment.', icon: 'ϟ' },
    { number: 'IS 14861:2000', title: 'Safety of household and similar electrical appliances', category: 'Electrical', year: '2000', status: 'Withdrawn', scope: 'Legacy safety requirements retained for catalogue reference.', icon: 'ϟ' },
]

const categoryOptions = ['Electrical', 'Food & Beverages', 'Construction', 'Automotive', 'Jewellery & Hallmarking', 'Consumer Products']
const yearOptions = ['2024', '2018', '2012', '2011', '2008', '2007', '2000']
const statusOptions = ['Current', 'Withdrawn', 'Amended']

function StandardsPage() {
    const [query, setQuery] = useState('')
    const [category, setCategory] = useState('All categories')
    const [filtersOpen, setFiltersOpen] = useState(false)
    const [selectedCategories, setSelectedCategories] = useState([])
    const [selectedYears, setSelectedYears] = useState([])
    const [selectedStatuses, setSelectedStatuses] = useState([])
    const results = standards.filter((standard) => {
        const matchesQuery = `${standard.number} ${standard.title} ${standard.category}`.toLowerCase().includes(query.toLowerCase())
        return matchesQuery && (category === 'All categories' || standard.category === category) && (!selectedCategories.length || selectedCategories.includes(standard.category)) && (!selectedYears.length || selectedYears.includes(standard.year)) && (!selectedStatuses.length || selectedStatuses.includes(standard.status))
    })
    const toggleFilter = (setter, value) => setter((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value])
    return <section className="data-page standards-page"><div className="page-intro-row"><div><p className="eyebrow"><span></span> Standards explorer</p><h1>Find the right <em>standard.</em></h1><p>Search the Indian Standards catalogue by IS number, product, category, or keyword.</p></div><Link className="button" to="/recommend">Recommend a standard <span>↗</span></Link></div><div className="search-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by IS number, product, or keyword" aria-label="Search Indian Standards" /><select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category"><option>All categories</option>{categoryOptions.map((option) => <option key={option}>{option}</option>)}</select><button className="filter-button" type="button" onClick={() => setFiltersOpen((open) => !open)} aria-expanded={filtersOpen}>More filters {filtersOpen ? '−' : '+'}</button></div>{filtersOpen && <div className="standards-filters"><fieldset><legend>Category</legend>{categoryOptions.map((option) => <label key={option}><input type="checkbox" checked={selectedCategories.includes(option)} onChange={() => toggleFilter(setSelectedCategories, option)} />{option}</label>)}</fieldset><fieldset><legend>Year</legend>{yearOptions.map((option) => <label key={option}><input type="checkbox" checked={selectedYears.includes(option)} onChange={() => toggleFilter(setSelectedYears, option)} />{option}</label>)}</fieldset><fieldset><legend>Status</legend>{statusOptions.map((option) => <label key={option}><input type="checkbox" checked={selectedStatuses.includes(option)} onChange={() => toggleFilter(setSelectedStatuses, option)} />{option}</label>)}</fieldset></div>}<div className="results-meta"><span>{results.length} standards found</span><span><span className="source-tag">◉ BIS official registry</span></span></div><div className="standards-list">{results.length ? results.map((standard) => <article className="standard-result" key={standard.number}><div className="standard-result-top"><span className="standard-category-icon" aria-hidden="true">{standard.icon}</span><span className="standard-number">{standard.number}</span><span className={`status-badge status-${standard.status.toLowerCase()}`}>{standard.status}</span>{standard.badge && <span className="trend-badge">{standard.badge}</span>}</div><h2>{standard.title}</h2><p>{standard.scope}</p><div className="standard-meta"><span>{standard.category}</span><span>Edition {standard.year}</span><Link to="/assistant">Ask standIQ <span>↗</span></Link></div></article>) : <div className="empty-state"><strong>No reliable match found</strong><p>Try a broader product description or ask the assistant for help.</p><Link className="button" to="/assistant">Ask the assistant <span>↗</span></Link></div>}</div><p className="page-disclaimer">Catalogue preview based on BIS-linked records. Verify the current standard and source document before making compliance decisions.</p></section>
}

export default StandardsPage
