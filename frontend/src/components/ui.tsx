import type { ReactNode } from 'react'
import { useEffect, useRef } from 'react'
import { LaurentAvatar } from './LaurentBaffist'
import type { PublicUser, RankColor } from '../types'

// --- Avatar ----------------------------------------------------------------

/** Avatar utilisateur, avec repli sur la première lettre du pseudo (spec §6.4). */
export function Avatar({
  user,
  size = 'md',
}: {
  user: PublicUser
  size?: 'sm' | 'md' | 'lg'
}) {
  const dimensions = { sm: 'h-7 w-7 text-xs', md: 'h-10 w-10 text-sm', lg: 'h-16 w-16 text-xl' }[size]

  if (user.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={`Avatar de ${user.username}`}
        className={`${dimensions} shrink-0 rounded-full object-cover`}
      />
    )
  }
  return (
    <span
      className={`${dimensions} grid shrink-0 place-items-center rounded-full bg-brand-600 font-bold text-white`}
      aria-label={`Avatar de ${user.username}`}
    >
      {user.initial}
    </span>
  )
}

// --- Image d'item ----------------------------------------------------------

/** Image d'un item, avec le placeholder Laurent Baffist si aucune image (spec §14.2). */
export function ItemImage({
  name,
  url,
  className = '',
}: {
  name: string
  url: string | null
  className?: string
}) {
  if (!url) {
    return (
      <div className={`overflow-hidden bg-brand-900 ${className}`}>
        <LaurentAvatar />
      </div>
    )
  }
  return (
    <img
      src={url}
      alt={name}
      loading="lazy"
      className={`object-cover ${className}`}
      onError={(event) => {
        // Une URL distante peut casser : on retombe sur le placeholder.
        event.currentTarget.style.display = 'none'
      }}
    />
  )
}

// --- Feedback --------------------------------------------------------------

export function Spinner({ label = 'Chargement…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-slate-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p
      role="alert"
      className="rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800/60 dark:bg-rose-950/40 dark:text-rose-200"
    >
      {children}
    </p>
  )
}

export function SuccessNote({ children }: { children: ReactNode }) {
  return (
    <p
      role="status"
      className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-200"
    >
      {children}
    </p>
  )
}

// --- Barre de progression --------------------------------------------------

export function ProgressBar({ percent, label }: { percent: number; label?: string }) {
  return (
    <div
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label ?? 'Progression'}
      className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
    >
      <div
        className="h-full rounded-full bg-brand-500 transition-all duration-500"
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  )
}

// --- Pastilles de rang -----------------------------------------------------

export const RANK_BACKGROUND: Record<RankColor, string> = {
  red: 'bg-rank-red',
  orange: 'bg-rank-orange',
  yellow: 'bg-rank-yellow',
  green: 'bg-rank-green',
  blue: 'bg-rank-blue',
}

/** Le texte reste lisible sur chaque couleur de rang (contraste, spec §58). */
export const RANK_TEXT: Record<RankColor, string> = {
  red: 'text-white',
  orange: 'text-slate-950',
  yellow: 'text-slate-950',
  green: 'text-slate-950',
  blue: 'text-white',
}

// --- Modale ----------------------------------------------------------------

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
}) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    panelRef.current?.focus()
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/60 p-0 sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="max-h-[90vh] w-full max-w-lg animate-pop-in overflow-y-auto rounded-t-3xl bg-white p-6 shadow-xl dark:bg-slate-900 sm:rounded-3xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-xl font-bold">{title}</h2>
          <button type="button" onClick={onClose} className="btn-ghost -mr-2 -mt-1" aria-label="Fermer">
            ✕
          </button>
        </div>
        {children}
        {footer && <div className="mt-6 flex flex-wrap justify-end gap-3">{footer}</div>}
      </div>
    </div>
  )
}

// --- État vide -------------------------------------------------------------

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 px-6 py-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
      {children}
    </div>
  )
}
