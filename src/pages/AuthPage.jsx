import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import {
    registerUser,
    loginUser,
    logoutUser
} from './services/authService'


function AuthPage({ mode = 'login', onAuthenticated }) {

    const [currentMode, setCurrentMode] = useState(mode)

    const [username, setUsername] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')

    const [role, setRole] = useState('user')

    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const navigate = useNavigate()


    // ========================================
    // FORM SUBMISSION
    // ========================================

    const submit = async (event) => {

        event.preventDefault()

        setError('')
        setLoading(true)

        try {

            // ========================================
            // SIGNUP
            // ========================================

            if (currentMode === 'signup') {

                const user = await registerUser(
                    username,
                    email,
                    password,
                    role
                )

                console.log(
                    'Registration successful:',
                    user.uid
                )

                // Tell App.jsx about the user's role
                onAuthenticated(role)

                // Return to home only after successful registration.
                navigate('/', {
                    state: {
                        authMessage: 'Registration successful. Welcome to standIQ.'
                    }
                })

            }

            // ========================================
            // LOGIN
            // ========================================

            else {

                const user = await loginUser(
                    email,
                    password
                )

                console.log(
                    'Login successful:',
                    user.uid
                )

                /*
                 * Do NOT set the role here.
                 *
                 * App.jsx will retrieve the user's
                 * actual role from Firestore.
                 */

                navigate('/', {
                    state: {
                        authMessage: 'Login successful. Welcome back.'
                    }
                })
            }

        }

        // ========================================
        // AUTHENTICATION ERRORS
        // ========================================

        catch (error) {

            console.error(
                'Authentication error:',
                error
            )

            // Ensure a previously persisted session cannot make a failed
            // login appear successful.
            try {
                await logoutUser()
            } catch (logoutError) {
                console.error('Failed to clear authentication state:', logoutError)
            }

            if (
                error.code === 'auth/invalid-credential' ||
                error.code === 'auth/wrong-password' ||
                error.code === 'auth/user-not-found'
            ) {

                setError(
                    'Invalid email or password.'
                )

            }

            else if (
                error.code === 'auth/invalid-email'
            ) {

                setError(
                    'Please enter a valid email address.'
                )

            }

            else if (
                error.code === 'auth/email-already-in-use'
            ) {

                setError(
                    'An account with this email already exists.'
                )

            }

            else if (
                error.code === 'auth/weak-password'
            ) {

                setError(
                    'Password should be at least 6 characters.'
                )

            }

            else if (
                error.code === 'auth/too-many-requests'
            ) {

                setError(
                    'Too many attempts. Please try again later.'
                )

            }

            else {

                setError(
                    error.message ||
                    'Authentication failed. Please try again.'
                )
            }

        }

        finally {

            setLoading(false)
        }
    }


    // ========================================
    // SWITCH LOGIN / SIGNUP
    // ========================================

    const switchMode = () => {

        setError('')

        setCurrentMode(
            currentMode === 'login'
                ? 'signup'
                : 'login'
        )
    }


    return (

        <section className="auth-page">

            <div className="auth-panel">

                <Link
                    className="back-link"
                    to="/"
                >
                    ← Back to home
                </Link>


                <p className="eyebrow">
                    <span></span> standIQ account
                </p>


                <h1>
                    {currentMode === 'login'
                        ? 'Welcome back.'
                        : 'Start with clarity.'
                    }
                </h1>


                <p>
                    {currentMode === 'login'
                        ? 'Continue your standards journey.'
                        : 'Save standards, conversations, and consultations in one place.'
                    }
                </p>


                <form onSubmit={submit}>

                    {/* ========================================
                        USERNAME
                        Only shown during signup
                    ======================================== */}

                    {currentMode === 'signup' && (

                        <label>

                            Username

                            <input
                                type="text"
                                placeholder="Choose a username"
                                value={username}
                                onChange={(event) =>
                                    setUsername(
                                        event.target.value
                                    )
                                }
                                required
                            />

                        </label>
                    )}


                    {/* ========================================
                        EMAIL
                    ======================================== */}

                    <label>

                        Email address

                        <input
                            type="email"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(event) =>
                                setEmail(
                                    event.target.value
                                )
                            }
                            required
                        />

                    </label>


                    {/* ========================================
                        PASSWORD
                    ======================================== */}

                    <label>

                        Password

                        <input
                            type="password"
                            placeholder="Enter your password"
                            value={password}
                            onChange={(event) =>
                                setPassword(
                                    event.target.value
                                )
                            }
                            required
                            minLength={6}
                        />

                    </label>


                    {/* ========================================
                        ROLE
                        Only shown during signup
                    ======================================== */}

                    {currentMode === 'signup' && (

                        <label>

                            Use standIQ as

                            <select
                                value={role}
                                onChange={(event) =>
                                    setRole(
                                        event.target.value
                                    )
                                }
                            >

                                <option value="user">
                                    User / consultancy seeker
                                </option>

                                <option value="consultant">
                                    Consultant
                                </option>

                            </select>

                        </label>
                    )}


                    {/* ========================================
                        ERROR MESSAGE
                    ======================================== */}

                    {error && (

                        <p
                            className="auth-error"
                            role="alert"
                        >
                            {error}
                        </p>
                    )}


                    {/* ========================================
                        SUBMIT BUTTON
                    ======================================== */}

                    <button
                        className="button auth-submit"
                        type="submit"
                        disabled={loading}
                    >

                        {loading
                            ? 'Please wait...'
                            : currentMode === 'login'
                                ? 'Log in'
                                : 'Create account'
                        }

                        {!loading && (
                            <span>↗</span>
                        )}

                    </button>

                </form>


                {/* ========================================
                    SWITCH LOGIN / SIGNUP
                ======================================== */}

                <button
                    className="switch-auth"
                    type="button"
                    onClick={switchMode}
                >

                    {currentMode === 'login'
                        ? 'New to standIQ? Create an account'
                        : 'Already have an account? Log in'
                    }

                </button>


                {/* ========================================
                    FORGOT PASSWORD
                ======================================== */}

                <button
                    className="password-link"
                    type="button"
                    onClick={() =>
                        setError(
                            'Password reset will be added next.'
                        )
                    }
                >
                    Forgot password?
                </button>

            </div>


            {/* ========================================
                RIGHT SIDE PROMISE
            ======================================== */}

            <div className="auth-promise">

                <span>✦</span>

                <h2>
                    Trusted guidance,
                    <br />
                    <em>clear next steps.</em>
                </h2>

                <p>
                    Your account helps you return to saved
                    standards and human consultation when
                    evidence is incomplete.
                </p>

            </div>

        </section>
    )
}


export default AuthPage