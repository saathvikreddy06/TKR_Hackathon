import { useEffect, useState } from 'react'
import {
    BrowserRouter,
    Navigate,
    NavLink,
    Route,
    Routes,
    useLocation,
    useNavigate
} from 'react-router-dom'

import AssistantPage from './pages/AssistantPage'
import AboutPage from './pages/AboutPage'
import AboutUsPage from './pages/AboutUsPage'
import HomePage from './pages/HomePage'
import ServicesPage from './pages/ServicesPage'
import StandardsPage from './pages/StandardsPage'
import RecommendationPage from './pages/RecommendationPage'
import AuthPage from './pages/AuthPage'
import DashboardPage from './pages/DashboardPage'
import DiscoveryPage from './pages/DiscoveryPage'

import {
    subscribeToAuthChanges,
    getUserProfile,
    logoutUser
} from './pages/services/authService'

import './App.css'


function SiteHeader({ onOpenAuth, role, language, onLanguageChange }) {
    const [isExploreOpen, setIsExploreOpen] = useState(false)
    const [isLoggingOut, setIsLoggingOut] = useState(false)
    const navigate = useNavigate()

    const closeExploreMenu = () => setIsExploreOpen(false)

    const handleLogout = async () => {
        setIsLoggingOut(true)

        try {
            await logoutUser()
            navigate('/')
        } catch (error) {
            console.error('Logout failed:', error)
        } finally {
            setIsLoggingOut(false)
        }
    }

    return (
        <header className="site-header">
            <NavLink
                className="brand"
                to="/"
                aria-label="standIQ home"
            >
                <img src="/logo.jpeg" alt="standIQ logo" />
                <span>
                    stand<span>IQ</span>
                </span>
            </NavLink>

            <nav
                className="main-nav"
                aria-label="Main navigation"
            >
                <NavLink to="/" end>
                    Home
                </NavLink>

                <div
                    className={`nav-explore ${isExploreOpen ? 'is-open' : ''
                        }`}
                >
                    <button
                        type="button"
                        className="nav-menu-button"
                        onClick={() =>
                            setIsExploreOpen(
                                (isOpen) => !isOpen
                            )
                        }
                        aria-expanded={isExploreOpen}
                    >
                        <span>Explore</span>
                        <span
                            className="nav-chevron"
                            aria-hidden="true"
                        >
                            ⌄
                        </span>
                    </button>

                    <div className="explore-menu">
                        {[
                            '/services',
                            '/standards',
                            '/recommend',
                            '/laboratories',
                            '/related-standards',
                            '/consultants'
                        ].map((path, index) => (
                            <NavLink
                                key={path}
                                to={path}
                                onClick={closeExploreMenu}
                            >
                                {
                                    [
                                        'BIS Services',
                                        'Standards',
                                        'Product Analyzer',
                                        'Testing Laboratories',
                                        'Related Standards',
                                        'Consultants'
                                    ][index]
                                }
                            </NavLink>
                        ))}
                    </div>
                </div>

                <NavLink to="/assistant">
                    AI Assistant
                </NavLink>

                <NavLink to="/about">
                    About BIS
                </NavLink>
            </nav>

            <div className="header-actions">
                <label className="language-control">
                    <img
                        className="language-globe"
                        src="/globe.jpeg"
                        alt="Language"
                    />

                    <span className="language-value">
                        <select
                            className="language-select"
                            value={language}
                            onChange={(event) =>
                                onLanguageChange(
                                    event.target.value
                                )
                            }
                            aria-label="Choose language"
                        >
                            <option value="EN">EN</option>
                            <option value="HI">HI</option>
                            <option value="TE">TE</option>
                        </select>

                        <span
                            className="nav-chevron"
                            aria-hidden="true"
                        >
                            ⌄
                        </span>
                    </span>
                </label>

                {role ? (
                    <>
                        <NavLink
                            className="dashboard-link"
                            to="/dashboard"
                        >
                            Dashboard
                        </NavLink>

                        <button
                            className="login-link"
                            type="button"
                            onClick={handleLogout}
                            disabled={isLoggingOut}
                        >
                            {isLoggingOut ? 'Logging out...' : 'Log out'}
                        </button>
                    </>
                ) : (
                    <>
                        <NavLink
                            className="login-link"
                            to="/login"
                            onClick={() =>
                                onOpenAuth(null)
                            }
                        >
                            Log in
                        </NavLink>

                        <NavLink
                            className="button button-small"
                            to="/signup"
                            onClick={() =>
                                onOpenAuth(null)
                            }
                        >
                            Create account <span>↗</span>
                        </NavLink>
                    </>
                )}
            </div>
        </header>
    )
}


function ChatAssistant() {
    const navigate = useNavigate()
    const location = useLocation()

    if (location.pathname === '/assistant') {
        return null
    }

    return (
        <div className="chat-widget">
            <button
                className="chat-toggle"
                aria-label="Open chat assistant"
                onClick={() => navigate('/assistant')}
            >
                ✦
                <span className="chat-ping"></span>
            </button>
        </div>
    )
}


function ScrollToTop() {
    const { pathname, hash } = useLocation()

    useEffect(() => {
        if (hash) {
            document
                .getElementById(hash.slice(1))
                ?.scrollIntoView()
        } else {
            window.scrollTo(0, 0)
        }
    }, [pathname, hash])

    return null
}


function ProtectedRoute({ role, children }) {
    return role
        ? children
        : <Navigate to="/login" replace />
}


