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

    // Match route title
    const rawTitle = ROUTE_TITLES[location.pathname]
    const title = rawTitle || location.pathname.substring(1).replace(/-/g, ' ').toUpperCase() || 'STANDIQ'

    // Accessibility check for reduced motion
    const prefersReducedMotion =
        typeof window !== 'undefined' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (prefersReducedMotion) return null

    return (
        <AnimatePresence mode="wait">
            <motion.div
                key={location.pathname}
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
        </AnimatePresence>
    )
}
