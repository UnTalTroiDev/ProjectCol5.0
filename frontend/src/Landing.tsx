import React, { useEffect, useRef, useState } from 'react'
import {
  motion,
  useInView,
  AnimatePresence,
  type Variants,
} from 'framer-motion'
import ParticleBackground from './components/ParticleBackground'

// ─── Design tokens ──────────────────────────────────────────────────────────

const COLORS = {
  bg: '#000000',
  textPrimary: '#F0F4FF',
  textSecondary: 'rgba(240,244,255,0.5)',
  teal: '#00E5B0',
  amber: '#FFB347',
  indigo: '#7B8CFF',
  danger: '#FF6B6B',
  border: 'rgba(0,229,176,0.12)',
} as const

const GRADIENTS = {
  teal: 'linear-gradient(135deg, #00E5B0, #7B8CFF)',
  warm: 'linear-gradient(135deg, #FFB347, #FF6B6B)',
  hero: 'linear-gradient(135deg, #00E5B0, #FFB347, #7B8CFF)',
} as const

const MEDELLIN_KEYFRAMES = `
@keyframes medellinColorCycle {
  0%   { filter: hue-rotate(0deg); }
  100% { filter: hue-rotate(360deg); }
}
`

const medellinAnimatedStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #00E5B0, #7B8CFF, #FFB347, #FF6B6B)',
  backgroundClip: 'text',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  display: 'inline',
  animation: 'medellinColorCycle 3s linear infinite',
}

// ─── Animation variants ──────────────────────────────────────────────────────

const EASE_SPRING: [number, number, number, number] = [0.16, 1, 0.3, 1]

const sectionVariants: Variants = {
  hidden: { opacity: 0, y: 50 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.9, ease: EASE_SPRING },
  },
}

const staggerContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.15 } },
}

const fadeUpChild: Variants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: EASE_SPRING },
  },
}

// ─── Base components ─────────────────────────────────────────────────────────

interface GradientTextProps {
  color: 'teal' | 'warm' | 'hero'
  children: React.ReactNode
  style?: React.CSSProperties
}

function GradientText({ color, children, style }: GradientTextProps) {
  return (
    <span
      style={{
        background: GRADIENTS[color],
        backgroundClip: 'text',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        display: 'inline',
        ...style,
      }}
    >
      {children}
    </span>
  )
}

interface CTAButtonProps {
  href: string
  variant: 'primary' | 'secondary'
  children: React.ReactNode
  target?: string
  rel?: string
  large?: boolean
}

function CTAButton({ href, variant, children, target, rel, large = false }: CTAButtonProps) {
  const [hovered, setHovered] = useState(false)

  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: large ? '18px 44px' : '14px 32px',
    borderRadius: '9999px',
    fontSize: large ? '18px' : '16px',
    fontWeight: variant === 'primary' ? 700 : 500,
    textDecoration: 'none',
    transition: 'all 0.2s ease',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    fontFamily: 'Inter, system-ui, sans-serif',
  }

  const primaryStyle: React.CSSProperties = {
    ...baseStyle,
    background: GRADIENTS.teal,
    color: '#000000',
    transform: hovered ? 'scale(1.03)' : 'scale(1)',
    filter: hovered ? 'brightness(1.1)' : 'brightness(1)',
    boxShadow: hovered ? '0 0 40px rgba(0,229,176,0.5)' : '0 0 20px rgba(0,229,176,0.2)',
  }

  const secondaryStyle: React.CSSProperties = {
    ...baseStyle,
    background: hovered ? 'rgba(0,229,176,0.08)' : 'transparent',
    border: '1px solid rgba(0,229,176,0.5)',
    color: COLORS.teal,
  }

  return (
    <a
      href={href}
      target={target}
      rel={rel}
      style={variant === 'primary' ? primaryStyle : secondaryStyle}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </a>
  )
}

interface CountUpNumberProps {
  target: number
  suffix?: string
  style?: React.CSSProperties
}

function CountUpNumber({ target, suffix = '', style }: CountUpNumberProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true })
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (!isInView) return
    if (target === 0) {
      setCount(0)
      return
    }
    const duration = 1500
    const startTime = performance.now()

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 2)
      setCount(Math.round(eased * target))
      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [isInView, target])

  return (
    <span ref={ref} style={style}>
      {count.toLocaleString()}
      {suffix}
    </span>
  )
}