function AuthModal({ mode, onClose, onSwitch }) {
    return (
        <div
            className="modal-backdrop"
            onClick={onClose}
        >
            <div
                className="auth-modal"
                onClick={(event) =>
                    event.stopPropagation()
                }
            >
                <button
                    className="modal-close"
                    onClick={onClose}
                    aria-label="Close authentication dialog"
                >
                    ×
                </button>

                <p className="eyebrow">
                    <span></span> Welcome to standIQ
                </p>

                <h2>
                    {mode === 'login'
                        ? 'Good to see you.'
                        : 'Start with clarity.'}
                </h2>

                <p>
                    {mode === 'login'
                        ? 'Log in to keep your standards journey moving.'
                        : 'Create an account to save your standards and conversations.'}
                </p>

                <label>
                    Email address
                    <input
                        type="email"
                        placeholder="you@example.com"
                    />
                </label>

                <label>
                    Password
                    <input
                        type="password"
                        placeholder="Enter your password"
                    />
                </label>

                <button className="button auth-submit">
                    {mode === 'login'
                        ? 'Log in'
                        : 'Create account'}
                    <span>↗</span>
                </button>

                <button
                    className="switch-auth"
                    onClick={onSwitch}
                >
                    {mode === 'login'
                        ? 'New to standIQ? Create an account'
                        : 'Already have an account? Log in'}
                </button>
            </div>
        </div>
    )
}


function App() {
    const [authMode, setAuthMode] = useState(null)
    const [role, setRole] = useState(null)
    const [language, setLanguage] = useState('EN')

    // Firebase authentication loading state
    const [authLoading, setAuthLoading] = useState(true)

    useEffect(() => {
        let authChangeId = 0

        const unsubscribe = subscribeToAuthChanges(
            async (user) => {
                const currentAuthChangeId = ++authChangeId

                setAuthLoading(true)

                // Clear access immediately while the profile is being checked.
                setRole(null)

                if (user) {
                    try {
                        // Get the user's profile from Firestore
                        const profile =
                            await getUserProfile(
                                user.uid
                            )

                        if (currentAuthChangeId !== authChangeId) {
                            return
                        }

                        if (profile) {
                            setRole(profile.role)
                        }

                    } catch (error) {
                        console.error(
                            'Failed to load user profile:',
                            error
                        )

                        if (currentAuthChangeId === authChangeId) {
                            setRole(null)
                        }
                    }

                }

                // Firebase has finished checking authentication
                setAuthLoading(false)
            }
        )

        // Cleanup listener when App unmounts
        return () => unsubscribe()
    }, [])


    // Wait until Firebase determines authentication state
    if (authLoading) {
        return (
            <div className="app-shell">
                <main>
                    <div
                        style={{
                            minHeight: '100vh',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <p>Loading standIQ...</p>
                    </div>
                </main>
            </div>
        )
    }


    return (
        <BrowserRouter>
            <ScrollToTop />

            <div className="app-shell">

                <SiteHeader
                    onOpenAuth={setAuthMode}
                    role={role}
                    language={language}
                    onLanguageChange={setLanguage}
                />

                <main>
                    <Routes>

                        <Route
                            path="/"
                            element={<HomePage />}
                        />

                        <Route
                            path="/about"
                            element={<AboutPage />}
                        />

                        <Route
                            path="/about-us"
                            element={<AboutUsPage />}
                        />

                        <Route
                            path="/login"
                            element={
                                <AuthPage
                                    mode="login"
                                    onAuthenticated={setRole}
                                />
                            }
                        />

                        <Route
                            path="/signup"
                            element={
                                <AuthPage
                                    mode="signup"
                                    onAuthenticated={setRole}
                                />
                            }
                        />

                        <Route
                            path="/services"
                            element={
                                <ProtectedRoute role={role}>
                                    <ServicesPage />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="/standards"
                            element={
                                <ProtectedRoute role={role}>
                                    <StandardsPage />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="/recommend"
                            element={
                                <ProtectedRoute role={role}>
                                    <RecommendationPage />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="/laboratories"
                            element={
                                <ProtectedRoute role={role}>
                                    <DiscoveryPage
                                        type="laboratories"
                                    />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="/related-standards"
                            element={
                                <ProtectedRoute role={role}>
                                    <DiscoveryPage
                                        type="related"
                                    />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="/consultants"
                            element={
                                <ProtectedRoute role={role}>
                                    <DiscoveryPage
                                        type="consultants"
                                    />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="/how-it-works"
                            element={
                                <ProtectedRoute role={role}>
                                    <Navigate
                                        to="/#how-it-works"
                                        replace
                                    />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="/assistant"
                            element={
                                <ProtectedRoute role={role}>
                                    <AssistantPage />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="/dashboard"
                            element={
                                <ProtectedRoute role={role}>
                                    <DashboardPage
                                        role={role}
                                    />
                                </ProtectedRoute>
                            }
                        />

                        <Route
                            path="*"
                            element={
                                <Navigate
                                    to="/"
                                    replace
                                />
                            }
                        />

                    </Routes>
                </main>

                <footer>
                    <NavLink
                        className="brand"
                        to="/"
                    >
                        <img
                            src="/logo.jpeg"
                            alt=""
                        />

                        <span>
                            stand<span>IQ</span>
                        </span>
                    </NavLink>

                    <p>
                        Intelligence for Indian standards.
                    </p>

                    <span>
                        © 2026 standIQ
                    </span>
                </footer>

                <ChatAssistant />

                {authMode && (
                    <AuthModal
                        mode={authMode}
                        onClose={() =>
                            setAuthMode(null)
                        }
                        onSwitch={() =>
                            setAuthMode(
                                authMode === 'login'
                                    ? 'signup'
                                    : 'login'
                            )
                        }
                    />
                )}

            </div>
        </BrowserRouter>
    )
}

export default App