import { useEffect, useRef, useState } from 'react'
import {
  motion,
  useInView,
  AnimatePresence,
  type Variants,
} from 'framer-motion'

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

// ─── Animation variants ──────────────────────────────────────────────────────

const sectionVariants: Variants = {
  hidden: { opacity: 0, y: 50 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.9, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
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
    transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
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
}

function CTAButton({ href, variant, children, target, rel }: CTAButtonProps) {
  const [hovered, setHovered] = useState(false)

  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '14px 32px',
    borderRadius: '9999px',
    fontSize: '16px',
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
    transform: hovered ? 'scale(1.02)' : 'scale(1)',
    filter: hovered ? 'brightness(1.1)' : 'brightness(1)',
    boxShadow: hovered ? '0 0 30px rgba(0,229,176,0.4)' : 'none',
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
      // quadratic ease-out
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

// ─── Chip component ──────────────────────────────────────────────────────────

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        display: 'inline-block',
        border: '1px solid rgba(0,229,176,0.3)',
        borderRadius: '20px',
        padding: '4px 14px',
        fontSize: '11px',
        color: COLORS.teal,
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
    <nav style={navStyle} role="navigation" aria-label="Main navigation">
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '20px' }} aria-hidden="true">🏙️</span>
        <span
          style={{
            fontFamily: 'Inter, system-ui, sans-serif',
            fontWeight: 700,
            color: '#ffffff',
            fontSize: '16px',
          }}
        >
          MedCity
        </span>
        <span
          style={{
            fontFamily: 'Inter, system-ui, sans-serif',
            fontWeight: 700,
            color: COLORS.teal,
            fontSize: '16px',
          }}
        >
          Dashboard
        </span>
      </div>

      {/* Links */}
      <div
        style={{ display: 'flex', gap: '32px', alignItems: 'center' }}
        role="list"
      >
        {[
          { label: 'Datos', id: 'datos' },
          { label: 'Comunas', id: 'comunas' },
          { label: 'Tecnología', id: 'tecnologia' },
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

      {/* CTA */}
      <CTAButton href="/dashboard" variant="primary">
        Ver Dashboard →
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
      {/* Background decoration */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          width: '800px',
          height: '800px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,229,176,0.06) 0%, transparent 70%)',
          zIndex: 0,
          pointerEvents: 'none',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        }}
      />

      {/* Content */}
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          textAlign: 'center',
          maxWidth: '900px',
          width: '100%',
        }}
      >
        {/* Eyebrow */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0, ease: [0.16, 1, 0.3, 1] }}
          style={{
            color: COLORS.teal,
            fontSize: '13px',
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            fontFamily: 'Inter, system-ui, sans-serif',
            marginBottom: '24px',
            fontWeight: 500,
          }}
        >
          Hackathon Colombia 5.0 · Medellín 2026
        </motion.p>

        {/* Headline */}
        <div
          style={{
            fontSize: 'clamp(52px, 9vw, 110px)',
            fontWeight: 300,
            letterSpacing: '-0.03em',
            lineHeight: 1.05,
            fontFamily: 'Inter, system-ui, sans-serif',
            marginBottom: '32px',
          }}
          role="heading"
          aria-level={1}
        >
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            style={{ color: '#ffffff' }}
          >
            Datos que
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            <GradientText color="hero">transforman</GradientText>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            style={{ color: '#ffffff' }}
          >
            ciudades.
          </motion.div>
        </div>

        {/* Rotating subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
          style={{
            fontSize: '20px',
            color: COLORS.textPrimary,
            fontFamily: 'Inter, system-ui, sans-serif',
            fontWeight: 300,
            marginBottom: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'wrap',
            gap: '6px',
            lineHeight: 1.5,
          }}
        >
          <span>Inteligencia territorial para</span>
          <span
            style={{
              display: 'inline-block',
              minWidth: '130px',
              textAlign: 'left',
            }}
          >
            <AnimatePresence mode="wait">
              {isVisible && (
                <motion.span
                  key={wordIndex}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.25 }}
                  style={{
                    color: currentWord.color,
                    fontWeight: 600,
                    display: 'inline-block',
                  }}
                >
                  {currentWord.word}
                </motion.span>
              )}
            </AnimatePresence>
          </span>
          <span>en Medellín.</span>
        </motion.p>

        {/* Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.8, ease: [0.16, 1, 0.3, 1] }}
          style={{
            display: 'flex',
            gap: '16px',
            justifyContent: 'center',
            flexWrap: 'wrap',
            marginBottom: '48px',
          }}
        >
          <CTAButton href="/dashboard" variant="primary">
            Explorar el Dashboard →
          </CTAButton>
          <CTAButton
            href="https://github.com/UnTalTroiDev/ProjectCol5.0"
            variant="secondary"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub ↗
          </CTAButton>
        </motion.div>

        {/* Trust badges */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 1, ease: [0.16, 1, 0.3, 1] }}
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
            '📊 3 fuentes MEData',
            '🏘️ 16 comunas',
            '🤖 IA con Claude',
          ].map((badge, i) => (
            <>
              {i > 0 && (
                <span key={`sep-${i}`} aria-hidden="true" style={{ opacity: 0.3 }}>
                  |
                </span>
              )}
              <span key={badge}>{badge}</span>
            </>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

// ─── Problem section ─────────────────────────────────────────────────────────

function StatCard({
  target,
  label,
  sub,
  gradientColor,
}: {
  target: number
  label: string
  sub: string
  gradientColor: 'teal' | 'warm'
}) {
  return (
    <motion.div
      variants={fadeUpChild}
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: `1px solid ${COLORS.border}`,
        borderRadius: '16px',
        padding: '28px',
      }}
    >
      <div
        style={{
          fontSize: 'clamp(60px,8vw,80px)',
          fontWeight: 200,
          lineHeight: 1,
          fontFamily: 'Inter, system-ui, sans-serif',
          marginBottom: '8px',
        }}
      >
        <GradientText color={gradientColor}>
          <CountUpNumber target={target} />
        </GradientText>
      </div>
      <div
        style={{
          color: '#ffffff',
          fontSize: '14px',
          fontWeight: 600,
          fontFamily: 'Inter, system-ui, sans-serif',
          marginBottom: '4px',
        }}
      >
        {label}
      </div>
      <div
        style={{
          color: COLORS.textSecondary,
          fontSize: '12px',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        {sub}
      </div>
    </motion.div>
  )
}

function ProblemSection() {
  return (
    <motion.section
      id="datos"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-80px' }}
      variants={sectionVariants}
      style={{
        padding: '120px 40px',
        maxWidth: '1200px',
        margin: '0 auto',
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '64px',
          alignItems: 'center',
        }}
      >
        {/* Left column */}
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true }}>
          <motion.div variants={fadeUpChild} style={{ marginBottom: '24px' }}>
            <Chip>El Problema</Chip>
          </motion.div>

          <motion.div variants={fadeUpChild}>
            <h2
              style={{
                fontSize: 'clamp(36px,5vw,64px)',
                fontWeight: 300,
                letterSpacing: '-0.02em',
                lineHeight: 1.1,
                fontFamily: 'Inter, system-ui, sans-serif',
                color: '#ffffff',
                margin: 0,
              }}
            >
              Los datos
              <br />
              existen.
              <br />
              Nadie los
              <br />
              <GradientText color="warm">aprovecha.</GradientText>
            </h2>
          </motion.div>

          <motion.p
            variants={fadeUpChild}
            style={{
              color: COLORS.textSecondary,
              fontSize: '18px',
              lineHeight: 1.7,
              marginTop: '24px',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            Medellín produce millones de registros cada día sobre movilidad,
            seguridad y servicios públicos. Pero comunidades y pymes siguen
            tomando decisiones a ciegas.
          </motion.p>
        </motion.div>

        {/* Right column — stat cards */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
        >
          <StatCard
            target={16}
            label="comunas de Medellín"
            sub="con datos abiertos en MEData"
            gradientColor="teal"
          />
          <StatCard
            target={3}
            label="fuentes integradas"
            sub="Movilidad · Seguridad · Inversión"
            gradientColor="teal"
          />
          <StatCard
            target={0}
            label="dashboards ciudadanos existían"
            sub="antes de este proyecto"
            gradientColor="warm"
          />
        </motion.div>
      </div>
    </motion.section>
  )
}

// ─── Solution section ────────────────────────────────────────────────────────

interface FeatureCardProps {
  icon: string
  iconBg: string
  title: string
  body: string
  chipLabel: string
  chipColor: string
  featured?: boolean
}

function FeatureCard({
  icon,
  iconBg,
  title,
  body,
  chipLabel,
  chipColor,
  featured = false,
}: FeatureCardProps) {
  const [hovered, setHovered] = useState(false)

  return (
    <motion.div
      variants={fadeUpChild}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: featured
          ? '1px solid rgba(0,229,176,0.3)'
          : `1px solid ${hovered ? 'rgba(0,229,176,0.25)' : 'rgba(0,229,176,0.1)'}`,
        borderRadius: '16px',
        padding: '28px',
        transform: hovered ? 'translateY(-6px)' : 'translateY(0)',
        transition: 'all 0.25s ease',
        boxShadow: featured ? '0 0 30px rgba(0,229,176,0.08)' : 'none',
      }}
    >
      {/* Icon */}
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          background: iconBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '20px',
          marginBottom: '16px',
        }}
        aria-hidden="true"
      >
        {icon}
      </div>

      {/* Title */}
      <h3
        style={{
          color: '#ffffff',
          fontWeight: 600,
          fontSize: '18px',
          fontFamily: 'Inter, system-ui, sans-serif',
          margin: '0 0 12px',
        }}
      >
        {title}
      </h3>

      {/* Body */}
      <p
        style={{
          color: COLORS.textSecondary,
          fontSize: '15px',
          lineHeight: 1.65,
          fontFamily: 'Inter, system-ui, sans-serif',
          margin: '0 0 20px',
        }}
      >
        {body}
      </p>

      {/* Tech chip */}
      <span
        style={{
          display: 'inline-block',
          background: 'rgba(123,140,255,0.15)',
          color: chipColor,
          borderRadius: '6px',
          padding: '3px 10px',
          fontSize: '11px',
          fontFamily: 'Inter, system-ui, sans-serif',
          fontWeight: 500,
        }}
      >
        {chipLabel}
      </span>
    </motion.div>
  )
}

