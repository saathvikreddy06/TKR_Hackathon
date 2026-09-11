import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

const ROUTE_TITLES = {
    '/': 'HOME',
    '/about': 'ABOUT BIS',
    '/about-us': 'ABOUT US',
    '/login': 'LOG IN',
    '/signup': 'CREATE ACCOUNT',
    '/services': 'BIS SERVICES',
    '/standards': 'STANDARDS',
    '/recommend': 'PRODUCT ANALYZER',
    '/laboratories': 'TESTING LABORATORIES',
    '/consultants': 'CONSULTANTS',
    '/assistant': 'AI ASSISTANT',
    '/dashboard': 'DASHBOARD'
}

export default function PageTitleTransition() {
    const location = useLocation()
    const [phase, setPhase] = useState('title') // 'title' | 'fade_overlay' | 'done'

    // Match route title
    const rawTitle = ROUTE_TITLES[location.pathname]
    const title = rawTitle || location.pathname.substring(1).replace(/-/g, ' ').toUpperCase() || 'STANDIQ'

    // Accessibility check for reduced motion
    const prefersReducedMotion =
        typeof window !== 'undefined' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches

    useEffect(() => {
        if (!prefersReducedMotion) {
            setPhase('title')
        }
    }, [location.pathname, prefersReducedMotion])

    if (prefersReducedMotion || phase === 'done') return null

    return (
        <AnimatePresence mode="wait">
            <div
                key={location.pathname}
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
                            setPhase('done')
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

                {/* Elastic Slide Title Animation */}
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
                            <span className="page-title-text">{title}</span>
                        </div>
                    </motion.div>
                )}
            </div>
        </AnimatePresence>
    )
}
