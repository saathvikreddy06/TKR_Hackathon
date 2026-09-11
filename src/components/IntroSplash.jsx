import { motion } from 'framer-motion'

const LETTERS = ['S', 'T', 'A', 'N', 'D', 'I', 'Q']

export default function IntroSplash({ onComplete }) {
    const isLastLetter = (index) => index === LETTERS.length - 1

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
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 99999,
                overflow: 'hidden',
                userSelect: 'none'
            }}
        >
            <div
                style={{
                    position: 'relative',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center'
                }}
            >
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        letterSpacing: '-0.04em'
                    }}
                >
                    {LETTERS.map((letter, index) => (
                        <motion.span
                            key={index}
                            initial={{
                                x: '-100vw',
                                opacity: 0,
                                scale: 0.85,
                                rotate: -8,
                                filter: 'blur(10px)'
                            }}
                            animate={{
                                x: ['-100vw', '4vw', '0vw', '0vw', '100vw'],
                                opacity: [0, 1, 1, 1, 0],
                                scale: [0.85, 1.04, 1, 1, 0.9],
                                rotate: [-8, 3, 0, 0, 8],
                                filter: [
                                    'blur(10px)',
                                    'blur(0px)',
                                    'blur(0px)',
                                    'blur(0px)',
                                    'blur(8px)'
                                ]
                            }}
                            transition={{
                                duration: 2.7,
                                delay: index * 0.07,
                                times: [0, 0.35, 0.45, 0.72, 1],
                                ease: ['easeOut', 'easeInOut', 'linear', 'easeIn']
                            }}
                            onAnimationComplete={() => {
                                if (isLastLetter(index) && onComplete) {
                                    onComplete()
                                }
                            }}
                            style={{
                                display: 'inline-block',
                                color: '#17271f',
                                font: "900 clamp(4rem, 10vw, 8.5rem) 'DM Mono', monospace",
                                textTransform: 'uppercase',
                                willChange: 'transform, opacity, filter'
                            }}
                        >
                            {letter}
                        </motion.span>
                    ))}
                </div>

                {/* Subtle Orange Accent Line under the assembled word during center hold */}
                <motion.div
                    initial={{ scaleX: 0, opacity: 0 }}
                    animate={{
                        scaleX: [0, 0, 1, 1, 0],
                        opacity: [0, 0, 0.9, 0.9, 0]
                    }}
                    transition={{
                        duration: 2.7,
                        times: [0, 0.42, 0.52, 0.72, 0.95],
                        ease: 'easeInOut'
                    }}
                    style={{
                        height: '4px',
                        width: '80%',
                        marginTop: '8px',
                        background: '#e07949',
                        borderRadius: '2px',
                        transformOrigin: 'center'
                    }}
                />
            </div>
        </div>
    )
}
