import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function PageTitleTransition() {
    // Accessibility check for reduced motion
    const prefersReducedMotion =
        typeof window !== 'undefined' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches

    // Check if user has already seen the StandIQ intro in this browser session
    const [shouldPlay] = useState(() => {
        if (prefersReducedMotion) return false
        try {
            const hasSeen = sessionStorage.getItem('hasSeenIntro')
            return !hasSeen
        } catch {
            return true
        }
    })

    const [phase, setPhase] = useState(() => (shouldPlay ? 'title' : 'done'))

    if (!shouldPlay || phase === 'done') return null

    const handleOverlayFadeComplete = () => {
        try {
            sessionStorage.setItem('hasSeenIntro', 'true')
        } catch (e) {
            console.error('Failed to set sessionStorage:', e)
        }
        setPhase('done')
    }

    return (
        <AnimatePresence mode="wait">
            <div
                style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    pointerEvents: 'none',
                    zIndex: 9998
                }}
            >
                {/* Opaque Blank Screen Overlay */}
                <motion.div
                    initial={{ opacity: 1 }}
                    animate={{ opacity: phase === 'fade_overlay' ? 0 : 1 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                    onAnimationComplete={() => {
                        if (phase === 'fade_overlay') {
                            handleOverlayFadeComplete()
                        }
                    }}
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        width: '100vw',
                        height: '100vh',
                        background: '#f7f5ef',
                        zIndex: 9998
                    }}
                />

                {/* Elastic Slide Title Animation for "StandIQ" */}
                {phase === 'title' && (
                    <motion.div
                        initial={{
                            x: '100vw',
                            opacity: 0,
                            scale: 1.08,
                            filter: 'blur(8px)'
                        }}
                        animate={{
                            x: ['100vw', '-4vw', '0vw', '0vw', '-100vw'],
                            opacity: [0, 1, 1, 1, 0],
                            scale: [1.08, 1.03, 1, 1, 0.95],
                            filter: [
                                'blur(8px)',
                                'blur(0px)',
                                'blur(0px)',
                                'blur(0px)',
                                'blur(6px)'
                            ]
                        }}
                        transition={{
                            duration: 1.9,
                            times: [0, 0.22, 0.32, 0.72, 1],
                            ease: ['easeOut', 'easeInOut', 'linear', 'easeIn']
                        }}
                        onAnimationComplete={() => {
                            setPhase('fade_overlay')
                        }}
                        style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            width: '100vw',
                            height: '100vh',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            pointerEvents: 'none',
                            zIndex: 9999
                        }}
                    >
                        <div className="page-title-transition-card">
                            <span className="page-title-dot" />
                            <span className="page-title-text">StandIQ</span>
                        </div>
                    </motion.div>
                )}
            </div>
        </AnimatePresence>
    )
}
