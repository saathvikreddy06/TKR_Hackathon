import { useEffect, useRef } from 'react'

export default function ParticleBackground({
    color = '224, 121, 73', // Site orange accent (#e07949 / #E38A54)
    dotRadius = 2.5,
    gridSpacing = 34,
    maxDistance = 140,
    pushForce = 45,
    lerpFactor = 0.08,
    idleTimeout = 200 // Time in ms before cursor is considered idle
}) {
    const canvasRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return

        const ctx = canvas.getContext('2d')
        let animationFrameId
        let dots = []
        let mouse = { x: -1000, y: -1000, active: false }
        let lastMoveTimestamp = 0

        // Accessibility & Device Checks
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
        const isTouchDevice = 'ontouchstart' in window || (navigator.maxTouchPoints > 0)

        const initDots = (width, height) => {
            dots = []
            const cols = Math.ceil(width / gridSpacing) + 1
            const rows = Math.ceil(height / gridSpacing) + 1

            for (let i = 0; i < cols; i++) {
                for (let j = 0; j < rows; j++) {
                    const originX = i * gridSpacing
                    const originY = j * gridSpacing
                    dots.push({
                        originX,
                        originY,
                        x: originX,
                        y: originY,
                        targetX: originX,
                        targetY: originY,
                        opacity: 0,
                        targetOpacity: 0,
                        radius: dotRadius
                    })
                }
            }
        }

        const handleResize = () => {
            const width = window.innerWidth
            const height = window.innerHeight
            const dpr = window.devicePixelRatio || 1

            canvas.width = width * dpr
            canvas.height = height * dpr
            canvas.style.width = `${width}px`
            canvas.style.height = `${height}px`

            ctx.scale(dpr, dpr)
            initDots(width, height)
        }

        const handleMouseMove = (e) => {
            if (isTouchDevice || prefersReducedMotion) return
            mouse.x = e.clientX
            mouse.y = e.clientY
            mouse.active = true
            lastMoveTimestamp = performance.now()
        }

        const handleMouseLeave = () => {
            mouse.x = -1000
            mouse.y = -1000
            mouse.active = false
        }

        if (!isTouchDevice && !prefersReducedMotion) {
            window.addEventListener('mousemove', handleMouseMove)
            window.addEventListener('mouseleave', handleMouseLeave)
        }
        window.addEventListener('resize', handleResize)

        handleResize()

        const render = () => {
            const width = window.innerWidth
            const height = window.innerHeight
            const now = performance.now()
            const isMoving = (now - lastMoveTimestamp) < idleTimeout

            ctx.clearRect(0, 0, width, height)

            for (let i = 0; i < dots.length; i++) {
                const dot = dots[i]

                if (!prefersReducedMotion && !isTouchDevice) {
                    const dx = dot.originX - mouse.x
                    const dy = dot.originY - mouse.y
                    const dist = Math.sqrt(dx * dx + dy * dy)

                    // Dots react ONLY when cursor is actively moving AND within distance
                    if (dist < maxDistance && mouse.active && isMoving) {
                        const factor = 1 - dist / maxDistance
                        const angle = Math.atan2(dy, dx)
                        const push = factor * pushForce

                        dot.targetX = dot.originX + Math.cos(angle) * push
                        dot.targetY = dot.originY + Math.sin(angle) * push
                        dot.targetOpacity = 0.03 + factor * 0.75
                    } else {
                        dot.targetX = dot.originX
                        dot.targetY = dot.originY
                        dot.targetOpacity = 0.03
                    }

                    // Smooth position & opacity easing (lerp)
                    dot.x += (dot.targetX - dot.x) * lerpFactor
                    dot.y += (dot.targetY - dot.y) * lerpFactor
                    dot.opacity += (dot.targetOpacity - dot.opacity) * lerpFactor
                } else {
                    // Static subtle display for reduced motion or touch devices
                    dot.x = dot.originX
                    dot.y = dot.originY
                    dot.opacity = 0.04
                }

                if (dot.opacity > 0.005) {
                    ctx.fillStyle = `rgba(${color}, ${dot.opacity})`
                    ctx.beginPath()
                    ctx.arc(dot.x, dot.y, dot.radius, 0, Math.PI * 2)
                    ctx.fill()
                }
            }

            if (!prefersReducedMotion) {
                animationFrameId = requestAnimationFrame(render)
            }
        }

        render()

        return () => {
            if (animationFrameId) cancelAnimationFrame(animationFrameId)
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('mouseleave', handleMouseLeave)
            window.removeEventListener('resize', handleResize)
        }
    }, [color, dotRadius, gridSpacing, maxDistance, pushForce, lerpFactor, idleTimeout])

    return (
        <canvas
            ref={canvasRef}
            className="particle-background-canvas"
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100vw',
                height: '100vh',
                pointerEvents: 'none',
                zIndex: 0
            }}
        />
    )
}
