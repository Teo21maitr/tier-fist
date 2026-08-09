import type { TierList } from '../types'

export type CallToActionTone = 'action' | 'waiting' | 'joker' | 'draft' | 'done'

export interface TierListState {
  /** Section de l'accueil (spec §43). */
  section: 'draft' | 'todo' | 'waiting' | 'joker' | 'done'
  label: string
  /** Marqueur redondant avec la couleur : on ne s'appuie jamais sur la seule couleur (spec §58). */
  marker: string
  tone: CallToActionTone
  /** `true` lorsque l'utilisateur doit agir : à mettre en évidence. */
  needsMe: boolean
  href: string
}

export function describeTierList(tierList: TierList): TierListState {
  const { status, viewer, id } = tierList

  if (status === 'DRAFT') {
    return {
      section: 'draft',
      label: 'En création',
      marker: '✏️',
      tone: 'draft',
      needsMe: false,
      href: `/tier-lists/${id}`,
    }
  }

  if (status === 'ANSWERING') {
    if (!viewer.has_finished_answering) {
      return {
        section: 'todo',
        label: 'Tu dois encore répondre',
        marker: '🔴',
        tone: 'action',
        needsMe: true,
        href: `/tier-lists/${id}/questionnaire`,
      }
    }
    return {
      section: 'waiting',
      label: 'En attente des autres joueurs',
      marker: '🟠',
      tone: 'waiting',
      needsMe: false,
      href: `/tier-lists/${id}/questionnaire`,
    }
  }

  if (status === 'JOKER') {
    if (viewer.is_my_joker_turn) {
      return {
        section: 'joker',
        label: "C'est ton tour de joker",
        marker: '🟣',
        tone: 'joker',
        needsMe: true,
        href: `/tier-lists/${id}/resultat`,
      }
    }
    return {
      section: 'waiting',
      label: 'Phase joker — en attente de ton tour',
      marker: '🟠',
      tone: 'waiting',
      needsMe: false,
      href: `/tier-lists/${id}/resultat`,
    }
  }

  return {
    section: 'done',
    label: 'Terminée',
    marker: '🟢',
    tone: 'done',
    needsMe: false,
    href: `/tier-lists/${id}/resultat`,
  }
}

export const TONE_CLASSES: Record<CallToActionTone, string> = {
  action: 'border-rose-400 bg-rose-50 text-rose-800 dark:border-rose-700 dark:bg-rose-950/40 dark:text-rose-200',
  waiting:
    'border-amber-400 bg-amber-50 text-amber-800 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200',
  joker:
    'border-brand-400 bg-brand-50 text-brand-800 dark:border-brand-600 dark:bg-brand-950/40 dark:text-brand-200',
  draft:
    'border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300',
  done: 'border-emerald-400 bg-emerald-50 text-emerald-800 dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200',
}

export const SECTION_TITLES: Record<TierListState['section'], string> = {
  todo: 'À compléter',
  joker: 'Joker à jouer',
  draft: 'En création',
  waiting: 'En attente des autres',
  done: 'Terminées',
}

/** Ordre d'affichage : ce qui requiert l'utilisateur passe en premier. */
export const SECTION_ORDER: Array<TierListState['section']> = [
  'todo',
  'joker',
  'draft',
  'waiting',
  'done',
]
