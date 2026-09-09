import { useState } from 'react'
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import AssistantPage from './pages/AssistantPage'
import AboutPage from './pages/AboutPage'
import HomePage from './pages/HomePage'
import HowItWorksPage from './pages/HowItWorksPage'
import ServicesPage from './pages/ServicesPage'
import './App.css'

function SiteHeader({ onOpenAuth }) {
    return <header className="site-header"><NavLink className="brand" to="/" aria-label="standIQ home"><img src="/logo.jpeg" alt="standIQ logo" /><span>stand<span>IQ</span></span></NavLink><nav className="main-nav" aria-label="Main navigation"><NavLink to="/" end>Home</NavLink><NavLink to="/services">BIS services</NavLink><NavLink to="/how-it-works">How it works</NavLink><NavLink to="/about">About BIS</NavLink></nav><div className="header-actions"><button className="login-link" onClick={() => onOpenAuth('login')}>Log in</button><button className="button button-small" onClick={() => onOpenAuth('signup')}>Create account <span>↗</span></button></div></header>
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
    return <BrowserRouter><div className="app-shell"><SiteHeader onOpenAuth={setAuthMode} /><main><Routes><Route path="/" element={<HomePage />} /><Route path="/services" element={<ServicesPage />} /><Route path="/how-it-works" element={<HowItWorksPage />} /><Route path="/about" element={<AboutPage />} /><Route path="/assistant" element={<AssistantPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></main><footer><NavLink className="brand" to="/"><img src="/logo.jpeg" alt="" /><span>stand<span>IQ</span></span></NavLink><p>Intelligence for Indian standards.</p><span>© 2026 standIQ</span></footer><ChatAssistant />{authMode && <AuthModal mode={authMode} onClose={() => setAuthMode(null)} onSwitch={() => setAuthMode(authMode === 'login' ? 'signup' : 'login')} />}</div></BrowserRouter>
}

export default App