function SolutionSection() {
  return (
    <motion.section
      id="comunas"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-80px' }}
      variants={sectionVariants}
      style={{ padding: '120px 40px' }}
    >
      {/* Header */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        style={{ textAlign: 'center', marginBottom: '60px' }}
      >
        <motion.div variants={fadeUpChild} style={{ marginBottom: '20px' }}>
          <Chip>La Solución</Chip>
        </motion.div>

        <motion.h2
          variants={fadeUpChild}
          style={{
            fontSize: 'clamp(36px,5vw,64px)',
            fontWeight: 300,
            letterSpacing: '-0.02em',
            lineHeight: 1.1,
            fontFamily: 'Inter, system-ui, sans-serif',
            color: '#ffffff',
            margin: '0 0 20px',
          }}
        >
          Todo el territorio.
          <br />
          Un solo <GradientText color="teal">vistazo.</GradientText>
        </motion.h2>

        <motion.p
          variants={fadeUpChild}
          style={{
            color: COLORS.textSecondary,
            fontSize: '18px',
            maxWidth: '600px',
            margin: '0 auto',
            lineHeight: 1.65,
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          Selecciona cualquier comuna y obtén indicadores de movilidad, seguridad
          e inversión comparados contra el promedio de la ciudad.
        </motion.p>
      </motion.div>

      {/* Feature cards grid */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px',
          maxWidth: '1100px',
          margin: '0 auto',
        }}
      >
        <FeatureCard
          icon="🗺️"
          iconBg="rgba(0,229,176,0.1)"
          title="Mapa Interactivo"
          body="Mapa choropleth SVG de las 16 comunas. El color varía según el indicador seleccionado. Click para filtrar todo el dashboard."
          chipLabel="SVG Nativo"
          chipColor={COLORS.indigo}
        />
        <FeatureCard
          icon="📊"
          iconBg="rgba(123,140,255,0.1)"
          title="Análisis vs Ciudad"
          body="Cada indicador se compara automáticamente contra el promedio de las 16 comunas. KPIs con delta porcentual y dirección de tendencia."
          chipLabel="FastAPI + Pandas"
          chipColor={COLORS.indigo}
        />
        <FeatureCard
          icon="✨"
          iconBg="rgba(0,229,176,0.1)"
          title="Recomendaciones con IA"
          body="Claude analiza los indicadores de cada comuna y genera recomendaciones accionables concretas. No datos crudos — decisiones reales."
          chipLabel="Claude API"
          chipColor={COLORS.teal}
          featured
        />
      </motion.div>
    </motion.section>
  )
}

// ─── Metrics section ─────────────────────────────────────────────────────────

function MetricsSection() {
  const TECH_STACK = [
    'React 19',
    'TypeScript',
    'FastAPI',
    'Python',
    'Pandas',
    'Docker',
    'MEData',
    'Claude API',
  ]

  return (
    <motion.section
      id="tecnologia"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-80px' }}
      variants={sectionVariants}
      style={{ padding: '120px 40px' }}
    >
      {/* Block A */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '64px',
          maxWidth: '1100px',
          margin: '0 auto 80px',
          alignItems: 'center',
        }}
      >
        {/* Left */}
        <div>
          <div
            style={{
              fontSize: 'clamp(72px,12vw,140px)',
              fontWeight: 200,
              lineHeight: 0.9,
              fontFamily: 'Inter, system-ui, sans-serif',
              marginBottom: '12px',
            }}
          >
            <GradientText color="teal">MEData</GradientText>
          </div>
          <p
            style={{
              fontSize: '11px',
              letterSpacing: '0.15em',
              color: COLORS.textSecondary,
              textTransform: 'uppercase',
              fontFamily: 'Inter, system-ui, sans-serif',
              marginBottom: '16px',
            }}
          >
            Portal de Datos Abiertos de Medellín
          </p>
          <p
            style={{
              color: COLORS.textSecondary,
              fontSize: '16px',
              lineHeight: 1.65,
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            Secretarías de Movilidad, Seguridad y Hacienda. Datos reales.
            Actualizados. Gratuitos.
          </p>
        </div>

        {/* Right — quote */}
        <div
          style={{
            borderLeft: `3px solid ${COLORS.teal}`,
            paddingLeft: '24px',
          }}
        >
          <p
            style={{
              fontSize: '20px',
              fontStyle: 'italic',
              color: '#ffffff',
              lineHeight: 1.6,
              fontFamily: 'Inter, system-ui, sans-serif',
              margin: 0,
            }}
          >
            "Cada dato que ignoramos es una decisión que alguien más tomó por
            nosotros."
          </p>
          <p
            style={{
              color: COLORS.textSecondary,
              fontSize: '14px',
              marginTop: '16px',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            — MedCity Dashboard · Hackathon 2026
          </p>
        </div>
      </div>

      {/* Separator */}
      <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)', maxWidth: '1100px', margin: '0 auto 80px' }} />

      {/* Block B — three stats */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          maxWidth: '900px',
          margin: '0 auto 80px',
          textAlign: 'center',
        }}
      >
        {/* Stat 1 */}
        <div
          style={{
            padding: '0 40px 40px',
            borderRight: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <div
            style={{
              fontSize: 'clamp(52px,8vw,80px)',
              fontWeight: 200,
              fontFamily: 'Inter, system-ui, sans-serif',
              lineHeight: 1,
              marginBottom: '8px',
            }}
          >
            <GradientText color="teal">
              <CountUpNumber target={16} suffix=" comunas" />
            </GradientText>
          </div>
          <div
            style={{
              fontSize: '11px',
              letterSpacing: '0.1em',
              color: COLORS.textSecondary,
              textTransform: 'uppercase',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            Mapeadas y analizadas
          </div>
        </div>

        {/* Stat 2 */}
        <div
          style={{
            padding: '0 40px 40px',
            borderRight: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <div
            style={{
              fontSize: 'clamp(52px,8vw,80px)',
              fontWeight: 200,
              fontFamily: 'Inter, system-ui, sans-serif',
              lineHeight: 1,
              marginBottom: '8px',
            }}
          >
            <GradientText color="teal">
              <CountUpNumber target={85} suffix="%" />
            </GradientText>
          </div>
          <div
            style={{
              fontSize: '11px',
              letterSpacing: '0.1em',
              color: COLORS.textSecondary,
              textTransform: 'uppercase',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            Reducción tiempo análisis
          </div>
        </div>

        {/* Stat 3 */}
        <div style={{ padding: '0 40px 40px' }}>
          <div
            style={{
              fontSize: 'clamp(52px,8vw,80px)',
              fontWeight: 200,
              fontFamily: 'Inter, system-ui, sans-serif',
              lineHeight: 1,
              marginBottom: '8px',
            }}
          >
            <GradientText color="warm">+$30M</GradientText>
          </div>
          <div
            style={{
              fontSize: '11px',
              letterSpacing: '0.1em',
              color: COLORS.textSecondary,
              textTransform: 'uppercase',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            Inversión pública trazada
          </div>
        </div>
      </div>

      {/* Separator */}
      <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)', maxWidth: '1100px', margin: '0 auto 80px' }} />

      {/* Block C — tech stack */}
      <div style={{ textAlign: 'center' }}>
        <p
          style={{
            color: COLORS.textSecondary,
            fontSize: '14px',
            fontFamily: 'Inter, system-ui, sans-serif',
            marginBottom: '16px',
          }}
        >
          Construido con
        </p>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '10px',
          }}
        >
          {TECH_STACK.map((tech) => (
            <TechChip key={tech} label={tech} />
          ))}
        </div>
      </div>
    </motion.section>
  )
}

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
  const lines = [
    { text: 'Mientras lo', delay: 0 },
    { text: 'debaten,', delay: 0.15 },
    { text: 'Medellín sigue', delay: 0.3 },
  ]

  return (
    <section
      style={{
        padding: '160px 40px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative circles */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          width: '600px',
          height: '600px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,229,176,0.07), transparent 70%)',
          top: '-150px',
          right: '-150px',
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
          background: 'radial-gradient(circle, rgba(255,179,71,0.05), transparent 70%)',
          bottom: '-150px',
          left: '-150px',
          zIndex: 0,
          pointerEvents: 'none',
        }}
      />

      {/* Content */}
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div
          style={{
            fontSize: 'clamp(44px,7vw,90px)',
            fontWeight: 300,
            lineHeight: 1.1,
            letterSpacing: '-0.03em',
            fontFamily: 'Inter, system-ui, sans-serif',
            marginBottom: '0',
          }}
          role="heading"
          aria-level={2}
        >
          {lines.map(({ text, delay }) => (
            <motion.div
              key={text}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
              style={{ color: '#ffffff' }}
            >
              {text}
            </motion.div>
          ))}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.45, ease: [0.16, 1, 0.3, 1] }}
          >
            <GradientText color="warm">sin datos.</GradientText>
          </motion.div>
        </div>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
          style={{
            color: COLORS.textSecondary,
            fontSize: '18px',
            maxWidth: '500px',
            margin: '24px auto 40px',
            lineHeight: 1.65,
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          El 24 de marzo, este dashboard cambia eso. Explora los indicadores ahora.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.75, ease: [0.16, 1, 0.3, 1] }}
          style={{
            display: 'flex',
            gap: '16px',
            justifyContent: 'center',
            flexWrap: 'wrap',
            marginBottom: '48px',
          }}
        >
          <CTAButton href="/dashboard" variant="primary">
            Explorar Dashboard →
          </CTAButton>
          <CTAButton
            href="https://github.com/UnTalTroiDev/ProjectCol5.0"
            variant="secondary"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub ↗
          </CTAButton>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.9 }}
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '24px',
            flexWrap: 'wrap',
            fontSize: '12px',
            color: 'rgba(240,244,255,0.35)',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          {['⚡ React 19 + FastAPI', '🏙️ Datos MEData', '🤖 Claude AI', '🐳 Docker'].map(
            (badge) => (
              <span key={badge}>{badge}</span>
            )
          )}
        </motion.div>
      </div>
    </section>
  )
}

// ─── Footer ──────────────────────────────────────────────────────────────────

function Footer() {
  const links = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'GitHub', href: 'https://github.com/UnTalTroiDev/ProjectCol5.0' },
    { label: 'MEData', href: 'https://medata.gov.co' },
  ]

  return (
    <footer
      style={{
        padding: '40px 24px',
        borderTop: '1px solid rgba(0,229,176,0.08)',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          color: COLORS.textSecondary,
          fontSize: '14px',
          fontFamily: 'Inter, system-ui, sans-serif',
          marginBottom: '16px',
        }}
      >
        <span aria-hidden="true">🏙️</span> MedCity Dashboard
      </div>

      <nav aria-label="Footer navigation">
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '24px',
            flexWrap: 'wrap',
            marginBottom: '12px',
          }}
        >
          {links.map(({ label, href }) => (
            <FooterLink key={label} href={href} label={label} />
          ))}
        </div>
      </nav>

      <p
        style={{
          fontSize: '12px',
          color: 'rgba(240,244,255,0.25)',
          fontFamily: 'Inter, system-ui, sans-serif',
          margin: 0,
        }}
      >
        Desarrollado para Hackathon Colombia 5.0 · Medellín · Marzo 2026
      </p>
    </footer>
  )
}

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
        <MetricsSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  )
}
