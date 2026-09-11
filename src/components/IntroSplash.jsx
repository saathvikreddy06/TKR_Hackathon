import { motion } from 'framer-motion'

export default function IntroSplash({ onComplete }) {
    return (
        <div
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100vw',
                height: '100vh',
                background: '#f7f5ef',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 99999,
                overflow: 'hidden'
            }}
        >
            <motion.div
                initial={{
                    x: '100vw',
                    opacity: 0,
                    scale: 1.05,
                    filter: 'blur(8px)'
                }}
                animate={{
                    x: ['100vw', '-4vw', '0vw', '0vw', '-100vw'],
                    opacity: [0, 1, 1, 1, 0],
                    scale: [1.05, 1.03, 1, 1, 0.95],
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
                    if (onComplete) {
                        onComplete()
                    }
                }}
                style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none'
                }}
            >
                <div className="page-title-transition-card">
                    <span className="page-title-dot" />
                    <span className="page-title-text">StandIQ</span>
                </div>
            </motion.div>
        </div>
    )
}
