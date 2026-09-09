import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

function AuthPage({ mode = 'login', onAuthenticated }) {
    const [currentMode, setCurrentMode] = useState(mode)
    const [role, setRole] = useState('user')
    const navigate = useNavigate()
    const submit = (event) => { event.preventDefault(); onAuthenticated(role); navigate('/dashboard') }
    return <section className="auth-page"><div className="auth-panel"><Link className="back-link" to="/">← Back to home</Link><p className="eyebrow"><span></span> standIQ account</p><h1>{currentMode === 'login' ? 'Welcome back.' : 'Start with clarity.'}</h1><p>{currentMode === 'login' ? 'Continue your standards journey.' : 'Save standards, conversations, and consultations in one place.'}</p><form onSubmit={submit}><label>Email address<input type="email" placeholder="you@example.com" required /></label><label>Password<input type="password" placeholder="Enter your password" required /></label>{currentMode === 'signup' && <label>Use standIQ as<select value={role} onChange={(event) => setRole(event.target.value)}><option value="user">User / consultancy seeker</option><option value="consultant">Consultant</option></select></label>}<button className="button auth-submit" type="submit">{currentMode === 'login' ? 'Log in' : 'Create account'} <span>↗</span></button></form><button className="switch-auth" onClick={() => setCurrentMode(currentMode === 'login' ? 'signup' : 'login')}>{currentMode === 'login' ? 'New to standIQ? Create an account' : 'Already have an account? Log in'}</button><button className="password-link" type="button">Forgot password?</button></div><div className="auth-promise"><span>✦</span><h2>Trusted guidance,<br /><em>clear next steps.</em></h2><p>Your account helps you return to saved standards and human consultation when evidence is incomplete.</p></div></section>
}

export default AuthPage