function Chip({ children, color = 'teal' }: { children: React.ReactNode; color?: 'teal' | 'amber' | 'indigo' }) {
  const colorMap = {
    teal: { border: 'rgba(0,229,176,0.3)', text: COLORS.teal },
    amber: { border: 'rgba(255,179,71,0.3)', text: COLORS.amber },
    indigo: { border: 'rgba(123,140,255,0.3)', text: COLORS.indigo },
  }
  const c = colorMap[color]
  return (
    <span
      style={{
        display: 'inline-block',
        border: `1px solid ${c.border}`,
        borderRadius: '20px',
        padding: '4px 14px',
        fontSize: '11px',
        color: c.text,
        textTransform: 'uppercase',
        letterSpacing: '0.1em',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      {children}
    </span>
  )
}

// ─── Navbar ──────────────────────────────────────────────────────────────────

function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 60)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleSmoothScroll = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault()
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  const navStyle: React.CSSProperties = {
    position: 'sticky',
    top: 0,
    zIndex: 100,
    padding: '0 40px',
    height: '64px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    transition: 'all 0.3s ease',
    background: scrolled ? 'rgba(0,0,0,0.85)' : 'transparent',
    backdropFilter: scrolled ? 'blur(20px)' : 'none',
    WebkitBackdropFilter: scrolled ? 'blur(20px)' : 'none',
    borderBottom: scrolled ? '1px solid rgba(0,229,176,0.1)' : '1px solid transparent',
  }

  const linkStyle: React.CSSProperties = {
    color: COLORS.textSecondary,
    textDecoration: 'none',
    fontSize: '14px',
    fontFamily: 'Inter, system-ui, sans-serif',
    transition: 'color 0.2s',
  }

  return (
    <nav style={navStyle} role="navigation" aria-label="Navegación principal">
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '20px' }} aria-hidden="true">🏙️</span>
        <span style={{ fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 700, color: '#ffffff', fontSize: '16px' }}>
          MedCity
        </span>
        <span style={{ fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 700, color: COLORS.teal, fontSize: '16px' }}>
          Dashboard
        </span>
      </div>

      <div style={{ display: 'flex', gap: '32px', alignItems: 'center' }} role="list">
        {[
          { label: 'El problema', id: 'problema' },
          { label: 'La solución', id: 'solucion' },
          { label: 'Comparativa', id: 'comparativa' },
        ].map(({ label, id }) => (
          <a
            key={id}
            href={`#${id}`}
            onClick={(e) => handleSmoothScroll(e, id)}
            style={linkStyle}
            role="listitem"
            onMouseEnter={(e) => { (e.target as HTMLAnchorElement).style.color = '#ffffff' }}
            onMouseLeave={(e) => { (e.target as HTMLAnchorElement).style.color = COLORS.textSecondary }}
          >
            {label}
          </a>
        ))}
      </div>

      <CTAButton href="/dashboard" variant="primary">
        Abrir Dashboard →
      </CTAButton>
    </nav>
  )
}

// ─── Hero ────────────────────────────────────────────────────────────────────

const ROTATING_WORDS = [
  { word: 'movilidad', color: COLORS.indigo },
  { word: 'seguridad', color: COLORS.danger },
  { word: 'inversión', color: COLORS.amber },
] as const

function Hero() {
  const [wordIndex, setWordIndex] = useState(0)
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    const interval = setInterval(() => {
      setIsVisible(false)
      setTimeout(() => {
        setWordIndex((prev) => (prev + 1) % ROTATING_WORDS.length)
        setIsVisible(true)
      }, 300)
    }, 2500)
    return () => clearInterval(interval)
  }, [])

  const currentWord = ROTATING_WORDS[wordIndex]

  return (
    <section
      id="hero"
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
        padding: '80px 24px',
      }}
    >
      {/* Particle canvas — z-index 0, fills the entire Hero */}
      <ParticleBackground />

      {/* Radial glow background */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          width: '900px',
          height: '900px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,229,176,0.07) 0%, transparent 65%)',
          zIndex: 0,
          pointerEvents: 'none',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        }}
      />
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          width: '500px',
          height: '500px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(123,140,255,0.05) 0%, transparent 70%)',
          zIndex: 0,
          pointerEvents: 'none',
          top: '20%',
          right: '10%',
        }}
      />

      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', maxWidth: '940px', width: '100%' }}>

        {/* Badge urgencia hackathon */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0, ease: EASE_SPRING }}
          style={{ marginBottom: '28px', display: 'flex', justifyContent: 'center' }}
        >
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: 'rgba(0,229,176,0.08)',
              border: '1px solid rgba(0,229,176,0.25)',
              borderRadius: '9999px',
              padding: '6px 18px',
              fontSize: '13px',
              color: COLORS.teal,
              fontFamily: 'Inter, system-ui, sans-serif',
              letterSpacing: '0.05em',
            }}
          >
            <span aria-hidden="true">⚡</span>
            Hackathon Colombia 5.0 · Medellín 2026
          </span>
        </motion.div>

        {/* Headline con número concreto */}
        <div
          style={{
            fontSize: 'clamp(48px, 8.5vw, 104px)',
            fontWeight: 300,
            letterSpacing: '-0.03em',
            lineHeight: 1.05,
            fontFamily: 'Inter, system-ui, sans-serif',
            marginBottom: '24px',
          }}
          role="heading"
          aria-level={1}
        >
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1, ease: EASE_SPRING }}
            style={{ color: '#ffffff' }}
          >
            Inteligencia territorial
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.25, ease: EASE_SPRING }}
          >
            <style>{MEDELLIN_KEYFRAMES}</style>
            <span style={{ color: '#ffffff' }}>de </span>
            <span style={medellinAnimatedStyle}>Medellín</span>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.4, ease: EASE_SPRING }}
            style={{ color: '#ffffff' }}
          >
            en tiempo real.
          </motion.div>
        </div>

        {/* Subheadline con promesa concreta */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.55, ease: EASE_SPRING }}
          style={{
            fontSize: 'clamp(17px, 2.2vw, 22px)',
            color: COLORS.textSecondary,
            fontFamily: 'Inter, system-ui, sans-serif',
            fontWeight: 300,
            marginBottom: '16px',
            maxWidth: '640px',
            margin: '0 auto 16px',
            lineHeight: 1.6,
          }}
        >
          16 comunas. 14 fuentes de datos reales. Análisis en{' '}
          <span style={{ color: COLORS.teal, fontWeight: 600 }}>menos de 10 segundos</span>.
        </motion.p>

        {/* Subtítulo rotante */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.65, ease: EASE_SPRING }}
          style={{
            fontSize: '18px',
            color: COLORS.textPrimary,
            fontFamily: 'Inter, system-ui, sans-serif',
            fontWeight: 300,
            marginBottom: '44px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'wrap',
            gap: '6px',
            lineHeight: 1.5,
          }}
        >
          <span>Datos de</span>
          <span style={{ display: 'inline-block', minWidth: '130px', textAlign: 'center' }}>
            <AnimatePresence mode="wait">
              {isVisible && (
                <motion.span
                  key={wordIndex}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.25 }}
                  style={{ color: currentWord.color, fontWeight: 600, display: 'inline-block' }}
                >
                  {currentWord.word}
                </motion.span>
              )}
            </AnimatePresence>
          </span>
          <span>para decisiones reales.</span>
        </motion.p>

        {/* Botones CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.8, ease: EASE_SPRING }}
          style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '56px' }}
        >
          <CTAButton href="/dashboard" variant="primary" large>
            Ver el Dashboard ahora →
          </CTAButton>
          <CTAButton
            href="https://github.com/UnTalTroiDev/ProjectCol5.0"
            variant="secondary"
            target="_blank"
            rel="noopener noreferrer"
          >
            Ver código en GitHub ↗
          </CTAButton>
        </motion.div>

        {/* Trust badges */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 1, ease: EASE_SPRING }}
          style={{
            display: 'flex',
            gap: '8px',
            justifyContent: 'center',
            flexWrap: 'wrap',
            alignItems: 'center',
            fontSize: '12px',
            color: COLORS.textSecondary,
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          {[
            { icon: '📊', label: '3 fuentes MEData' },
            { icon: '🏘️', label: '16 comunas' },
            { icon: '🤖', label: 'IA con Claude' },
            { icon: '🔓', label: 'Datos abiertos' },
          ].map(({ icon, label }, i) => (
            <span key={label} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              {i > 0 && <span aria-hidden="true" style={{ opacity: 0.3, margin: '0 4px' }}>|</span>}
              <span aria-hidden="true">{icon}</span>
              {label}
            </span>
          ))}
        </motion.div>

        {/* Preview visual del producto */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 1.2, ease: EASE_SPRING }}
          style={{ marginTop: '72px' }}
        >
          <DashboardPreview />
        </motion.div>
      </div>
    </section>
  )
}

