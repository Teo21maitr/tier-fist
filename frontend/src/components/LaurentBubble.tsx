import type { ReactNode } from 'react'
import { LaurentBaffist } from './LaurentBaffist'

interface BubbleProps {
  children: ReactNode
  /** `compact` pour les bulles en ligne, `hero` pour les grands écrans d'accueil. */
  variant?: 'default' | 'compact' | 'hero'
  mood?: 'neutral' | 'happy' | 'smug'
  tone?: 'default' | 'warning'
}

/**
 * Bulle de Laurent Baffist (spec §7.3).
 * Le ton reste léger : le sarcasme sert le côté ludique, jamais l'humiliation.
 */
export function LaurentBubble({
  children,
  variant = 'default',
  mood = 'smug',
  tone = 'default',
}: BubbleProps) {
  const mascotSize =
    variant === 'hero' ? 'h-28 w-28 sm:h-36 sm:w-36' : variant === 'compact' ? 'h-10 w-10' : 'h-16 w-16'

  const bubbleTone =
    tone === 'warning'
      ? 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-100'
      : 'border-brand-200 bg-brand-50 text-brand-900 dark:border-brand-800/60 dark:bg-brand-950/40 dark:text-brand-100'

  return (
    <div className="flex items-center gap-3 animate-pop-in">
      <LaurentBaffist className={`${mascotSize} shrink-0`} mood={mood} />
      <div
        className={`relative rounded-2xl border px-4 py-3 ${bubbleTone} ${
          variant === 'hero' ? 'text-base sm:text-lg' : 'text-sm'
        }`}
      >
        {/* Pointe de la bulle */}
        <span
          aria-hidden
          className={`absolute -left-1.5 top-1/2 h-3 w-3 -translate-y-1/2 rotate-45 border-b border-l ${bubbleTone}`}
        />
        <p className="relative italic leading-snug">{children}</p>
      </div>
    </div>
  )
}
