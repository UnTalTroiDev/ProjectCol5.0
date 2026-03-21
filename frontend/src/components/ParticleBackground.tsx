import { useEffect, useRef } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Vec2 {
  x: number
  y: number
}

interface Particle {
  pos: Vec2
  vel: Vec2
  radius: number
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PARTICLE_COUNT_DESKTOP = 60
const PARTICLE_COUNT_MOBILE = 30
const MOBILE_BREAKPOINT = 768
const BASE_SPEED = 0.4
const MIN_RADIUS = 1.5
const MAX_RADIUS = 3.0
const CONNECTION_DISTANCE = 120
const REPULSION_RADIUS = 80
const REPULSION_STRENGTH = 3.5
const PARTICLE_OPACITY = 0.3
const LINE_OPACITY = 0.12
const FALLBACK_COLOR = '240, 244, 255'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function readTextSecondaryRGB(canvas: HTMLCanvasElement): string {
  const raw = getComputedStyle(canvas).getPropertyValue('--color-text-secondary').trim()
  if (raw) {
    // Try to parse hex or rgb from the resolved value
    const hexMatch = raw.match(/^#([0-9a-f]{6})$/i)
    if (hexMatch) {
      const n = parseInt(hexMatch[1], 16)
      return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`
    }
    const rgbMatch = raw.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/)
    if (rgbMatch) return `${rgbMatch[1]}, ${rgbMatch[2]}, ${rgbMatch[3]}`
  }
  return FALLBACK_COLOR
}

function randomBetween(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

function createParticle(width: number, height: number): Particle {
  const angle = Math.random() * 2 * Math.PI
  return {
    pos: { x: Math.random() * width, y: Math.random() * height },
    vel: {
      x: Math.cos(angle) * BASE_SPEED,
      y: Math.sin(angle) * BASE_SPEED,
    },
    radius: randomBetween(MIN_RADIUS, MAX_RADIUS),
  }
}

function initParticles(count: number, width: number, height: number): Particle[] {
  return Array.from({ length: count }, () => createParticle(width, height))
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  // Store mouse position relative to the canvas; null when pointer is outside
  const mouseRef = useRef<Vec2 | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Resolve the color once after mount (CSS variables are available at this point)
    const colorRGB = readTextSecondaryRGB(canvas)

    let animationId = 0
    let particles: Particle[] = []

    // ── Sizing ──────────────────────────────────────────────────────────────

    function resize() {
      if (!canvas) return
      const { offsetWidth: w, offsetHeight: h } = canvas.parentElement ?? canvas
      canvas.width = w
      canvas.height = h

      const isMobile = w < MOBILE_BREAKPOINT
      const targetCount = isMobile ? PARTICLE_COUNT_MOBILE : PARTICLE_COUNT_DESKTOP

      // Preserve existing particles, only add/remove to match target count
      if (particles.length < targetCount) {
        const extra = Array.from(
          { length: targetCount - particles.length },
          () => createParticle(w, h),
        )
        particles = particles.concat(extra)
      } else if (particles.length > targetCount) {
        particles = particles.slice(0, targetCount)
      }

      // Clamp existing particle positions to new bounds
      for (const p of particles) {
        p.pos.x = Math.min(p.pos.x, w)
        p.pos.y = Math.min(p.pos.y, h)
      }
    }

    // Initial sizing + particle creation
    const parent = canvas.parentElement ?? canvas
    const initWidth = parent.offsetWidth || window.innerWidth
    const initHeight = parent.offsetHeight || window.innerHeight
    canvas.width = initWidth
    canvas.height = initHeight

    const isMobileInit = initWidth < MOBILE_BREAKPOINT
    particles = initParticles(
      isMobileInit ? PARTICLE_COUNT_MOBILE : PARTICLE_COUNT_DESKTOP,
      initWidth,
      initHeight,
    )

    // ── ResizeObserver ───────────────────────────────────────────────────────

    const ro = new ResizeObserver(resize)
    ro.observe(canvas.parentElement ?? canvas)

    // ── Mouse handlers ───────────────────────────────────────────────────────

    function handleMouseMove(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect()
      mouseRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      }
    }

    function handleMouseLeave() {
      mouseRef.current = null
    }

    canvas.addEventListener('mousemove', handleMouseMove)
    canvas.addEventListener('mouseleave', handleMouseLeave)

    // ── Animation loop ───────────────────────────────────────────────────────

    function tick() {
      if (!canvas || !ctx) return

      const W = canvas.width
      const H = canvas.height
      const mouse = mouseRef.current

      ctx.clearRect(0, 0, W, H)

      for (const p of particles) {
        // Repulsion: push particle away from mouse
        if (mouse !== null) {
          const dx = p.pos.x - mouse.x
          const dy = p.pos.y - mouse.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < REPULSION_RADIUS && dist > 0) {
            const force = (1 - dist / REPULSION_RADIUS) * REPULSION_STRENGTH
            p.pos.x += (dx / dist) * force
            p.pos.y += (dy / dist) * force
          }
        }

        // Move
        p.pos.x += p.vel.x
        p.pos.y += p.vel.y

        // Bounce off edges
        if (p.pos.x < 0) {
          p.pos.x = 0
          p.vel.x *= -1
        } else if (p.pos.x > W) {
          p.pos.x = W
          p.vel.x *= -1
        }
        if (p.pos.y < 0) {
          p.pos.y = 0
          p.vel.y *= -1
        } else if (p.pos.y > H) {
          p.pos.y = H
          p.vel.y *= -1
        }

        // Draw particle
        ctx.beginPath()
        ctx.arc(p.pos.x, p.pos.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${colorRGB}, ${PARTICLE_OPACITY})`
        ctx.fill()
      }

      // Draw connection lines
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const dx = a.pos.x - b.pos.x
          const dy = a.pos.y - b.pos.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < CONNECTION_DISTANCE) {
            // Fade line opacity based on distance
            const alpha = LINE_OPACITY * (1 - dist / CONNECTION_DISTANCE)
            ctx.beginPath()
            ctx.moveTo(a.pos.x, a.pos.y)
            ctx.lineTo(b.pos.x, b.pos.y)
            ctx.strokeStyle = `rgba(${colorRGB}, ${alpha})`
            ctx.lineWidth = 1
            ctx.stroke()
          }
        }
      }

      animationId = requestAnimationFrame(tick)
    }

    animationId = requestAnimationFrame(tick)

    // ── Cleanup ──────────────────────────────────────────────────────────────

    return () => {
      cancelAnimationFrame(animationId)
      ro.disconnect()
      canvas.removeEventListener('mousemove', handleMouseMove)
      canvas.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'auto',
        display: 'block',
      }}
    />
  )
}
