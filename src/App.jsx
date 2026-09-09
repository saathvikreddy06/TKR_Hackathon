import { useState } from 'react'
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import AssistantPage from './pages/AssistantPage'
import AboutPage from './pages/AboutPage'
import HomePage from './pages/HomePage'
import HowItWorksPage from './pages/HowItWorksPage'
import ServicesPage from './pages/ServicesPage'
import StandardsPage from './pages/StandardsPage'
import RecommendationPage from './pages/RecommendationPage'
import AuthPage from './pages/AuthPage'
import DashboardPage from './pages/DashboardPage'
import DiscoveryPage from './pages/DiscoveryPage'
import './App.css'

function SiteHeader({ onOpenAuth, role, language, onLanguageChange }) {
    return <header className="site-header"><NavLink className="brand" to="/" aria-label="standIQ home"><img src="/logo.jpeg" alt="standIQ logo" /><span>stand<span>IQ</span></span></NavLink><nav className="main-nav" aria-label="Main navigation"><NavLink to="/" end>Home</NavLink><div className="nav-explore"><button type="button" className="nav-menu-button"><span>Explore</span><span className="nav-chevron" aria-hidden="true">⌄</span></button><div className="explore-menu"><NavLink to="/services">BIS Services</NavLink><NavLink to="/standards">Standards</NavLink><NavLink to="/recommend">Product Analyzer</NavLink><NavLink to="/laboratories">Testing Laboratories</NavLink><NavLink to="/related-standards">Related Standards</NavLink><NavLink to="/consultants">Consultants</NavLink></div></div><NavLink to="/assistant">AI Assistant</NavLink><NavLink to="/how-it-works">How It Works</NavLink><NavLink to="/about">About BIS</NavLink></nav><div className="header-actions"><label className="language-control"><img className="language-globe" src="/globe.jpeg" alt="Language" /><span className="language-value"><select className="language-select" value={language} onChange={(event) => onLanguageChange(event.target.value)} aria-label="Choose language"><option value="EN">EN</option><option value="HI">HI</option><option value="TE">TE</option></select><span className="nav-chevron" aria-hidden="true">⌄</span></span></label>{role ? <NavLink className="dashboard-link" to="/dashboard">Dashboard</NavLink> : <><NavLink className="login-link" to="/login" onClick={() => onOpenAuth(null)}>Log in</NavLink><NavLink className="button button-small" to="/signup" onClick={() => onOpenAuth(null)}>Create account <span>↗</span></NavLink></>}</div></header>
}

function ChatAssistant() {
    const navigate = useNavigate()
    const location = useLocation()
    if (location.pathname === '/assistant') return null
    return <div className="chat-widget"><button className="chat-toggle" aria-label="Open chat assistant" onClick={() => navigate('/assistant')}>✦<span className="chat-ping"></span></button></div>
}

function AuthModal({ mode, onClose, onSwitch }) {
    return <div className="modal-backdrop" onClick={onClose}><div className="auth-modal" onClick={(event) => event.stopPropagation()}><button className="modal-close" onClick={onClose} aria-label="Close authentication dialog">×</button><p className="eyebrow"><span></span> Welcome to standIQ</p><h2>{mode === 'login' ? 'Good to see you.' : 'Start with clarity.'}</h2><p>{mode === 'login' ? 'Log in to keep your standards journey moving.' : 'Create an account to save your standards and conversations.'}</p><label>Email address<input type="email" placeholder="you@example.com" /></label><label>Password<input type="password" placeholder="Enter your password" /></label><button className="button auth-submit">{mode === 'login' ? 'Log in' : 'Create account'} <span>↗</span></button><button className="switch-auth" onClick={onSwitch}>{mode === 'login' ? 'New to standIQ? Create an account' : 'Already have an account? Log in'}</button></div></div>
}

function App() {
    const [authMode, setAuthMode] = useState(null)
    const [role, setRole] = useState(null)
    const [language, setLanguage] = useState('EN')
    return <BrowserRouter><div className="app-shell"><SiteHeader onOpenAuth={setAuthMode} role={role} language={language} onLanguageChange={setLanguage} /><main><Routes><Route path="/" element={<HomePage />} /><Route path="/services" element={<ServicesPage />} /><Route path="/standards" element={<StandardsPage />} /><Route path="/recommend" element={<RecommendationPage />} /><Route path="/laboratories" element={<DiscoveryPage type="laboratories" />} /><Route path="/related-standards" element={<DiscoveryPage type="related" />} /><Route path="/consultants" element={<DiscoveryPage type="consultants" />} /><Route path="/how-it-works" element={<HowItWorksPage />} /><Route path="/about" element={<AboutPage />} /><Route path="/assistant" element={<AssistantPage />} /><Route path="/login" element={<AuthPage mode="login" onAuthenticated={setRole} />} /><Route path="/signup" element={<AuthPage mode="signup" onAuthenticated={setRole} />} /><Route path="/dashboard" element={role ? <DashboardPage role={role} /> : <Navigate to="/login" replace />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></main><footer><NavLink className="brand" to="/"><img src="/logo.jpeg" alt="" /><span>stand<span>IQ</span></span></NavLink><p>Intelligence for Indian standards.</p><span>© 2026 standIQ</span></footer><ChatAssistant />{authMode && <AuthModal mode={authMode} onClose={() => setAuthMode(null)} onSwitch={() => setAuthMode(authMode === 'login' ? 'signup' : 'login')} />}</div></BrowserRouter>
}

export default App