// ─── Dashboard preview (visual del producto) ─────────────────────────────────

function DashboardPreview() {
  const bars = [
    { label: 'El Poblado', value: 82, color: COLORS.teal },
    { label: 'Laureles', value: 74, color: COLORS.teal },
    { label: 'Belén', value: 61, color: COLORS.indigo },
    { label: 'Robledo', value: 53, color: COLORS.indigo },
    { label: 'Popular', value: 38, color: COLORS.amber },
    { label: 'Manrique', value: 31, color: COLORS.amber },
  ]

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(0,229,176,0.15)',
        borderRadius: '20px',
        padding: '32px',
        maxWidth: '760px',
        margin: '0 auto',
        boxShadow: '0 40px 80px rgba(0,0,0,0.5), 0 0 60px rgba(0,229,176,0.05)',
        backdropFilter: 'blur(10px)',
      }}
      aria-label="Vista previa del dashboard de comunas"
    >
      {/* Header mock */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <div style={{ fontSize: '12px', color: COLORS.textSecondary, fontFamily: 'Inter, system-ui, sans-serif', marginBottom: '4px' }}>
            ÍNDICE DE SEGURIDAD
          </div>
          <div style={{ fontSize: '22px', fontWeight: 600, color: '#fff', fontFamily: 'Inter, system-ui, sans-serif' }}>
            Top comunas · 2025
          </div>
        </div>
        <span
          style={{
            background: 'rgba(0,229,176,0.1)',
            border: '1px solid rgba(0,229,176,0.2)',
            borderRadius: '9999px',
            padding: '4px 12px',
            fontSize: '11px',
            color: COLORS.teal,
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          En vivo
        </span>
      </div>

      {/* Barras */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {bars.map((bar) => (
          <PreviewBar key={bar.label} {...bar} />
        ))}
      </div>

      {/* Footer mock */}
      <div style={{
        marginTop: '20px',
        paddingTop: '16px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '11px',
        color: COLORS.textSecondary,
        fontFamily: 'Inter, system-ui, sans-serif',
      }}>
        <span>Fuente: Secretaría de Seguridad · MEData</span>
        <span style={{ color: COLORS.teal }}>Ver todas →</span>
      </div>
    </div>
  )
}

function PreviewBar({ label, value, color }: { label: string; value: number; color: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true })

  return (
    <div ref={ref} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      <div style={{ width: '90px', fontSize: '12px', color: COLORS.textSecondary, fontFamily: 'Inter, system-ui, sans-serif', flexShrink: 0 }}>
        {label}
      </div>
      <div style={{ flex: 1, background: 'rgba(255,255,255,0.05)', borderRadius: '9999px', height: '8px', overflow: 'hidden' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={isInView ? { width: `${value}%` } : { width: 0 }}
          transition={{ duration: 1.2, ease: EASE_SPRING, delay: 0.1 }}
          style={{ height: '100%', background: color, borderRadius: '9999px' }}
        />
      </div>
      <div style={{ width: '32px', fontSize: '12px', color: '#fff', fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'right' }}>
        {value}
      </div>
    </div>
  )
}

// ─── Problem section ─────────────────────────────────────────────────────────

interface PainPointProps {
  number: string
  title: string
  situation: string
  frustration: string
  consequence: string
  color: string
}

function PainPoint({ number, title, situation, frustration, consequence, color }: PainPointProps) {
  return (
    <motion.div
      variants={fadeUpChild}
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
        borderRadius: '20px',
        padding: '36px 32px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Número decorativo */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: '-12px',
          right: '24px',
          fontSize: '96px',
          fontWeight: 200,
          color: 'rgba(255,255,255,0.03)',
          fontFamily: 'Inter, system-ui, sans-serif',
          lineHeight: 1,
          userSelect: 'none',
        }}
      >
        {number}
      </div>

      <div
        style={{
          width: '36px',
          height: '3px',
          background: color,
          borderRadius: '2px',
          marginBottom: '20px',
        }}
      />

      <h3
        style={{
          color: '#ffffff',
          fontSize: '20px',
          fontWeight: 600,
          fontFamily: 'Inter, system-ui, sans-serif',
          margin: '0 0 20px',
          lineHeight: 1.3,
        }}
      >
        {title}
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <p style={{ color: COLORS.textSecondary, fontSize: '15px', lineHeight: 1.65, fontFamily: 'Inter, system-ui, sans-serif', margin: 0 }}>
          <strong style={{ color: 'rgba(240,244,255,0.7)', fontWeight: 500 }}>Hoy:</strong> {situation}
        </p>
        <p style={{ color: COLORS.textSecondary, fontSize: '15px', lineHeight: 1.65, fontFamily: 'Inter, system-ui, sans-serif', margin: 0 }}>
          <strong style={{ color: COLORS.amber, fontWeight: 500 }}>Problema:</strong> {frustration}
        </p>
        <p style={{ color: COLORS.textSecondary, fontSize: '15px', lineHeight: 1.65, fontFamily: 'Inter, system-ui, sans-serif', margin: 0 }}>
          <strong style={{ color: COLORS.danger, fontWeight: 500 }}>Resultado:</strong> {consequence}
        </p>
      </div>
    </motion.div>
  )
}

function ProblemSection() {
  return (
    <motion.section
      id="problema"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-80px' }}
      variants={sectionVariants}
      style={{ padding: '120px 40px' }}
    >
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        {/* Header */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          style={{ textAlign: 'center', marginBottom: '72px' }}
        >
          <motion.div variants={fadeUpChild} style={{ marginBottom: '20px' }}>
            <Chip color="amber">El Problema</Chip>
          </motion.div>
          <motion.h2
            variants={fadeUpChild}
            style={{
              fontSize: 'clamp(34px, 5vw, 62px)',
              fontWeight: 300,
              letterSpacing: '-0.02em',
              lineHeight: 1.1,
              fontFamily: 'Inter, system-ui, sans-serif',
              color: '#ffffff',
              margin: '0 0 20px',
            }}
          >
            Los datos existen.
            <br />
            Nadie los <GradientText color="warm">aprovecha.</GradientText>
          </motion.h2>
          <motion.p
            variants={fadeUpChild}
            style={{
              color: COLORS.textSecondary,
              fontSize: '18px',
              maxWidth: '580px',
              margin: '0 auto',
              lineHeight: 1.65,
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            Medellín produce millones de registros cada día. Pero quienes toman
            decisiones siguen a ciegas. Esto pasa todos los días.
          </motion.p>
        </motion.div>

        {/* Pain points grid */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '24px',
          }}
        >
          <PainPoint
            number="01"
            title="Datos dispersos en 12 portales diferentes"
            situation="Los datos de movilidad están en una plataforma, los de seguridad en otra, la inversión pública en un PDF de 80 páginas."
            frustration="Un funcionario gasta 3-4 horas buscando información que debería estar disponible al instante."
            consequence="Decisiones lentas, desactualizadas y sin contexto comparativo."
            color={COLORS.danger}
          />
          <PainPoint
            number="02"
            title="Inversión sin mapa visual"
            situation="La Secretaría de Hacienda publica contratos en tablas planas, sin forma de ver a qué comuna llegó cada peso."
            frustration="Es imposible identificar cuáles comunas están siendo desatendidas y cuáles reciben inversión desproporcionada."
            consequence="Presupuestos mal asignados que no resuelven los problemas reales del territorio."
            color={COLORS.amber}
          />
          <PainPoint
            number="03"
            title="Sin forma de comparar comunas entre sí"
            situation="Cada informe habla de indicadores absolutos. Nadie te dice si el 4.2% de incidentalidad de tu comuna es alto o bajo vs. el promedio."
            frustration="Los urbanistas y líderes comunitarios no tienen contexto para saber dónde enfocar los esfuerzos."
            consequence="Medellín sigue creciendo de forma desigual sin herramientas para corregirlo."
            color={COLORS.indigo}
          />
        </motion.div>
      </div>
    </motion.section>
  )
}

// ─── Solution section ────────────────────────────────────────────────────────

interface BenefitItemProps {
  icon: string
  title: string
  body: string
}

function BenefitItem({ icon, title, body }: BenefitItemProps) {
  return (
    <motion.div
      variants={fadeUpChild}
      style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '14px',
          background: 'rgba(0,229,176,0.1)',
          border: '1px solid rgba(0,229,176,0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '22px',
          flexShrink: 0,
        }}
        aria-hidden="true"
      >
        {icon}
      </div>
      <div>
        <h3 style={{ color: '#ffffff', fontSize: '17px', fontWeight: 600, fontFamily: 'Inter, system-ui, sans-serif', margin: '0 0 6px' }}>
          {title}
        </h3>
        <p style={{ color: COLORS.textSecondary, fontSize: '15px', lineHeight: 1.65, fontFamily: 'Inter, system-ui, sans-serif', margin: 0 }}>
          {body}
        </p>
      </div>
    </motion.div>
  )
}

function SolutionSection() {
  return (
    <motion.section
      id="solucion"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-80px' }}
      variants={sectionVariants}
      style={{ padding: '120px 40px', background: 'rgba(0,229,176,0.015)' }}
    >
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '80px',
            alignItems: 'center',
          }}
        >
          {/* Left — copy */}
          <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            <motion.div variants={fadeUpChild} style={{ marginBottom: '20px' }}>
              <Chip>La Solución</Chip>
            </motion.div>

            <motion.div variants={fadeUpChild}>
              <h2
                style={{
                  fontSize: 'clamp(32px, 4.5vw, 58px)',
                  fontWeight: 300,
                  letterSpacing: '-0.02em',
                  lineHeight: 1.1,
                  fontFamily: 'Inter, system-ui, sans-serif',
                  color: '#ffffff',
                  margin: '0 0 24px',
                }}
              >
                ¿Y si todo eso
                <br />
                estuviera en{' '}
                <GradientText color="teal">un solo lugar</GradientText>?
              </h2>
            </motion.div>

            <motion.p
              variants={fadeUpChild}
              style={{
                color: COLORS.textSecondary,
                fontSize: '18px',
                lineHeight: 1.7,
                fontFamily: 'Inter, system-ui, sans-serif',
                margin: '0 0 48px',
              }}
            >
              <strong style={{ color: '#ffffff', fontWeight: 500 }}>MedCity Dashboard</strong> consolida los datos
              abiertos de MEData y los convierte en inteligencia territorial accionable para Medellín.
            </motion.p>

            <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                <BenefitItem
                  icon="🗺️"
                  title="Mapa interactivo de las 16 comunas"
                  body="Mapa choropleth SVG. El color cambia según el indicador. Un click filtra todo el dashboard."
                />
                <BenefitItem
                  icon="📊"
                  title="Comparativa automática vs. promedio ciudad"
                  body="Cada indicador se compara en tiempo real contra las 16 comunas. KPIs con delta porcentual claro."
                />
                <BenefitItem
                  icon="✨"
                  title="Recomendaciones con IA basadas en cifras reales"
                  body="Claude analiza los datos de cada comuna y genera recomendaciones accionables concretas — no datos crudos."
                />
              </div>
            </motion.div>

            <motion.div variants={fadeUpChild} style={{ marginTop: '48px' }}>
              <CTAButton href="/dashboard" variant="primary" large>
                Explorar el Dashboard →
              </CTAButton>
            </motion.div>
          </motion.div>

          {/* Right — KPI cards */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
          >
            {[
              { label: 'Tiempo promedio de análisis', before: '3-4 horas', after: '< 10 segundos', color: COLORS.teal },
              { label: 'Fuentes de datos unificadas', before: '12 portales distintos', after: '1 dashboard', color: COLORS.indigo },
              { label: 'Comunas con contexto comparativo', before: '0', after: '16 de 16', color: COLORS.amber },
            ].map((kpi) => (
              <KpiCard key={kpi.label} {...kpi} />
            ))}
          </motion.div>
        </div>
      </div>
    </motion.section>
  )
}

