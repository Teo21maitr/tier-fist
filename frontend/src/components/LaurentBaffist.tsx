/**
 * Laurent Baffist — mascotte officielle de Tier Fist (spec §7).
 *
 * Petit robot à la silhouette sympathique, dont les mains évoquent des gants
 * médicaux. Sarcastique et taquin, jamais insultant ni agressif.
 */

interface LaurentProps {
  className?: string
  /** Variante d'expression : neutre, content, ou sourcil levé (sceptique). */
  mood?: 'neutral' | 'happy' | 'smug'
  title?: string
}

export function LaurentBaffist({ className = 'h-24 w-24', mood = 'smug', title }: LaurentProps) {
  return (
    <svg
      viewBox="0 0 120 150"
      className={className}
      role="img"
      aria-label={title ?? 'Laurent Baffist, la mascotte de Tier Fist'}
      fill="none"
    >
      <title>{title ?? 'Laurent Baffist'}</title>

      {/* Antenne */}
      <line x1="60" y1="20" x2="60" y2="9" stroke="#9370ff" strokeWidth="3.5" strokeLinecap="round" />
      <circle cx="60" cy="6" r="4.5" fill="#c4b5fd" />

      {/* Bras + mains-gants */}
      <GloveHand x={16} y={92} flip />
      <GloveHand x={104} y={92} />
      <path
        d="M34 88 C24 88 20 92 18 96"
        stroke="#5a1fbb"
        strokeWidth="7"
        strokeLinecap="round"
      />
      <path
        d="M86 88 C96 88 100 92 102 96"
        stroke="#5a1fbb"
        strokeWidth="7"
        strokeLinecap="round"
      />

      {/* Corps */}
      <rect x="34" y="80" width="52" height="46" rx="16" fill="#6a29e0" />
      <rect x="45" y="92" width="30" height="20" rx="7" fill="#4a1c97" />
      <circle cx="60" cy="102" r="4.5" fill="#c4b5fd" />

      {/* Pieds */}
      <rect x="40" y="126" width="16" height="9" rx="4.5" fill="#4a1c97" />
      <rect x="64" y="126" width="16" height="9" rx="4.5" fill="#4a1c97" />

      {/* Tête */}
      <rect x="24" y="20" width="72" height="58" rx="20" fill="#7a45f5" />
      <rect x="32" y="30" width="56" height="36" rx="14" fill="#1e1b3a" />

      {/* Yeux */}
      {mood === 'happy' ? (
        <>
          <path d="M42 48 Q48 41 54 48" stroke="#8df0d0" strokeWidth="4" strokeLinecap="round" />
          <path d="M66 48 Q72 41 78 48" stroke="#8df0d0" strokeWidth="4" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="48" cy="46" r="5.5" fill="#8df0d0" />
          <circle cx="72" cy="46" r="5.5" fill="#8df0d0" />
        </>
      )}

      {/* Sourcil levé : le sarcasme, en une ligne */}
      {mood === 'smug' && (
        <path d="M64 35 L80 32" stroke="#8df0d0" strokeWidth="3" strokeLinecap="round" />
      )}

      {/* Sourire en coin */}
      <path
        d={mood === 'happy' ? 'M48 57 Q60 64 72 57' : 'M48 58 Q58 62 70 56'}
        stroke="#8df0d0"
        strokeWidth="3"
        strokeLinecap="round"
      />

      {/* Oreillettes */}
      <rect x="17" y="38" width="8" height="20" rx="4" fill="#5a1fbb" />
      <rect x="95" y="38" width="8" height="20" rx="4" fill="#5a1fbb" />
    </svg>
  )
}

/** Main en forme de gant médical : paume arrondie et doigts saillants. */
function GloveHand({ x, y, flip = false }: { x: number; y: number; flip?: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${flip ? -1 : 1} 1)`}>
      <circle cx="0" cy="6" r="9" fill="#e9e3ff" />
      <rect x="-6" y="-4" width="4" height="8" rx="2" fill="#e9e3ff" />
      <rect x="-1" y="-6" width="4" height="10" rx="2" fill="#e9e3ff" />
      <rect x="4" y="-4" width="4" height="8" rx="2" fill="#e9e3ff" />
      <rect x="7" y="4" width="7" height="4" rx="2" fill="#e9e3ff" />
    </g>
  )
}

/**
 * Variante « avatar » : la tête seule.
 * Sert aussi de placeholder pour les items sans image (spec §7.1, §14.2).
 */
export function LaurentAvatar({ className = 'h-full w-full' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      role="img"
      aria-label="Aucune image : Laurent Baffist prend la pose"
      fill="none"
      preserveAspectRatio="xMidYMid slice"
    >
      <rect width="100" height="100" fill="#3d1a7a" />
      <line x1="50" y1="26" x2="50" y2="16" stroke="#9370ff" strokeWidth="3" strokeLinecap="round" />
      <circle cx="50" cy="13" r="4" fill="#c4b5fd" />
      <rect x="20" y="26" width="60" height="50" rx="18" fill="#7a45f5" />
      <rect x="27" y="35" width="46" height="31" rx="12" fill="#1e1b3a" />
      <circle cx="40" cy="49" r="5" fill="#8df0d0" />
      <circle cx="60" cy="49" r="5" fill="#8df0d0" />
      <path d="M53 39 L67 36" stroke="#8df0d0" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M40 59 Q49 63 59 58" stroke="#8df0d0" strokeWidth="2.5" strokeLinecap="round" />
      <rect x="13" y="42" width="7" height="17" rx="3.5" fill="#5a1fbb" />
      <rect x="80" y="42" width="7" height="17" rx="3.5" fill="#5a1fbb" />
    </svg>
  )
}
