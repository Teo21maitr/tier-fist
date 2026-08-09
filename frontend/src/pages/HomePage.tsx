import { Link } from 'react-router-dom'
import { useTierLists } from '../api/queries'
import { LaurentBubble } from '../components/LaurentBubble'
import { TierListCard } from '../components/TierListCard'
import { EmptyState, ErrorNote, Spinner } from '../components/ui'
import { SECTION_ORDER, SECTION_TITLES, describeTierList } from '../utils/tierListState'
import type { TierList } from '../types'

export function HomePage() {
  const { data, isLoading, isError } = useTierLists()

  const grouped = new Map<string, TierList[]>()
  for (const tierList of data ?? []) {
    const { section } = describeTierList(tierList)
    grouped.set(section, [...(grouped.get(section) ?? []), tierList])
  }

  return (
    <div className="space-y-8">
      <LaurentBubble variant="hero" mood="smug">
        Une Tier List normale ? Trop facile. Ici, je fais les calculs à votre place.
      </LaurentBubble>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          to="/creer"
          className="group rounded-2xl bg-brand-600 p-6 text-white transition hover:bg-brand-500"
        >
          <h2 className="font-display text-xl font-bold">Créer une Tier List</h2>
          <p className="mt-1 text-sm text-brand-100">
            Choisis un sujet, invite tes amis, laisse-moi trancher.
          </p>
        </Link>
        <Link
          to="/rejoindre"
          className="rounded-2xl border-2 border-brand-500 p-6 transition hover:bg-brand-50 dark:hover:bg-brand-950/40"
        >
          <h2 className="font-display text-xl font-bold">Rejoindre avec un code</h2>
          <p className="mt-1 text-sm text-slate-500">
            Six caractères et te voilà juge officiel.
          </p>
        </Link>
      </div>

      {isLoading && <Spinner label="Je récupère tes parties…" />}
      {isError && <ErrorNote>Impossible de charger tes Tier Lists.</ErrorNote>}

      {data && data.length === 0 && (
        <EmptyState>
          Aucune Tier List pour l'instant. Crées-en une, ou fais-toi inviter — je ne juge pas.
        </EmptyState>
      )}

      {SECTION_ORDER.map((section) => {
        const tierLists = grouped.get(section)
        if (!tierLists || tierLists.length === 0) return null
        const needsAttention = section === 'todo' || section === 'joker'
        return (
          <section key={section} className="space-y-3">
            <h2 className="flex items-center gap-2 font-display text-lg font-bold">
              {SECTION_TITLES[section]}
              <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {tierLists.length}
              </span>
              {needsAttention && (
                <span className="text-xs font-medium uppercase tracking-wide text-brand-500">
                  action requise
                </span>
              )}
            </h2>
            <div className="grid gap-3 md:grid-cols-2">
              {tierLists.map((tierList) => (
                <TierListCard key={tierList.id} tierList={tierList} />
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