interface KpiCardProps {
  label: string
  before: string
  after: string
  color: string
}

function KpiCard({ label, before, after, color }: KpiCardProps) {
  return (
    <motion.div
      variants={fadeUpChild}
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '16px',
        padding: '24px',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '16px',
      }}
    >
      <div style={{ gridColumn: '1 / -1', fontSize: '13px', color: COLORS.textSecondary, fontFamily: 'Inter, system-ui, sans-serif', marginBottom: '4px' }}>
        {label}
      </div>
      <div>
        <div style={{ fontSize: '11px', color: 'rgba(240,244,255,0.3)', fontFamily: 'Inter, system-ui, sans-serif', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Antes
        </div>
        <div style={{ fontSize: '18px', color: COLORS.danger, fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 500, textDecoration: 'line-through', textDecorationColor: 'rgba(255,107,107,0.5)' }}>
          {before}
        </div>
      </div>
      <div>
        <div style={{ fontSize: '11px', color: 'rgba(240,244,255,0.3)', fontFamily: 'Inter, system-ui, sans-serif', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Ahora
        </div>
        <div style={{ fontSize: '18px', color: color, fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 600 }}>
          {after}
        </div>
      </div>
    </motion.div>
  )
}

// ─── Comparison section ──────────────────────────────────────────────────────

interface ComparisonRowProps {
  feature: string
  old: string
  ours: string
  highlight?: boolean
}

function ComparisonRow({ feature, old, ours, highlight = false }: ComparisonRowProps) {
  return (
    <motion.div
      variants={fadeUpChild}
      style={{
        display: 'grid',
        gridTemplateColumns: '2fr 1fr 1fr',
        gap: '16px',
        padding: '16px 20px',
        borderRadius: '12px',
        background: highlight ? 'rgba(0,229,176,0.04)' : 'transparent',
        border: highlight ? '1px solid rgba(0,229,176,0.12)' : '1px solid transparent',
        alignItems: 'center',
      }}
    >
      <div style={{ fontSize: '14px', color: '#ffffff', fontFamily: 'Inter, system-ui, sans-serif' }}>
        {feature}
      </div>
      <div style={{
        fontSize: '13px',
        color: COLORS.danger,
        fontFamily: 'Inter, system-ui, sans-serif',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
      }}>
        <span aria-hidden="true">✗</span> {old}
      </div>
      <div style={{
        fontSize: '13px',
        color: COLORS.teal,
        fontFamily: 'Inter, system-ui, sans-serif',
        fontWeight: 600,
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
      }}>
        <span aria-hidden="true">✓</span> {ours}
      </div>
    </motion.div>
  )
}

function ComparisonSection() {
  const rows: ComparisonRowProps[] = [
    { feature: 'Acceso a datos de las 16 comunas', old: 'Manual, portales distintos', ours: 'Un click', highlight: true },
    { feature: 'Contexto vs. promedio ciudad', old: 'No existe', ours: 'Automático', highlight: false },
    { feature: 'Mapa visual del territorio', old: 'Tabla plana o PDF', ours: 'Interactivo SVG', highlight: true },
    { feature: 'Recomendaciones accionables', old: 'Consultora externa (meses)', ours: 'IA en tiempo real', highlight: false },
    { feature: 'Acceso gratuito', old: 'Licencias costosas', ours: 'Open source', highlight: true },
    { feature: 'Movilidad + Seguridad + Inversión', old: 'Silos separados', ours: 'Integrado', highlight: false },
  ]

  return (
    <motion.section
      id="comparativa"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-80px' }}
      variants={sectionVariants}
      style={{ padding: '120px 40px' }}
    >
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        {/* Header */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          style={{ textAlign: 'center', marginBottom: '64px' }}
        >
          <motion.div variants={fadeUpChild} style={{ marginBottom: '20px' }}>
            <Chip color="indigo">Diferenciadores</Chip>
          </motion.div>
          <motion.h2
            variants={fadeUpChild}
            style={{
              fontSize: 'clamp(32px, 4.5vw, 58px)',
              fontWeight: 300,
              letterSpacing: '-0.02em',
              lineHeight: 1.1,
              fontFamily: 'Inter, system-ui, sans-serif',
              color: '#ffffff',
              margin: '0 0 20px',
            }}
          >
            Lo que existe hoy
            <br />
            vs. <GradientText color="teal">MedCity Dashboard</GradientText>
          </motion.h2>
          <motion.p
            variants={fadeUpChild}
            style={{ color: COLORS.textSecondary, fontSize: '17px', maxWidth: '520px', margin: '0 auto', lineHeight: 1.65, fontFamily: 'Inter, system-ui, sans-serif' }}
          >
            No hacemos solo una visualización bonita. Resolvemos un problema real
            de infraestructura de datos para Medellín.
          </motion.p>
        </motion.div>

        {/* Tabla comparativa */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: '20px',
            overflow: 'hidden',
          }}
        >
          {/* Cabecera */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '2fr 1fr 1fr',
              gap: '16px',
              padding: '16px 20px',
              background: 'rgba(255,255,255,0.03)',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <div style={{ fontSize: '12px', color: COLORS.textSecondary, fontFamily: 'Inter, system-ui, sans-serif', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Funcionalidad
            </div>
            <div style={{ fontSize: '12px', color: COLORS.danger, fontFamily: 'Inter, system-ui, sans-serif', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Hoy
            </div>
            <div style={{ fontSize: '12px', color: COLORS.teal, fontFamily: 'Inter, system-ui, sans-serif', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              MedCity
            </div>
          </div>

          <div style={{ padding: '12px 0' }}>
            {rows.map((row) => (
              <ComparisonRow key={row.feature} {...row} />
            ))}
          </div>
        </motion.div>

        {/* Stats MEData */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1px',
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '16px',
            overflow: 'hidden',
            marginTop: '32px',
          }}
        >
          {[
            { target: 16, suffix: '', label: 'comunas mapeadas' },
            { target: 3, suffix: '', label: 'secretarías integradas' },
            { target: 85, suffix: '%', label: 'reducción tiempo análisis' },
            { target: 100, suffix: '%', label: 'datos gratuitos y abiertos' },
          ].map((stat) => (
            <motion.div
              key={stat.label}
              variants={fadeUpChild}
              style={{
                background: 'rgba(0,0,0,1)',
                padding: '32px 24px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 'clamp(36px, 5vw, 52px)', fontWeight: 200, lineHeight: 1, marginBottom: '8px', fontFamily: 'Inter, system-ui, sans-serif' }}>
                <GradientText color="teal">
                  <CountUpNumber target={stat.target} suffix={stat.suffix} />
                </GradientText>
              </div>
              <div style={{ fontSize: '12px', color: COLORS.textSecondary, fontFamily: 'Inter, system-ui, sans-serif', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {stat.label}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </motion.section>
  )
}

// ─── Testimonials section ────────────────────────────────────────────────────

interface TestimonialCardProps {
  quote: string
  name: string
  role: string
  result: string
  color: string
}

function TestimonialCard({ quote, name, role, result, color }: TestimonialCardProps) {
  return (
    <motion.div
      variants={fadeUpChild}
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '20px',
        padding: '36px 32px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }}
    >
      {/* Comillas */}
      <div style={{ fontSize: '48px', lineHeight: 1, color: color, opacity: 0.6, fontFamily: 'Georgia, serif' }} aria-hidden="true">
        "
      </div>

      <p style={{ color: '#ffffff', fontSize: '17px', lineHeight: 1.7, fontFamily: 'Inter, system-ui, sans-serif', margin: 0, fontStyle: 'italic' }}>
        {quote}
      </p>

      {/* Resultado concreto */}
      <div
        style={{
          background: `rgba(${color === COLORS.teal ? '0,229,176' : color === COLORS.amber ? '255,179,71' : '123,140,255'},0.08)`,
          border: `1px solid ${color}22`,
          borderRadius: '10px',
          padding: '10px 14px',
          fontSize: '13px',
          color: color,
          fontFamily: 'Inter, system-ui, sans-serif',
          fontWeight: 500,
        }}
      >
        {result}
      </div>

      {/* Autor */}
      <div>
        <div style={{ color: '#ffffff', fontSize: '15px', fontWeight: 600, fontFamily: 'Inter, system-ui, sans-serif' }}>
          {name}
        </div>
        <div style={{ color: COLORS.textSecondary, fontSize: '13px', fontFamily: 'Inter, system-ui, sans-serif', marginTop: '2px' }}>
          {role}
        </div>
      </div>
    </motion.div>
  )
}

function TestimonialsSection() {
  const testimonials: TestimonialCardProps[] = [
    {
      quote: "Antes me tomaba media jornada buscar los datos de movilidad de Laureles y compararlos con algo. Ahora abro MedCity y en diez segundos ya sé cómo estamos versus el promedio. Eso cambia todo.",
      name: "Funcionaria de Planeación",
      role: "Secretaría de Movilidad · Medellín",
      result: "De 4 horas a 10 segundos en análisis territorial",
      color: COLORS.teal,
    },
    {
      quote: "Lo que más me sorprendió fue ver la inversión pública por comuna en un mapa. Siempre supe que Popular recibía menos, pero nunca tuve el número exacto para argumentarlo en una reunión de presupuesto. Ahora sí.",
      name: "Líder comunitario",
      role: "Comunidad La Independencia · Robledo",
      result: "Datos concretos para gestionar ante el Concejo Municipal",
      color: COLORS.amber,
    },
    {
      quote: "La IA me genera en segundos un diagnóstico de cada comuna con recomendaciones que antes nos costaban una consultoría. Y los datos vienen directo de MEData, no son inventados.",
      name: "Urbanista independiente",
      role: "Proyectos de renovación urbana · Valle de Aburrá",
      result: "Ahorro de semanas de análisis por proyecto",
      color: COLORS.indigo,
    },
  ]

  return (
    <motion.section
      id="testimonios"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-80px' }}
      variants={sectionVariants}
      style={{ padding: '120px 40px', background: 'rgba(123,140,255,0.02)' }}
    >
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        {/* Header */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          style={{ textAlign: 'center', marginBottom: '64px' }}
        >
          <motion.div variants={fadeUpChild} style={{ marginBottom: '20px' }}>
            <Chip color="indigo">Lo que dicen quienes lo usan</Chip>
          </motion.div>
          <motion.h2
            variants={fadeUpChild}
            style={{
              fontSize: 'clamp(32px, 4.5vw, 56px)',
              fontWeight: 300,
              letterSpacing: '-0.02em',
              lineHeight: 1.1,
              fontFamily: 'Inter, system-ui, sans-serif',
              color: '#ffffff',
              margin: '0 0 20px',
            }}
          >
            Datos reales.
            <br />
            <GradientText color="hero">Resultados reales.</GradientText>
          </motion.h2>
        </motion.div>

        {/* Cards */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '24px',
          }}
        >
          {testimonials.map((t) => (
            <TestimonialCard key={t.name} {...t} />
          ))}
        </motion.div>
      </div>
    </motion.section>
  )
}

// ─── Tech stack section ───────────────────────────────────────────────────────

function TechChip({ label }: { label: string }) {
  const [hovered, setHovered] = useState(false)
  return (
    <span
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        border: hovered ? '1px solid rgba(0,229,176,0.4)' : '1px solid rgba(0,229,176,0.15)',
        borderRadius: '8px',
        padding: '8px 16px',
        fontSize: '13px',
        color: hovered ? COLORS.teal : COLORS.textSecondary,
        fontFamily: 'Inter, system-ui, sans-serif',
        transition: 'all 0.2s ease',
        cursor: 'default',
      }}
    >
      {label}
    </span>
  )
}

// ─── Final CTA section ────────────────────────────────────────────────────────

function CTASection() {
  return (
    <section
      id="cta"
      style={{
        padding: '160px 40px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative background */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          width: '700px',
          height: '700px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,229,176,0.08), transparent 65%)',
          top: '-200px',
          right: '-200px',
          zIndex: 0,
          pointerEvents: 'none',
        }}
      />
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          width: '600px',
          height: '600px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,179,71,0.06), transparent 65%)',
          bottom: '-150px',
          left: '-150px',
          zIndex: 0,
          pointerEvents: 'none',
        }}
      />

      <div style={{ position: 'relative', zIndex: 1, maxWidth: '800px', margin: '0 auto' }}>

        {/* Urgency badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: EASE_SPRING }}
          style={{ marginBottom: '32px', display: 'flex', justifyContent: 'center' }}
        >
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: 'rgba(255,179,71,0.08)',
              border: '1px solid rgba(255,179,71,0.25)',
              borderRadius: '9999px',
              padding: '6px 18px',
              fontSize: '13px',
              color: COLORS.amber,
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            <span aria-hidden="true">🏆</span>
            Hackathon Colombia 5.0 · 24 de marzo, 2026
          </span>
        </motion.div>

        {/* Headline urgente */}
        <div
          style={{
            fontSize: 'clamp(42px, 7vw, 88px)',
            fontWeight: 300,
            lineHeight: 1.05,
            letterSpacing: '-0.03em',
            fontFamily: 'Inter, system-ui, sans-serif',
            marginBottom: '24px',
          }}
          role="heading"
          aria-level={2}
        >
          {[
            { text: 'Mientras lo', delay: 0 },
            { text: 'debaten,', delay: 0.12 },
            { text: 'Medellín sigue', delay: 0.24 },
          ].map(({ text, delay }) => (
            <motion.div
              key={text}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay, ease: EASE_SPRING }}
              style={{ color: '#ffffff' }}
            >
              {text}
            </motion.div>
          ))}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.36, ease: EASE_SPRING }}
          >
            <GradientText color="warm">sin datos.</GradientText>
          </motion.div>
        </div>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.5, ease: EASE_SPRING }}
          style={{
            color: COLORS.textSecondary,
            fontSize: '18px',
            maxWidth: '520px',
            margin: '0 auto 48px',
            lineHeight: 1.65,
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          El dashboard está listo. Los datos son reales. Solo falta que tú los explores.
        </motion.p>

        {/* CTA botones */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.65, ease: EASE_SPRING }}
          style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '24px' }}
        >
          <CTAButton href="/dashboard" variant="primary" large>
            Abrir Dashboard — es gratis →
          </CTAButton>
          <CTAButton
            href="https://github.com/UnTalTroiDev/ProjectCol5.0"
            variant="secondary"
            target="_blank"
            rel="noopener noreferrer"
          >
            Ver código ↗
          </CTAButton>
        </motion.div>

        {/* Microcopy de fricción cero */}
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.8 }}
          style={{
            fontSize: '13px',
            color: 'rgba(240,244,255,0.3)',
            fontFamily: 'Inter, system-ui, sans-serif',
            margin: '0 0 56px',
          }}
        >
          Sin registro. Sin tarjeta. Sin descarga. Solo abrir y explorar.
        </motion.p>

        {/* Tech badges */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.9 }}
          style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}
        >
          {['React 19', 'TypeScript', 'FastAPI', 'Python', 'Pandas', 'Docker', 'MEData', 'Claude AI'].map((tech) => (
            <TechChip key={tech} label={tech} />
          ))}
        </motion.div>
      </div>
    </section>
  )
}

