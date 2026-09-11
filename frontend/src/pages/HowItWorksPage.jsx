import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

const STEP_NOTES = {
    1: { num: '01', title: 'Ask a question.', desc: 'We’ll find the signal.' },
    2: { num: '02', title: 'Get a clear direction.', desc: 'Find the standard or service.' },
    3: { num: '03', title: 'Move forward.', desc: 'Trusted, source-backed guidance.' }
}

function HowItWorksPage() {
    const [activeStep, setActiveStep] = useState(1)
    const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)

    useEffect(() => {
        const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
        setPrefersReducedMotion(mediaQuery.matches)
        const handleChange = (e) => setPrefersReducedMotion(e.matches)
        mediaQuery.addEventListener('change', handleChange)
        return () => mediaQuery.removeEventListener('change', handleChange)
    }, [])

    return (
        <section className="how-section page-section" id="how-it-works">
            <div className="how-visual">
                <span className="vertical-word">YOUR NEXT STEP</span>

                {/* SVG Concentric Rings with Draw-in effect & Orbital layers */}
                <div className="concentric-rings-wrapper">
                    <svg viewBox="0 0 440 440" className="concentric-svg">
                        {/* Outer Ring */}
                        <motion.circle
                            cx="220"
                            cy="220"
                            r="210"
                            stroke="#a5bba5"
                            strokeWidth="1.5"
                            fill="none"
                            initial={
                                prefersReducedMotion
                                    ? { strokeDashoffset: 0 }
                                    : { strokeDasharray: 1319, strokeDashoffset: 1319 }
                            }
                            whileInView={{ strokeDashoffset: 0 }}
                            viewport={{ once: true, margin: '-50px' }}
                            transition={{ duration: 1.2, ease: 'easeInOut' }}
                        />

                        {/* Middle Orbit Path Ring */}
                        <motion.circle
                            cx="220"
                            cy="220"
                            r="155"
                            stroke="#8da78f"
                            strokeWidth="1"
                            strokeDasharray="4 6"
                            fill="none"
                            initial={
                                prefersReducedMotion
                                    ? { strokeDashoffset: 0 }
                                    : { strokeDasharray: 973, strokeDashoffset: 973 }
                            }
                            whileInView={{ strokeDashoffset: 0 }}
                            viewport={{ once: true, margin: '-50px' }}
                            transition={{ duration: 1.2, delay: 0.15, ease: 'easeInOut' }}
                        />

                        {/* Inner Ring */}
                        <motion.circle
                            cx="220"
                            cy="220"
                            r="120"
                            stroke="#d77243"
                            strokeWidth="1.5"
                            fill="none"
                            initial={
                                prefersReducedMotion
                                    ? { strokeDashoffset: 0 }
                                    : { strokeDasharray: 754, strokeDashoffset: 754 }
                            }
                            whileInView={{ strokeDashoffset: 0 }}
                            viewport={{ once: true, margin: '-50px' }}
                            transition={{ duration: 1.2, delay: 0.3, ease: 'easeInOut' }}
                        />
                    </svg>

                    {/* Outer Orbit Layer (Clockwise slow orbit) */}
                    <motion.div
                        className="orbit-layer outer-orbit"
                        animate={prefersReducedMotion ? {} : { rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 36, ease: 'linear' }}
                    >
                        {/* Dot 1 - Step 01 */}
                        <div
                            className={`orbital-dot-container dot-step-1 ${activeStep === 1 ? 'is-active' : ''}`}
                            style={{ transform: 'rotate(35deg) translate(155px) rotate(-35deg)' }}
                        >
                            <motion.span
                                className="orbital-dot"
                                animate={
                                    activeStep === 1
                                        ? { scale: 1.5, opacity: 1 }
                                        : { scale: 1, opacity: 0.6 }
                                }
                                transition={{ duration: 0.3 }}
                            />
                        </div>

                        {/* Dot 2 - Step 02 */}
                        <div
                            className={`orbital-dot-container dot-step-2 ${activeStep === 2 ? 'is-active' : ''}`}
                            style={{ transform: 'rotate(155deg) translate(155px) rotate(-155deg)' }}
                        >
                            <motion.span
                                className="orbital-dot"
                                animate={
                                    activeStep === 2
                                        ? { scale: 1.5, opacity: 1 }
                                        : { scale: 1, opacity: 0.6 }
                                }
                                transition={{ duration: 0.3 }}
                            />
                        </div>

                        {/* Dot 3 - Step 03 */}
                        <div
                            className={`orbital-dot-container dot-step-3 ${activeStep === 3 ? 'is-active' : ''}`}
                            style={{ transform: 'rotate(275deg) translate(155px) rotate(-275deg)' }}
                        >
                            <motion.span
                                className="orbital-dot"
                                animate={
                                    activeStep === 3
                                        ? { scale: 1.5, opacity: 1 }
                                        : { scale: 1, opacity: 0.6 }
                                }
                                transition={{ duration: 0.3 }}
                            />
                        </div>
                    </motion.div>

                    {/* Inner Orbit Layer (Counter-clockwise slow orbit) */}
                    <motion.div
                        className="orbit-layer inner-orbit"
                        animate={prefersReducedMotion ? {} : { rotate: -360 }}
                        transition={{ repeat: Infinity, duration: 26, ease: 'linear' }}
                    >
                        <div
                            className="orbital-dot-container ambient-dot-1"
                            style={{ transform: 'rotate(80deg) translate(120px) rotate(-80deg)' }}
                        >
                            <span className="orbital-dot ambient" />
                        </div>
                        <div
                            className="orbital-dot-container ambient-dot-2"
                            style={{ transform: 'rotate(260deg) translate(120px) rotate(-260deg)' }}
                        >
                            <span className="orbital-dot ambient" />
                        </div>
                    </motion.div>
                </div>

                <div className="path-note">
                    <strong>{STEP_NOTES[activeStep].num}</strong>
                    <span>
                        {STEP_NOTES[activeStep].title}
                        <br />
                        {STEP_NOTES[activeStep].desc}
                    </span>
                </div>
            </div>

            <div className="how-copy">
                <p className="eyebrow">
                    <span></span> How standIQ works
                </p>
                <h2>
                    Less searching.
                    <br />
                    <em>More certainty.</em>
                </h2>
                <p>
                    We translate the world of standards into useful next steps. Search by what you make, what you need, or simply ask in your own words.
                </p>

                <div className="steps">
                    <motion.div
                        className={`step-block ${activeStep === 1 ? 'active-step-block' : ''}`}
                        onClick={() => setActiveStep(1)}
                        onViewportEnter={() => setActiveStep(1)}
                        viewport={{ amount: 0.5 }}
                    >
                        <b>01</b>
                        <span>
                            <strong>Tell us what you need</strong>
                            <small>Describe your product or question.</small>
                        </span>
                    </motion.div>

                    <motion.div
                        className={`step-block ${activeStep === 2 ? 'active-step-block' : ''}`}
                        onClick={() => setActiveStep(2)}
                        onViewportEnter={() => setActiveStep(2)}
                        viewport={{ amount: 0.5 }}
                    >
                        <b>02</b>
                        <span>
                            <strong>Get a clear direction</strong>
                            <small>Find the right standard or service.</small>
                        </span>
                    </motion.div>

                    <motion.div
                        className={`step-block ${activeStep === 3 ? 'active-step-block' : ''}`}
                        onClick={() => setActiveStep(3)}
                        onViewportEnter={() => setActiveStep(3)}
                        viewport={{ amount: 0.5 }}
                    >
                        <b>03</b>
                        <span>
                            <strong>Move forward</strong>
                            <small>Use trusted, source-backed guidance.</small>
                        </span>
                    </motion.div>
                </div>
            </div>
        </section>
    )
}

export default HowItWorksPage