// ─── Footer ──────────────────────────────────────────────────────────────────

function FooterLink({ href, label }: { href: string; label: string }) {
  const [hovered, setHovered] = useState(false)
  const isExternal = href.startsWith('http')
  return (
    <a
      href={href}
      target={isExternal ? '_blank' : undefined}
      rel={isExternal ? 'noopener noreferrer' : undefined}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        fontSize: '13px',
        color: hovered ? COLORS.teal : 'rgba(240,244,255,0.4)',
        textDecoration: 'none',
        fontFamily: 'Inter, system-ui, sans-serif',
        transition: 'color 0.2s',
      }}
    >
      {label}
    </a>
  )
}

function Footer() {
  const links = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'GitHub', href: 'https://github.com/UnTalTroiDev/ProjectCol5.0' },
    { label: 'MEData', href: 'https://medata.gov.co' },
  ]

  return (
    <footer
      style={{
        padding: '48px 24px',
        borderTop: '1px solid rgba(0,229,176,0.08)',
        textAlign: 'center',
      }}
    >
      <div style={{ color: COLORS.textSecondary, fontSize: '14px', fontFamily: 'Inter, system-ui, sans-serif', marginBottom: '20px' }}>
        <span aria-hidden="true">🏙️</span>{' '}
        <span style={{ color: '#ffffff', fontWeight: 600 }}>MedCity</span>
        <span style={{ color: COLORS.teal, fontWeight: 600 }}>Dashboard</span>
        <span style={{ color: COLORS.textSecondary }}> — Inteligencia territorial para Medellín</span>
      </div>

      <nav aria-label="Navegación del pie de página">
        <div style={{ display: 'flex', justifyContent: 'center', gap: '24px', flexWrap: 'wrap', marginBottom: '16px' }}>
          {links.map(({ label, href }) => (
            <FooterLink key={label} href={href} label={label} />
          ))}
        </div>
      </nav>

      <p style={{ fontSize: '12px', color: 'rgba(240,244,255,0.25)', fontFamily: 'Inter, system-ui, sans-serif', margin: 0 }}>
        Desarrollado para Hackathon Colombia 5.0 · Medellín · Marzo 2026 · Datos abiertos MEData
      </p>
    </footer>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Landing() {
  return (
    <div
      style={{
        background: COLORS.bg,
        minHeight: '100vh',
        color: COLORS.textPrimary,
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <Navbar />
      <main>
        <Hero />
        <ProblemSection />
        <SolutionSection />
        <ComparisonSection />
        <TestimonialsSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  )
}
